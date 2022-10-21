import functools
import itertools
import json
import logging
import math
import os
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from glob import glob
from os import makedirs, path, remove
from statistics import mean

import numpy as np
from celery import chain
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField
from django.core.files.uploadedfile import File
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import Avg, JSONField, Prefetch, Q, Sum
from django.db.models.functions import Coalesce, Length
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.forms import ValidationError
from django.template.defaultfilters import slugify
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_prometheus.models import ExportModelOperationsMixin
from easy_thumbnails.files import get_thumbnailer
from kraken import blla, rpred
from kraken.binarization import nlbin
from kraken.kraken import SEGMENTATION_DEFAULT_MODEL
from kraken.lib import models as kraken_models
from kraken.lib import vgsl
from kraken.lib.segmentation import calculate_polygonal_environment
from kraken.lib.util import is_bitonal
from ordered_model.models import OrderedModel, OrderedModelManager
from PIL import Image
from shapely import affinity
from shapely.geometry import LineString, Polygon
from sklearn import preprocessing
from sklearn.cluster import DBSCAN

from core.tasks import (
    align,
    binarize,
    convert,
    generate_part_thumbnails,
    lossless_compression,
    segment,
    segtrain,
    train,
    transcribe,
)
from core.utils import ColorField
from core.validators import JSONSchemaValidator
from reporting.models import TASK_FINAL_STATES, TaskReport
from users.consumers import send_event
from users.models import User
from versioning.models import Versioned

logger = logging.getLogger(__name__)


class ProcessFailureException(Exception):
    pass


class AlreadyProcessingException(Exception):
    pass


class Typology(ExportModelOperationsMixin("Typology"), models.Model):
    name = models.CharField(max_length=128)

    # if True, is visible as a choice in the ontology edition in a new document
    public = models.BooleanField(default=False)
    # if True, is a valid choice by default in a new document
    default = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class DocumentType(Typology):
    pass


class DocumentPartType(Typology):
    pass


class BlockType(Typology):
    pass


class LineType(Typology):
    pass


class Tag(models.Model):
    name = models.CharField(max_length=100)
    color = ColorField()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class DocumentTag(Tag):
    project = models.ForeignKey(
        "core.Project",
        blank=True,
        related_name="document_tags",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ["project", "name"]


# class DocumentPartTag(Tag):
#     pass


class AnnotationType(Typology):
    """
    Represents a set of annotations
    for example for image annotations it could be 'pictures' or 'paleographical',
    for textual it could be 'Stylistic, Named Entity..'
    """

    pass


class AnnotationComponent(models.Model):
    name = models.CharField(max_length=128, blank=True)
    allowed_values = ArrayField(
        models.CharField(max_length=128),
        null=True,
        blank=True,
        help_text=_(
            "Comma separated list of possible value, leave it empty for free input."
        ),
    )
    document = models.ForeignKey("core.Document", on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class AnnotationTaxonomy(OrderedModel):
    MARKER_TYPE_RECTANGLE = 1
    MARKER_TYPE_POLYGON = 2
    MARKER_TYPE_BG_COLOR = 3
    MARKER_TYPE_TXT_COLOR = 4
    MARKER_TYPE_BOLD = 5
    MARKER_TYPE_ITALIC = 6
    IMG_MARKER_TYPE_CHOICES = (
        (MARKER_TYPE_RECTANGLE, _("Rectangle")),
        (MARKER_TYPE_POLYGON, _("Polygon")),
    )
    TEXT_MARKER_TYPE_CHOICES = (
        (MARKER_TYPE_BG_COLOR, _("Background Color")),
        (MARKER_TYPE_TXT_COLOR, _("Text Color")),
        (MARKER_TYPE_BOLD, _("Bold")),
        (MARKER_TYPE_ITALIC, _("Italic")),
        # (7, _('Underline'))
    )
    MARKER_TYPE_CHOICES = IMG_MARKER_TYPE_CHOICES + TEXT_MARKER_TYPE_CHOICES

    typology = models.ForeignKey(
        AnnotationType, null=True, blank=True, on_delete=models.CASCADE
    )
    has_comments = models.BooleanField(default=False)

    name = models.CharField(max_length=64)
    abbreviation = models.CharField(max_length=3, null=True, blank=True)
    marker_type = models.PositiveSmallIntegerField(choices=MARKER_TYPE_CHOICES)
    marker_detail = ColorField(null=True, blank=True)

    components = models.ManyToManyField(
        AnnotationComponent, blank=True, related_name="taxonomy"
    )

    document = models.ForeignKey(
        "core.Document", null=True, blank=True, on_delete=models.CASCADE
    )

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        return self.name


class Annotation(models.Model):
    taxonomy = models.ForeignKey(AnnotationTaxonomy, on_delete=models.CASCADE)
    comments = ArrayField(models.TextField(), null=True, blank=True)

    part = models.ForeignKey("core.DocumentPart", on_delete=models.CASCADE)

    class Meta:
        abstract = True

    def as_w3c(self):
        if self.taxonomy.marker_type in [AnnotationTaxonomy.MARKER_TYPE_RECTANGLE, AnnotationTaxonomy.MARKER_TYPE_POLYGON]:
            selector = {
                'type': 'SvgSelector',
                'value': '<svg><polygon points="{pts}"></polygon></svg>'.format(
                    pts=' '.join(['%d,%d' % (pt[0], pt[1]) for pt in self.coordinates])
                )
            }

        elif self.taxonomy.marker_type in [
            AnnotationTaxonomy.MARKER_TYPE_BG_COLOR,
            AnnotationTaxonomy.MARKER_TYPE_TXT_COLOR,
            AnnotationTaxonomy.MARKER_TYPE_BOLD,
            AnnotationTaxonomy.MARKER_TYPE_ITALIC,
        ]:

            start = (
                LineTranscription.objects.filter(
                    line__order__lt=self.start_line.order,
                    line__document_part=self.part,
                    transcription=self.transcription,
                ).aggregate(res=Coalesce(Sum(Length("content")), 0))["res"]
                + self.start_offset
            )
            end = (
                LineTranscription.objects.filter(
                    line__order__lt=self.end_line.order,
                    line__document_part=self.part,
                    transcription=self.transcription
                ).aggregate(res=Coalesce(Sum(Length("content")), 0))["res"]
                + self.end_offset
            )

            selector = {"type": "TextPositionSelector", "start": start, "end": end}

        return {
            "id": self.id,
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "type": "Annotation",
            "body": [
                {"type": "TextualBody", "value": comment, "purpose": "commenting"}
                for comment in self.comments
            ]
            + [
                {
                    "type": "TextualBody",
                    "value": component.value,
                    "purpose": "attribute-" + component.component.name,
                }
                for component in self.components.all()
            ],
            "target": {"selector": selector},
        }


class ImageAnnotation(Annotation):
    # array of points
    coordinates = ArrayField(ArrayField(models.IntegerField(), size=2))


class TextAnnotation(Annotation):
    start_line = models.ForeignKey(
        "core.Line", on_delete=models.CASCADE, related_name="annotation_starts"
    )
    start_offset = models.PositiveIntegerField()
    end_line = models.ForeignKey(
        "core.Line", on_delete=models.CASCADE, related_name="annotations_ends"
    )
    end_offset = models.PositiveIntegerField()
    transcription = models.ForeignKey("core.Transcription", on_delete=models.CASCADE)


class TextAnnotationComponentValue(models.Model):
    component = models.ForeignKey(AnnotationComponent, on_delete=models.CASCADE)
    annotation = models.ForeignKey(
        "TextAnnotation", related_name="components", on_delete=models.CASCADE
    )
    value = models.CharField(max_length=256)


class ImageAnnotationComponentValue(models.Model):
    component = models.ForeignKey(AnnotationComponent, on_delete=models.CASCADE)
    annotation = models.ForeignKey(
        "ImageAnnotation", related_name="components", on_delete=models.CASCADE
    )
    value = models.CharField(max_length=256)


class Metadata(ExportModelOperationsMixin("Metadata"), models.Model):
    name = models.CharField(max_length=128, unique=True)
    cidoc_id = models.CharField(max_length=8, null=True, blank=True)
    public = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Script(ExportModelOperationsMixin("Script"), models.Model):
    TEXT_DIRECTION_HORIZONTAL_LTR = "horizontal-lr"
    TEXT_DIRECTION_HORIZONTAL_RTL = "horizontal-rl"
    TEXT_DIRECTION_VERTICAL_LTR = "vertical-lr"
    TEXT_DIRECTION_VERTICAL_RTL = "vertical-rl"
    TEXT_DIRECTION_TTB = "ttb"
    TEXT_DIRECTION_CHOICES = (
        (TEXT_DIRECTION_HORIZONTAL_LTR, _("Horizontal l2r")),
        (TEXT_DIRECTION_HORIZONTAL_RTL, _("Horizontal r2l")),
        (TEXT_DIRECTION_VERTICAL_LTR, _("Vertical l2r")),
        (TEXT_DIRECTION_VERTICAL_RTL, _("Vertical r2l")),
        (TEXT_DIRECTION_TTB, _("Top to bottom")),
    )

    name = models.CharField(max_length=128)
    name_fr = models.CharField(max_length=128, blank=True)
    iso_code = models.CharField(max_length=4, blank=True)
    text_direction = models.CharField(max_length=64, default='horizontal-lr',
                                      choices=TEXT_DIRECTION_CHOICES)
    blank_char = models.CharField(max_length=1, default=' ', blank=True)  # Blank character in script

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DocumentMetadata(ExportModelOperationsMixin("DocumentMetadata"), models.Model):
    document = models.ForeignKey("core.Document", on_delete=models.CASCADE)
    key = models.ForeignKey(Metadata, on_delete=models.CASCADE)
    value = models.CharField(max_length=512)

    def __str__(self):
        return "%s:%s" % (self.document.name, self.key.name)


class DocumentPartMetadata(models.Model):
    part = models.ForeignKey("core.DocumentPart", on_delete=models.CASCADE, related_name="metadata")
    key = models.ForeignKey(Metadata, on_delete=models.CASCADE)
    value = models.CharField(max_length=512)

    def __str__(self):
        return "%s:%s" % (self.part.name, self.key.name)


class ProjectManager(models.Manager):
    def for_user_write(self, user):
        # return the list of EDITABLE projects
        # allows to add documents to it
        return (
            self.filter(Q(owner=user) | Q(shared_with_users=user))
            #   | Q(shared_with_groups__user=user))
            .distinct()
        )

    def for_user_read(self, user):
        # return the list of VIEWABLE projects
        # Note: Monitor this query
        return self.filter(
            Q(owner=user)
            | Q(shared_with_users=user)
            #   | Q(shared_with_groups__user=user))
            | (
                Q(documents__shared_with_users=user)
                | Q(documents__shared_with_groups__user=user)
            )
        ).distinct()


class Project(ExportModelOperationsMixin("Project"), models.Model):
    name = models.CharField(max_length=512)
    slug = models.SlugField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    shared_with_users = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Share with users"),
        related_name="shared_projects",
    )
    shared_with_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name=_("Share with teams"),
        related_name="shared_projects",
    )

    # strict_ontology =

    objects = ProjectManager()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name

    def make_slug(self):
        slug = slugify(self.name)
        # check unicity
        exists = Project.objects.filter(slug=slug).count()
        if not exists:
            self.slug = slug
        else:
            self.slug = slug[:40] + hex(int(time.time()))[2:]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.make_slug()
        super().save(*args, **kwargs)


class DocumentManager(models.Manager):
    def for_user(self, user):
        return (
            Document.objects.filter(
                Q(owner=user)
                | Q(project__owner=user)
                | Q(project__shared_with_users=user)
                #   | Q(project__shared_with_groups__user=user))
                | (Q(shared_with_users=user) | Q(shared_with_groups__user=user))
            )
            .exclude(workflow_state=Document.WORKFLOW_STATE_ARCHIVED)
            .select_related("owner")
            .distinct()
        )


class Document(ExportModelOperationsMixin("Document"), models.Model):
    WORKFLOW_STATE_DRAFT = 0
    WORKFLOW_STATE_PUBLISHED = 2  # viewable by the world
    WORKFLOW_STATE_ARCHIVED = 3  #
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_DRAFT, _("Draft")),
        (WORKFLOW_STATE_PUBLISHED, _("Published")),
        (WORKFLOW_STATE_ARCHIVED, _("Archived")),
    )
    READ_DIRECTION_LTR = "ltr"
    READ_DIRECTION_RTL = "rtl"
    READ_DIRECTION_CHOICES = (
        (READ_DIRECTION_LTR, _("Left to right")),
        (READ_DIRECTION_RTL, _("Right to left")),
    )
    LINE_OFFSET_BASELINE = 0
    LINE_OFFSET_TOPLINE = 1
    LINE_OFFSET_CENTERLINE = 2
    LINE_OFFSET_CHOICES = (
        (LINE_OFFSET_BASELINE, _("Baseline")),
        (LINE_OFFSET_TOPLINE, _("Topline")),
        (LINE_OFFSET_CENTERLINE, _("Centered")),
    )

    name = models.CharField(max_length=512)

    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_DRAFT, choices=WORKFLOW_STATE_CHOICES
    )
    main_script = models.ForeignKey(
        Script, null=True, blank=True, on_delete=models.SET_NULL
    )
    read_direction = models.CharField(
        max_length=3,
        choices=READ_DIRECTION_CHOICES,
        default=READ_DIRECTION_LTR,
        help_text=_(
            "The read direction describes the order of the elements in the document, in opposition with the text direction which describes the order of the words in a line and is set by the script."
        ),
    )
    line_offset = models.PositiveSmallIntegerField(
        choices=LINE_OFFSET_CHOICES,
        default=LINE_OFFSET_BASELINE,
        help_text=_("The position of the line relative to the polygon."),
    )
    typology = models.ForeignKey(
        DocumentType, null=True, blank=True, on_delete=models.SET_NULL
    )

    # A list of Typology(ies) which are valid to this document. Part of the document's ontology.
    valid_block_types = models.ManyToManyField(
        BlockType, blank=True, related_name="valid_in"
    )
    valid_line_types = models.ManyToManyField(
        LineType, blank=True, related_name="valid_in"
    )
    valid_part_types = models.ManyToManyField(
        DocumentPartType, blank=True, related_name="valid_in"
    )

    # Temporary stopgap before redesign of confidence visualization tools
    show_confidence_viz = models.BooleanField(
        verbose_name=_("Show confidence visualizations"),
        blank=False,
        null=False,
        default=False,
        help_text=_("If checked, enable toggling on and off colorized overlays for automatic transcription (OCR/HTR) confidences."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    metadatas = models.ManyToManyField(Metadata, through=DocumentMetadata, blank=True)

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="documents"
    )

    shared_with_users = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Share with users"),
        related_name="shared_documents",
    )
    shared_with_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name=_("Share with teams"),
        related_name="shared_documents",
    )

    tags = models.ManyToManyField(DocumentTag, blank=True, related_name='tags_document')

    objects = DocumentManager()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        created = not self.pk
        res = super().save(*args, **kwargs)
        if created:
            Transcription.objects.get_or_create(
                document=self, name=_(Transcription.DEFAULT_NAME)
            )
            self.valid_block_types.through.objects.bulk_create(
                [Document.valid_block_types.through(document_id=self.id, blocktype_id=type_.id)
                 for type_ in BlockType.objects.filter(public=True, default=True)]
            )
            self.valid_line_types.through.objects.bulk_create(
                [Document.valid_line_types.through(document_id=self.id, linetype_id=type_.id)
                 for type_ in LineType.objects.filter(public=True, default=True)]
            )

        return res

    @property
    def is_published(self):
        return self.workflow_state == self.WORKFLOW_STATE_PUBLISHED

    @property
    def is_archived(self):
        return self.workflow_state == self.WORKFLOW_STATE_ARCHIVED

    @cached_property
    def is_transcribing(self):
        return (
            self.parts.filter(
                workflow_state__gte=DocumentPart.WORKFLOW_STATE_TRANSCRIBING
            ).first()
            is not None
        )

    @cached_property
    def default_text_direction(self):
        if self.main_script:
            if self.main_script.text_direction == Script.TEXT_DIRECTION_HORIZONTAL_RTL:
                return "rtl"
            else:
                return "ltr"
        else:
            if self.read_direction == self.READ_DIRECTION_RTL:
                return "rtl"
            else:
                return "ltr"

    @cached_property
    def last_edited_part(self):
        try:
            return self.parts.order_by("-updated_at")[0]
        except IndexError:
            return None

    @property
    def training_model(self):
        return self.ocr_models.filter(training=True).first()

    def tasks_finished(self):
        """Return False if alignment or other tasks are still happening"""
        if self.parts.filter(workflow_state=DocumentPart.WORKFLOW_STATE_ALIGNING).count() == 0:
            for part in self.parts.all():
                if not part.tasks_finished():
                    return False
            return True
        return False

    def build_alignment_input_dict(self, line_transcriptions, pk):
        """Helper function for alignment to create a dict of lines for Passim input"""
        line_ids = []
        line_start = 0
        text = ""
        for lt in line_transcriptions:
            # prep the line transcription to serialize to json
            line_dict = {
                "id": str(lt.line.pk),
                "start": line_start,
            }
            text = text + lt.content + "\n"
            line_ids.append(line_dict)
            line_start = line_start + len(lt.content + "\n")
        return {
            "text": text,
            "id": pk,
            "lineIDs": line_ids,
            "ref": 0,  # distinguishes OCR from witness
        }

    def align(self, part_pks, transcription_pk, witness_pk, n_gram, max_offset, merge, full_doc, threshold, region_types, layer_name, beam_size):
        """Use subprocess call to Passim to align transcription with textual witness"""
        parts = DocumentPart.objects.filter(document=self, pk__in=part_pks)

        for part in parts:
            # set workflow state
            part.workflow_state = part.WORKFLOW_STATE_ALIGNING
        DocumentPart.objects.bulk_update(parts, ["workflow_state"])

        # set output directory
        outdir = path.join(
            settings.MEDIA_ROOT,
            f"alignments/document-{self.pk}/t{transcription_pk}+w{witness_pk}-{hex(int(time.time()))[2:]}",
        )

        # get relevant LineTranscriptions
        all_line_transcriptions = LineTranscription.objects.filter(
            transcription__pk=transcription_pk  # transcription matches the filter
        )
        # filter by region type
        region_filters = Block.get_filters(block_types=region_types, filtering_lines=True)
        all_line_transcriptions = all_line_transcriptions.filter(region_filters)

        # ensure lines are in order
        all_line_transcriptions = all_line_transcriptions.order_by(
            "line__document_part", "line__document_part__order", "line__order"
        )

        # build the JSON input for passim
        input_list = []
        if not full_doc:
            for part in parts:
                line_transcriptions = all_line_transcriptions.filter(
                    line__document_part=part,  # has lines related to this DocumentPart
                ).order_by(
                    "line__document_part", "line__document_part__order", "line__order"
                )
                input_list.append(self.build_alignment_input_dict(line_transcriptions, part.pk))
        else:
            input_list.append(self.build_alignment_input_dict(all_line_transcriptions, self.pk))

        witness = TextualWitness.objects.get(pk=witness_pk)
        f = witness.file.open('r')
        txt = f.read()
        witness_dict = {
            "id": "witness",
            "text": txt,
            "ref": 1,  # distinguishes witness from OCR
        }
        input_list.append(witness_dict)
        # save to a file
        infile = f"{outdir}.json"
        if not path.exists(outdir):
            makedirs(outdir)
        with open(infile, "w", encoding="utf-8") as file:
            for entry in input_list:  # dump to JSONL
                json.dump(entry, file, ensure_ascii=False)
                file.write("\n")

        # set beam size if present and > 0, otherwise set max-offset
        offset_beam = ("--beam", str(beam_size)) if (
            beam_size and int(beam_size) > 0
        ) else ("--max-offset", str(max_offset))

        try:
            # call passim
            subprocess.check_call([
                "seriatim",  # Passim call
                "--docwise",  # docwise mode (instead of linewise/pairwise)
                "--floating-ngrams",  # allow n-gram matches anywhere, not just at word boundaries
                "-n", str(n_gram),  # index n-grams
                offset_beam[0], offset_beam[1],
                "--fields", "ref",
                "--filterpairs", "ref = 1 AND ref2 = 0",
                infile,
                outdir,
            ])
        except Exception as e:
            # cleanup in case of exception
            remove(infile)
            shutil.rmtree(outdir)
            raise e

        # get the output json file(s)
        out_json = glob(f"{outdir}/out.json/*.json")
        aligned_lines = []
        if out_json:
            # handle multi-part output
            for json_part in out_json:
                json_file = open(json_part, "r", encoding="utf-8")
                for line in json_file.readlines():
                    # iterate through lines in output with "wits" entries
                    out_dict = json.loads(line)
                    for line in out_dict.get("lines", []):
                        for match in line.get("wits", []):
                            match_text = match.get("text", "")
                            n_matches = float(match.get("matches", 0))
                            # if the % of matches is greater than or equal to threshold:
                            if (
                                n_matches / max(len(line.get("text", "")), len(match_text))
                            ) >= threshold:
                                # find the matching line id in line_ids based on character position
                                match_line_id = next((
                                    identified_line for identified_line in out_dict.get("lineIDs", [])
                                    if identified_line["start"] == line["begin"]
                                ), {})
                                aligned_lines.append({
                                    "id": match_line_id.get("id", -1),
                                    "text": match_text,
                                    "alg": match.get("alg", ""),
                                })

        # build the new transcription layer
        original_trans = Transcription.objects.get(pk=transcription_pk)
        if not layer_name:
            # if the user did not provide a new layer name, use generated format
            layer_name = f"Aligned: {witness.name} + {original_trans.name}"
        trans, created = Transcription.objects.get_or_create(
            name=layer_name,
            document=self,
        )
        for part in parts:
            lines = part.lines.all()
            for line in lines:
                # find this line by "id" key in the output
                matches = list(filter(lambda alg: int(alg["id"]) == line.pk, aligned_lines))

                # build LineTranscription
                # if this line is present in the aligned output, set its content to aligned text
                if matches:
                    lt, created = LineTranscription.objects.get_or_create(line=line, transcription=trans)
                    # use matches[0]["alg"] instead for forced alignment with dashes
                    # lt.content = matches[0]["alg"]
                    lt.content = matches[0]["text"]
                    lt.save()
                # if "merge" is checked and this line is not present, get content from original transcription
                elif merge:
                    try:
                        old_lt = LineTranscription.objects.get(line=line, transcription=original_trans)
                        lt, created = LineTranscription.objects.get_or_create(line=line, transcription=trans)
                        lt.content = old_lt.content
                        lt.save()
                    except LineTranscription.DoesNotExist:
                        pass

        # clean up temp files
        if not getattr(settings, "KEEP_ALIGNMENT_TEMPFILES", None):
            remove(infile)
            shutil.rmtree(outdir)

        for part in parts:
            # set workflow state
            part.workflow_state = part.WORKFLOW_STATE_ALIGNED
        DocumentPart.objects.bulk_update(parts, ["workflow_state"])

    def queue_alignment(self, parts_qs, **kwargs):
        if not self.tasks_finished():
            raise AlreadyProcessingException
        align.delay(
            document_pk=self.pk,
            part_pks=list(parts_qs.values_list('pk', flat=True)),
            **kwargs,
        )

    def cancel_alignment(self, revoke_task=True, username=None):
        """Cancel the alignment task; adapted from OcrModel"""
        task_id = None

        # We don't need to search for the task_id if the alignment task was already revoked
        if revoke_task:
            try:
                report = self.reports.filter(document_pk=self.pk, method="core.tasks.align").last()
                task_id = report.task_id
            except AttributeError:
                raise ProcessFailureException(_("Couldn't find the alignment task."))
            else:
                report.cancel(username)

        # set all aligning parts to a canceled workflow state
        parts = DocumentPart.objects.filter(document=self, workflow_state=DocumentPart.WORKFLOW_STATE_ALIGNING)
        for part in parts:
            send_event("document", self.pk, "part:workflow", {
                "id": part.pk,
                "process": "align",
                "status": "canceled",
                "task_id": task_id,
            })
            part.workflow_state = part.WORKFLOW_STATE_TRANSCRIBING
        DocumentPart.objects.bulk_update(parts, ["workflow_state"])


def document_images_path(instance, filename):
    return "documents/{0}/{1}".format(instance.document.pk, filename)


class DocumentPart(ExportModelOperationsMixin("DocumentPart"), OrderedModel):
    """
    Represents a physical part of a larger document that is usually a page
    """

    name = models.CharField(max_length=512, blank=True)
    image = models.ImageField(upload_to=document_images_path)
    original_filename = models.CharField(max_length=1024, blank=True)
    image_file_size = models.BigIntegerField()
    source = models.CharField(max_length=1024, blank=True)
    bw_backend = models.CharField(max_length=128, default="kraken")
    bw_image = models.ImageField(
        upload_to=document_images_path,
        null=True,
        blank=True,
        help_text=_("Binarized image needs to be the same size as original image."),
    )
    typology = models.ForeignKey(
        DocumentPartType, null=True, blank=True, on_delete=models.SET_NULL
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="parts"
    )
    order_with_respect_to = "document"

    comments = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # average confidence for lines on this part (page), from the transcription whose confidence is the best
    max_avg_confidence = models.FloatField(null=True, blank=True)

    WORKFLOW_STATE_CREATED = 0
    WORKFLOW_STATE_CONVERTING = 1
    WORKFLOW_STATE_CONVERTED = 2
    # WORKFLOW_STATE_BINARIZING = 3  # legacy
    # WORKFLOW_STATE_BINARIZED = 4
    WORKFLOW_STATE_SEGMENTING = 5
    WORKFLOW_STATE_SEGMENTED = 6
    WORKFLOW_STATE_TRANSCRIBING = 7
    WORKFLOW_STATE_ALIGNING = 8
    WORKFLOW_STATE_ALIGNED = 9
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_CREATED, _("Created")),
        (WORKFLOW_STATE_CONVERTING, _("Converting")),
        (WORKFLOW_STATE_CONVERTED, _("Converted")),
        (WORKFLOW_STATE_SEGMENTING, _("Segmenting")),
        (WORKFLOW_STATE_SEGMENTED, _("Segmented")),
        (WORKFLOW_STATE_TRANSCRIBING, _("Transcribing")),
        (WORKFLOW_STATE_ALIGNING, _("Aligning")),
        (WORKFLOW_STATE_ALIGNED, _("Aligned")),
    )
    workflow_state = models.PositiveSmallIntegerField(
        choices=WORKFLOW_STATE_CHOICES, default=WORKFLOW_STATE_CREATED
    )

    # this is denormalized because it's too heavy to calculate on the fly
    transcription_progress = models.PositiveSmallIntegerField(default=0)

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        if self.name:
            return self.name
        return "%s %d" % (self.typology or _("Element"), self.order + 1)

    @property
    def title(self):
        return str(self)

    @property
    def converted(self):
        return self.workflow_state >= self.WORKFLOW_STATE_CONVERTED

    @property
    def binarized(self):
        try:
            self.bw_image.file
        except ValueError:
            # catches ValueError: The 'bw_image' attribute has no file associated with it.
            return False
        else:
            return True

    @property
    def segmented(self):
        return self.lines.count() > 0

    @property
    def has_masks(self):
        try:
            # Note: imposing a limit and catching IndexError is faster than counting
            self.lines.exclude(mask=None)[0]
            return True
        except IndexError:
            return False

    @property
    def filename(self):
        # TODO: os.path.split(self.image.path)[1] looks like it could sometime
        # produce an error. Maybe use Path().name, or at the very least
        # os.path.split(self.image.path)[-1]?
        return self.original_filename or os.path.split(self.image.path)[1]

    def calculate_progress(self):
        total = self.lines.count()
        if not total:
            return 0
        transcribed = LineTranscription.objects.filter(line__document_part=self).count()
        self.transcription_progress = min(int(transcribed / total * 100), 100)

    def recalculate_ordering(self, read_direction=None):
        """
        Re-order the lines of the DocumentPart depending on read direction.
        """
        read_direction = read_direction or self.document.read_direction
        # imgbox = ((0, 0), (self.image.width, self.image.height))

        origin_box = [
            self.image.width if read_direction == Document.READ_DIRECTION_RTL else 0,
            0,
        ]

        def distance(x, y):
            return math.sqrt(sum([(a - b) ** 2 for a, b in zip(x, y)]))

        def poly_origin_pt(shape):
            return min(shape, key=lambda pt: distance(pt, origin_box))

        def baseline_origin_pt(baseline_, read_direction_):
            return baseline_[
                -1 if read_direction_ == Document.READ_DIRECTION_RTL else 0
            ]

        def line_origin_pt(line_, read_direction_):
            return (
                baseline_origin_pt(line_.baseline, read_direction_)
                if line_.baseline
                else poly_origin_pt(line_.mask)
            )

        def line_block_pk(line_):
            return line_.block.pk if line_.block else 0

        def avg_line_height_column(y_origins_np, line_labels):
            """ "Return the min of the averages line heights of the columns"""
            labels = np.unique(line_labels)
            line_heights_list = []
            for label in labels:
                y_origins_column = y_origins_np[line_labels == label]
                column_height = (
                    y_origins_column.max() - y_origins_column.min()
                ) / y_origins_column.size
                line_heights_list.append(column_height)
            return min(line_heights_list)

        def avg_line_height_block(lines_in_block, read_direction_):
            """Returns the average line height in the block taking into account devising number of columns
            based on x lines origins clustering. Key parameters of the algorithm:
            x_cluster: tolerance used to gather lines in a column
            line_height_decrease: scaling factor to avoid over gathering of lines"""
            x_cluster, line_height_decrease = 0.1, 0.8

            origins_np = np.array(
                list(map(lambda l: line_origin_pt(l, read_direction_), lines_in_block))
            )

            # Devise the number of columns by performing DBSCAN clustering on x coordinate of line origins
            x_origins_np = origins_np[:, 0].reshape(-1, 1)
            scaler = preprocessing.MinMaxScaler()
            scaler.fit(x_origins_np)
            x_scaled = scaler.transform(x_origins_np)
            clustering = DBSCAN(eps=x_cluster)
            clustering.fit(x_scaled)

            # Compute the average line size based on the guessed number of columns
            y_origins_np = origins_np[:, 1]
            return (
                avg_line_height_column(y_origins_np, clustering.labels_)
                * line_height_decrease
            )

        def avg_lines_heights_dict(lines, read_direction_):
            """Returns a dictionary with block.pk (or 0 if None) as keys and average lines height
            in the block as values"""
            sorted_by_block = sorted(lines, key=line_block_pk)
            organized_by_block = itertools.groupby(sorted_by_block, key=line_block_pk)

            avg_heights = {}
            for block_pk, lines_in_block in organized_by_block:
                avg_heights[block_pk] = avg_line_height_block(
                    lines_in_block, read_direction_
                )
            return avg_heights

        # fetch all lines and regroup them by block
        qs = self.lines.select_related("block").all()
        ls = list(qs)
        if len(ls) == 0:
            return

        dict_avg_heights = avg_lines_heights_dict(ls, read_direction)

        def cmp_lines(a, b):
            # cache origin pts for efficiency
            if not hasattr(a, "origin_pt"):
                a.origin_pt = line_origin_pt(a, read_direction)
            if not hasattr(b, "origin_pt"):
                b.origin_pt = line_origin_pt(b, read_direction)

            try:
                if a.block != b.block:
                    pt1 = poly_origin_pt(a.block.box) if a.block else a.origin_pt
                    pt2 = poly_origin_pt(b.block.box) if b.block else b.origin_pt

                    # when comparing blocks we can use the distance
                    return distance(pt1, origin_box) - distance(pt2, origin_box)
                else:
                    pt1 = a.origin_pt
                    pt2 = b.origin_pt

                    # # 2 lines more or less on the same level
                    avg_height = dict_avg_heights[line_block_pk(a)]
                    if abs(pt1[1] - pt2[1]) < avg_height:
                        return distance(pt1, origin_box) - distance(pt2, origin_box)
                return pt1[1] - pt2[1]
            except TypeError:  # invalid line
                return 0

        # sort depending on the distance to the origin
        ls.sort(key=functools.cmp_to_key(lambda a, b: cmp_lines(a, b)))
        # one query / line, super gory
        for order, line in enumerate(ls):
            if line.order != order:
                line.order = order
                line.save()

    def save(self, *args, **kwargs):
        new = self.pk is None
        instance = super().save(*args, **kwargs)
        if new:
            self.task(
                "convert",
                user_pk=self.document.owner and self.document.owner.pk or None,
            )
            send_event("document", self.document.pk, "part:new", {"id": self.pk})
        else:
            self.calculate_progress()
        return instance

    def delete(self, *args, **kwargs):
        send_event("document", self.document.pk, "part:delete", {"id": self.pk})
        return super().delete(*args, **kwargs)

    @property
    def workflow(self):
        w = {}
        if self.workflow_state == self.WORKFLOW_STATE_CONVERTING:
            w["convert"] = "ongoing"
        elif self.workflow_state > self.WORKFLOW_STATE_CONVERTING:
            w["convert"] = "done"
        if self.workflow_state == self.WORKFLOW_STATE_SEGMENTING:
            w["segment"] = "ongoing"
        elif self.workflow_state > self.WORKFLOW_STATE_SEGMENTING:
            w["segment"] = "done"
        if self.workflow_state == self.WORKFLOW_STATE_TRANSCRIBING:
            w["transcribe"] = "done"
        if self.workflow_state == self.WORKFLOW_STATE_ALIGNING:
            w["align"] = "ongoing"
        if self.workflow_state == self.WORKFLOW_STATE_ALIGNED:
            w["align"] = "done"

        for report in self.reports.filter(method__in=["core.tasks.binarize", "core.tasks.segment", "core.tasks.transcribe", "core.tasks.align"]):
            # Only the last registered state for each group of tasks will be kept
            short_name = report.method.split(".")[-1]
            if report.workflow_state == TaskReport.WORKFLOW_STATE_QUEUED:
                w[short_name] = "pending"
            elif report.workflow_state == TaskReport.WORKFLOW_STATE_STARTED:
                w[short_name] = "ongoing"
            elif report.workflow_state == TaskReport.WORKFLOW_STATE_ERROR:
                w[short_name] = "canceled"
            elif report.workflow_state == TaskReport.WORKFLOW_STATE_CANCELED:
                w[short_name] = "error"
        return w

    def tasks_finished(self):
        try:
            return len([t for t in self.workflow if t["status"] != "done"]) == 0
        except (KeyError, TypeError):
            return True

    def in_queue(self):
        try:
            return (self.reports.filter(workflow_state=TaskReport.WORKFLOW_STATE_STARTED).count() == 0
                    and self.reports.filter(workflow_state=TaskReport.WORKFLOW_STATE_QUEUED).count() > 0)
        except (KeyError, TypeError):
            return False

    def cancel_tasks(self, username=None):
        uncancelable = [
            "core.tasks.convert",
            "core.tasks.lossless_compression",
            "core.tasks.generate_part_thumbnails",
        ]
        if self.workflow_state == self.WORKFLOW_STATE_SEGMENTING:
            self.workflow_state = self.WORKFLOW_STATE_CONVERTED
            self.save()
        elif self.workflow_state == self.WORKFLOW_STATE_ALIGNING:
            # handle alignment cancellation on the entire document
            self.document.cancel_alignment(username=username)
            return

        for report in self.reports.all():
            if report.method not in uncancelable and report.workflow_state not in TASK_FINAL_STATES:
                if report.task_id:  # if not, it is still pending
                    report.cancel(username)

                try:
                    send_event('document', self.document.pk, 'part:workflow',
                               {'id': self.id,
                                'process': report.method.split('.')[-1],
                                'status': 'error',
                                'reason': _('Canceled.')})
                except Exception as e:
                    # don't crash on websocket error
                    logger.exception(e)

    def recoverable(self):
        now = round(datetime.utcnow().timestamp())
        try:
            return len([report for report in self.reports.all()
                        if (int(report.started_at.strftime('%s')) if report.started_at else 0)
                        + getattr(settings, 'TASK_RECOVER_DELAY', 60 * 60 * 24) > now]) != 0

        except KeyError:
            return True  # probably old school stored task

    def recover(self):
        tasks_map = {  # map a task to a workflow state it should go back to if failed
            "core.tasks.convert": (
                self.WORKFLOW_STATE_CONVERTING,
                self.WORKFLOW_STATE_CREATED,
            ),
            "core.tasks.segment": (
                self.WORKFLOW_STATE_SEGMENTING,
                self.WORKFLOW_STATE_CONVERTED,
            ),
            "core.tasks.transcribe": (
                self.WORKFLOW_STATE_TRANSCRIBING,
                self.WORKFLOW_STATE_SEGMENTED,
            ),
            "core.tasks.align": (
                self.WORKFLOW_STATE_ALIGNING,
                self.WORKFLOW_STATE_TRANSCRIBING,
            ),
        }
        for task_name in tasks_map:
            if self.workflow_state == tasks_map[task_name][0] and self.reports.filter(method=task_name).exists():
                report = self.reports.filter(method=task_name).last()
                report.error("error")
                self.workflow_state = tasks_map[task_name][1]

        self.save()

    def convert(self):
        if not getattr(settings, "ALWAYS_CONVERT", False):
            return

        if self.workflow_state < self.WORKFLOW_STATE_CONVERTING:
            self.workflow_state = self.WORKFLOW_STATE_CONVERTING
            self.save()

        old_name = self.image.file.name
        filename, extension = os.path.splitext(old_name)
        if extension != ".png":
            new_name = filename + ".png"
            error = subprocess.check_call(["convert", old_name, new_name])
            if error:
                raise RuntimeError("Error trying to convert file(%s) to png.")

            self.image = new_name.split(settings.MEDIA_ROOT)[1][1:]
            os.remove(old_name)

        if self.workflow_state < self.WORKFLOW_STATE_CONVERTED:
            self.workflow_state = self.WORKFLOW_STATE_CONVERTED

        with Image.open(self.image.path) as im:
            if is_bitonal(im):
                self.bw_image = self.image

        self.save()

    def compress(self):
        if not getattr(settings, "COMPRESS_ENABLE", True):
            return
        filename, extension = os.path.splitext(self.image.file.name)
        if extension != "png":
            return
        opti_name = filename + "_opti.png"
        try:
            subprocess.check_call(["pngcrush", "-q", self.image.file.name, opti_name])
        except Exception as e:
            # Note: let it fail it's fine
            logger.exception("png optimization failed for %s." % filename)
            if settings.DEBUG:
                raise e
        else:
            os.rename(opti_name, self.image.file.name)

    def binarize(self, threshold=None):
        fname = os.path.basename(self.image.file.name)
        # should be formatted to png already by lossless_compression but better safe than sorry
        form = None
        f_, ext = os.path.splitext(self.image.file.name)
        if ext[1] in [".jpg", ".jpeg", ".JPG", ".JPEG", ""]:
            if ext:
                logger.warning("jpeg does not support 1bpp images. Forcing to png.")
            form = "png"
            fname = "%s.%s" % (f_, form)
        bw_file_name = "bw_" + fname
        bw_file = os.path.join(os.path.dirname(self.image.file.name), bw_file_name)
        with Image.open(self.image.path) as im:
            # threshold, zoom, escale, border, perc, range, low, high
            if threshold is not None:
                res = nlbin(im, threshold)
            else:
                res = nlbin(im)
            res.save(bw_file, format=form)

        self.bw_image = document_images_path(self, bw_file_name)
        self.save()

    def segment(
        self,
        steps=None,
        text_direction=None,
        read_direction=None,
        model=None,
        override=False,
    ):
        """
        steps: lines regions masks
        """
        self.workflow_state = self.WORKFLOW_STATE_SEGMENTING
        self.save()

        if model:
            model_path = model.file.path
        else:
            model_path = SEGMENTATION_DEFAULT_MODEL
        model_ = vgsl.TorchVGSLModel.load_model(model_path)

        # TODO: check model_type [None, 'recognition', 'segmentation']
        #    &  seg_type [None, 'bbox', 'baselines']

        im = Image.open(self.image.file.name)
        # will be fixed sometime in the future
        # if model_.one_channel_mode == '1':
        #     # TODO: need to binarize, probably not live...
        #     if not self.bw_image:
        #         self.binarize()
        #     im = Image.open(self.bw_image.file.name)
        # elif model_.one_channel_mode == 'L':
        #     im = Image.open(self.image.file.name).convert('L')
        # else:
        #     im = Image.open(self.image.file.name)

        options = {
            "device": getattr(settings, "KRAKEN_TRAINING_DEVICE", "cpu"),
            "model": model_,
        }
        if text_direction:
            options["text_direction"] = text_direction

        with transaction.atomic():
            # cleanup pre-existing
            if steps in ["lines", "both"] and override:
                self.lines.all().delete()
            if steps in ["regions", "both"] and override:
                self.blocks.all().delete()

            res = blla.segment(im, **options)

            if steps in ["regions", "both"]:
                block_types = {t.name: t for t in self.document.valid_block_types.all()}
                for region_type, regions in res["regions"].items():
                    for region in regions:
                        Block.objects.create(
                            document_part=self,
                            typology=block_types.get(region_type),
                            box=region,
                        )

            regions = self.blocks.all()
            if steps in ["lines", "both"]:
                line_types = {t.name: t for t in self.document.valid_line_types.all()}
                for line in res["lines"]:
                    mask = line["boundary"] if line["boundary"] is not None else None
                    baseline = line["baseline"]

                    # calculate if the center of the line is contained in one of the region
                    # (pick the first one that matches)
                    center = LineString(baseline).interpolate(0.5, normalized=True)
                    region = next(
                        (r for r in regions if Polygon(r.box).contains(center)), None
                    )

                    Line.objects.create(
                        document_part=self,
                        typology=line_types.get(line["tags"].get("type")),
                        block=region,
                        baseline=baseline,
                        mask=mask,
                    )

        im.close()

        self.workflow_state = self.WORKFLOW_STATE_SEGMENTED
        self.save()
        self.recalculate_ordering(read_direction=read_direction)

    def transcribe(self, model, text_direction=None):
        trans, created = Transcription.objects.get_or_create(
            name="kraken:" + model.name, document=self.document
        )
        model_ = kraken_models.load_any(model.file.path)

        lines = self.lines.all()
        text_direction = (
            text_direction
            or (self.document.main_script and self.document.main_script.text_direction)
            or "horizontal-lr"
        )

        if (self.document.main_script
            and (self.document.main_script.text_direction == 'horizontal-rl'
                 or self.document.main_script.text_direction == 'vertical-rl')):
            reorder = 'R'
        else:
            reorder = 'L'

        with Image.open(self.image.file.name) as im:
            line_confidences = []
            for line in lines:
                if not line.baseline:
                    bounds = {
                        "boxes": [line.box],
                        "text_direction": text_direction,
                        "type": "baselines",
                        # 'script_detection': True
                    }
                else:
                    bounds = {
                        "lines": [
                            {
                                "baseline": line.baseline,
                                "boundary": line.mask,
                                "text_direction": text_direction,
                                "tags": {'type': line.typology and line.typology.name or 'default'},
                            }
                        ],  # self.document.main_script.name
                        "type": "baselines",
                        # 'selfcript_detection': True
                    }

                it = rpred.rpred(
                    model_,
                    im,
                    bounds=bounds,
                    pad=16,  # TODO: % of the image?
                    bidi_reordering=reorder
                )
                lt, created = LineTranscription.objects.get_or_create(
                    line=line, transcription=trans
                )
                for pred in it:
                    lt.content = pred.prediction
                    lt.graphs = [{
                        'c': letter,
                        'poly': poly,
                        'confidence': float(confidence)
                    } for letter, poly, confidence in zip(
                        pred.prediction, pred.cuts, pred.confidences)]
                if lt.graphs:
                    line_avg_confidence = mean([graph['confidence'] for graph in lt.graphs if "confidence" in graph])
                    lt.avg_confidence = line_avg_confidence
                    line_confidences.append(line_avg_confidence)
                lt.save()
        if line_confidences:
            # calculate and set all avg confidence values on models
            avg_line_confidence = mean(line_confidences)
            # store max avg confidence on the page
            if not self.max_avg_confidence or avg_line_confidence > self.max_avg_confidence:
                self.max_avg_confidence = avg_line_confidence

        self.workflow_state = self.WORKFLOW_STATE_TRANSCRIBING
        self.calculate_progress()
        self.save()

        # overall avg recalculations; may use DB aggregation so run after self.save()
        if line_confidences and not created:
            # if new line_confidences have been added to existing transcription,
            # then recalculate average confidence across the transcription
            lines_with_confidence = trans.linetranscription_set.filter(avg_confidence__isnull=False)
            trans.avg_confidence = lines_with_confidence.aggregate(avg=Avg("avg_confidence")).get("avg")
            trans.save()
        elif line_confidences:
            # if this is a new transcription, its avg confidence will be the avg of lines
            # transcribed here
            trans.avg_confidence = avg_line_confidence
            trans.save()

    def chain_tasks(self, *tasks):
        chain(*tasks).delay()

    def task(self, task_name, commit=True, **kwargs):
        if not self.tasks_finished():
            raise AlreadyProcessingException
        tasks = []

        if task_name == 'convert' or self.workflow_state < self.WORKFLOW_STATE_CONVERTED:
            sig = convert.si(instance_pk=self.pk, **kwargs)

            if getattr(settings, 'THUMBNAIL_ENABLE', True):
                sig.link(chain(lossless_compression.si(instance_pk=self.pk, **kwargs),
                               generate_part_thumbnails.si(instance_pk=self.pk, **kwargs)))
            else:
                sig.link(lossless_compression.si(instance_pk=self.pk, **kwargs))
            tasks.append(sig)

        if task_name == 'binarize':
            tasks.append(binarize.si(instance_pk=self.pk,
                                     report_label='Binarize in %s' % self.document.name,
                                     **kwargs))

        if (task_name == 'segment'):
            tasks.append(segment.si(instance_pk=self.pk,
                                    report_label='Segment in %s' % self.document.name,
                                    **kwargs))

        if task_name == 'transcribe':
            if not self.segmented:
                kw = kwargs.copy()
                kw.pop('model_pk')  # we don't want to transcribe with a segmentation model
                tasks.append(segment.si(instance_pk=self.pk,
                                        report_label='Segment in %s' % self.document.name,
                                        **kw))
            tasks.append(transcribe.si(instance_pk=self.pk,
                                       report_label='Transcribe in %s' % self.document.name,
                                       **kwargs))

        if commit:
            self.chain_tasks(*tasks)

        return tasks

    def make_masks(self, only=None):
        im = Image.open(self.image).convert("L")
        lines = list(self.lines.all())  # needs to store the qs result
        to_calc = [line for line in lines if (only and line.pk in only) or (only is None)]

        for line in to_calc:
            context = [line_.baseline for line_ in lines if line_.pk != line.pk]
            if line.block:
                poly = line.block.box
                poly.append(line.block.box[0])  # close it
                context.append(poly)

            if self.document.line_offset == Document.LINE_OFFSET_TOPLINE:
                topline = True
            elif self.document.line_offset == Document.LINE_OFFSET_CENTERLINE:
                topline = None
            else:
                topline = False

            mask = calculate_polygonal_environment(
                im, [line.baseline], suppl_obj=context, scale=(1200, 0), topline=topline
            )
            if mask[0]:
                line.mask = mask[0]
                line.save()

        return to_calc

    def rotate(self, angle, user=None):
        """
        Rotates everything in this document part around the center by a given angle (in degrees):
        images, lines and regions.
        Changes the file system image path to deal with browser cache.
        """
        angle_match = re.search(r"_rot(\d+)", self.image.name)
        old_angle = angle_match and int(angle_match.group(1)) or 0
        new_angle = (old_angle + angle) % 360

        def update_name(fpath, old_angle=old_angle, new_angle=new_angle):
            # we need to change the name of the file to avoid all kind of cache issues
            if old_angle:
                if new_angle:
                    new_name = re.sub(
                        r"(_rot)" + str(old_angle), r"\g<1>" + str(new_angle), fpath
                    )
                else:
                    new_name = re.sub(r"_rot" + str(old_angle), "", fpath)
            else:
                # if there was no angle before, there is one now
                name, ext = os.path.splitext(fpath)
                new_name = f"{name}_rot{new_angle}{ext}"
            return new_name

        # rotate image
        with Image.open(self.image.file.name) as im:
            # store center point while it's open with old bounds
            center = (im.width / 2, im.height / 2)
            rim = im.rotate(360 - angle, expand=True, fillcolor=None)

            # the image size is shifted so we need to calculate by which offset
            # to update points accordingly
            new_center = (rim.width / 2, rim.height / 2)
            offset = (center[0] - new_center[0], center[1] - new_center[1])

            # Note: self.image.file.name (full path) != self.image.name (relative path)
            rim.save(update_name(self.image.file.name))
            rim.close()
            # save the updated file name in db
            self.image = update_name(self.image.name)

        # rotate bw image
        if self.bw_image:
            with Image.open(self.bw_image.file.name) as im:
                rim = im.rotate(360 - angle, expand=True)
                rim.save(update_name(self.bw_image.file.name))
                rim.close()
                self.bw_image = update_name(self.bw_image.name)

        self.save()

        # we need this one right away
        get_thumbnailer(self.image).get_thumbnail(
            settings.THUMBNAIL_ALIASES[""]["large"]
        )
        generate_part_thumbnails.delay(instance_pk=self.pk)

        # rotate lines
        for line in self.lines.all():
            if line.baseline:
                poly = affinity.rotate(LineString(line.baseline), angle, origin=center)
                line.baseline = [
                    (int(x - offset[0]), int(y - offset[1])) for x, y in poly.coords
                ]
            if line.mask:
                poly = affinity.rotate(Polygon(line.mask), angle, origin=center)
                line.mask = [
                    (int(x - offset[0]), int(y - offset[1]))
                    for x, y in poly.exterior.coords
                ]
            line.save()

        # rotate regions
        for region in self.blocks.all():
            poly = affinity.rotate(Polygon(region.box), angle, origin=center)
            region.box = [
                (int(x - offset[0]), int(y - offset[1]))
                for x, y in poly.exterior.coords
            ]
            region.save()

        # rotate img annotations
        for annotation in self.imageannotation_set.prefetch_related('taxonomy'):
            poly = affinity.rotate(Polygon(annotation.coordinates), angle, origin=center)
            annotation.coordinates = [
                (int(x - offset[0]), int(y - offset[1]))
                for x, y in poly.exterior.coords
            ]

            annotation.save()

    def crop(self, x1, y1, x2, y2):
        """
        Crops the image outside the rectangle defined
        by top left (x1, y1) and bottom right (x2, y2) points.
        Moves the lines and regions accordingly.
        """
        with Image.open(self.image.file.name) as im:
            cim = im.crop((x1, y1, x2, y2))
            cim.save(self.image.file.name)
            cim.close()

        if self.bw_image:
            with Image.open(self.image.file.name) as im:
                cim = im.crop((x1, y1, x2, y2))
                cim.save(self.image.file.name)
                cim.close()

        for line in self.lines.all():
            if line.baseline:
                line.baseline = [(int(x - x1), int(y - y1)) for x, y in line.baseline]
            if line.mask:
                line.mask = [(int(x - x1), int(y - y1)) for x, y in line.mask]
            line.save()

        for region in self.blocks.all():
            region.box = [(int(x - x1), int(y - y1)) for x, y in region.box]
            region.save()

    def enforce_line_order(self):
        # django-ordered-model doesn't care about unicity and linearity...
        lines = self.lines.order_by("order", "pk")
        for i, line in enumerate(lines):
            if line.order != i:
                logger.debug("Enforcing line order %d : %d" % (line.pk, i))
                line.order = i
                line.save()


def validate_polygon(value):
    if value is None:
        return
    try:
        value[0][0]
    except (TypeError, KeyError, IndexError):
        raise ValidationError(
            _("%(value)s is not a polygon - a 2 dimensional array."),
            params={"value": value},
        )


def validate_2_points(value):
    if value is None:
        return
    if len(value) < 2:
        raise ValidationError(
            _("Polygon needs to have at least 2 points, it has %(length)d: %(value)s."),
            params={"length": len(value), "value": value},
        )


def validate_3_points(value):
    if value is None:
        return
    if len(value) < 3:
        raise ValidationError(
            _("Polygon needs to have at least 3 points, it has %(length)d: %(value)s."),
            params={"length": len(value), "value": value},
        )


class Block(ExportModelOperationsMixin("Block"), OrderedModel, models.Model):
    """
    Represents a visually close group of graphemes (characters) bound by the same semantic
    example: a paragraph, a margin note or floating text
    """

    # box = models.BoxField()  # in case we use PostGIS
    box = JSONField(validators=[validate_polygon, validate_3_points])
    typology = models.ForeignKey(
        BlockType, null=True, blank=True, on_delete=models.SET_NULL
    )
    document_part = models.ForeignKey(
        DocumentPart, on_delete=models.CASCADE, related_name="blocks"
    )
    order_with_respect_to = "document_part"

    external_id = models.CharField(max_length=128, blank=True, null=True)

    class Meta(OrderedModel.Meta):
        pass

    @property
    def coordinates_box(self):
        """
        Cast the box field to the format [xmin, ymin, xmax, ymax]
        to make it usable to calculate VPOS, HPOS, WIDTH, HEIGHT for ALTO
        """
        return [*map(min, *self.box), *map(max, *self.box)]

    @property
    def width(self):
        return self.coordinates_box[2] - self.coordinates_box[0]

    @property
    def height(self):
        return self.coordinates_box[3] - self.coordinates_box[1]

    def get_filters(block_types, filtering_lines=False):
        """
        Helper method to get filters for block types. By default, assumes filters are built for
        a QuerySet of Blocks. Set filtering_lines param to True to filter on LineTranscriptions
        instead.
        """
        # check for oprhan and undefined
        include_orphans = False
        if "Orphan" in block_types:
            include_orphans = True
            block_types.remove("Orphan")
        include_undefined = False
        if "Undefined" in block_types:
            include_undefined = True
            block_types.remove("Undefined")

        # build filters
        filters = Q(line__block__typology_id__in=block_types) if filtering_lines else Q(typology_id__in=block_types)
        if include_orphans and filtering_lines:
            # this filter is only applicable to LineTranscriptions
            filters |= Q(line__block__isnull=True)
        if include_undefined:
            filters |= Q(
                line__block__isnull=False, line__block__typology_id__isnull=True
            ) if filtering_lines else Q(typology_id__isnull=True)
        return filters

    def make_external_id(self):
        self.external_id = "eSc_textblock_%s" % str(uuid.uuid4())[:8]

    def save(self, *args, **kwargs):
        if self.external_id is None:
            self.make_external_id()
        return super().save(*args, **kwargs)


class LineManager(OrderedModelManager):
    def prefetch_transcription(self, transcription):
        return (self.get_queryset().order_by('order')
                .prefetch_related(
            Prefetch('transcriptions',
                     to_attr='transcription',
                     queryset=LineTranscription.objects.filter(
                         transcription=transcription))))


class Line(OrderedModel):  # Versioned,
    """
    Represents a segmented line from a DocumentPart
    """

    # box = gis_models.PolygonField()  # in case we use PostGIS
    # Closed Polygon: [[x1, y1], [x2, y2], ..]
    mask = JSONField(
        null=True, blank=True, validators=[validate_polygon, validate_3_points]
    )
    # Polygon: [[x1, y1], [x2, y2], ..]
    baseline = JSONField(
        null=True, blank=True, validators=[validate_polygon, validate_2_points]
    )
    document_part = models.ForeignKey(
        DocumentPart, on_delete=models.CASCADE, related_name="lines"
    )
    block = models.ForeignKey(
        Block, null=True, blank=True, on_delete=models.SET_NULL, related_name="lines"
    )
    script = models.CharField(max_length=8, null=True, blank=True)  # choices ??
    # text direction
    order_with_respect_to = "document_part"
    # version_ignore_fields = ('document_part', 'order')

    typology = models.ForeignKey(
        LineType, null=True, blank=True, on_delete=models.SET_NULL
    )

    external_id = models.CharField(max_length=128, blank=True, null=True)

    objects = LineManager()

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        return "%s#%d" % (self.document_part, self.order)

    @property
    def width(self):
        return self.box[2] - self.box[0]

    @property
    def height(self):
        return self.box[3] - self.box[1]

    def get_box(self):
        if self.mask:
            return [*map(min, *self.mask), *map(max, *self.mask)]
        elif self.baseline:
            return [*map(min, *self.baseline), *map(max, *self.baseline)]
        else:
            return None

    def set_box(self, box):
        self.mask = [
            (box[0], box[1]),
            (box[0], box[3]),
            (box[2], box[3]),
            (box[2], box[1]),
        ]

    box = cached_property(get_box, set_box)

    def make_external_id(self):
        self.external_id = "eSc_line_%s" % str(uuid.uuid4())[:8]

    def clean(self):
        super().clean()
        if self.baseline is None and self.mask is None:
            raise ValidationError(_("Both baseline and mask are empty."))

    def save(self, *args, **kwargs):
        if self.external_id is None:
            self.make_external_id()
        return super().save(*args, **kwargs)


class ProtectedObjectException(Exception):
    pass


class Transcription(ExportModelOperationsMixin("Transcription"), models.Model):
    name = models.CharField(max_length=512)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="transcriptions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    avg_confidence = models.FloatField(null=True, blank=True)

    DEFAULT_NAME = "manual"

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["name", "document"]

    def __str__(self):
        return self.name

    def archive(self):
        if self.name == self.DEFAULT_NAME:
            raise ProtectedObjectException
        else:
            self.archived = True
            self.save()

    def delete(self):
        if self.name == self.DEFAULT_NAME:
            raise ProtectedObjectException
        else:
            super().delete()


class LineTranscription(
    ExportModelOperationsMixin("LineTranscription"), Versioned, models.Model
):
    """
    Represents a transcribed line of a document part in a given transcription
    """

    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)
    content = models.CharField(blank=True, default="", max_length=2048)

    graphs_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "c": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1
                },
                "poly": {
                    "type": "array",
                    "minItems": 3,
                    "items": {
                        "type": "array",
                        "contains": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    }

                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                }
            }
        }
    }
    # on postgres this maps to the jsonb type!
    graphs = JSONField(null=True, blank=True,
                       validators=[JSONSchemaValidator(limit_value=graphs_schema)])

    # average confidence for graphs in the line
    avg_confidence = models.FloatField(null=True, blank=True)

    # nullable in case we re-segment ?? for now we lose data.
    line = models.ForeignKey(
        Line, null=True, on_delete=models.CASCADE, related_name="transcriptions"
    )
    version_ignore_fields = ("line", "transcription")

    class Meta:
        unique_together = ["line", "transcription"]

    @property
    def text(self):
        return re.sub("<[^<]+?>", "", self.content)


def models_path(instance, filename):
    # Note: we want a separate directory by model because
    # kraken stores epochs file version as a fixed filename and we don't want to override them.
    fn, ext = os.path.splitext(filename)
    hash = str(uuid.uuid4())[:8]
    return "models/%s/%s%s" % (hash, slugify(fn), ext)


class OcrModel(ExportModelOperationsMixin("OcrModel"), Versioned, models.Model):
    name = models.CharField(max_length=256)
    file = models.FileField(
        upload_to=models_path,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["mlmodel"])],
    )
    file_size = models.BigIntegerField()

    MODEL_JOB_SEGMENT = 1
    MODEL_JOB_RECOGNIZE = 2
    MODEL_JOB_CHOICES = (
        (MODEL_JOB_SEGMENT, _("Segment")),
        (MODEL_JOB_RECOGNIZE, _("Recognize")),
    )
    job = models.PositiveSmallIntegerField(choices=MODEL_JOB_CHOICES)
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    training = models.BooleanField(default=False)
    training_epoch = models.PositiveSmallIntegerField(default=0)
    training_accuracy = models.FloatField(default=0.0)
    training_total = models.IntegerField(default=0)
    training_errors = models.IntegerField(default=0)
    documents = models.ManyToManyField(
        Document, through="core.OcrModelDocument", related_name="ocr_models"
    )
    script = models.ForeignKey(Script, blank=True, null=True, on_delete=models.SET_NULL)

    version_ignore_fields = (
        "name",
        "owner",
        "documents",
        "script",
        "training",
        "parent",
    )
    version_history_max_length = None  # keep em all

    public = models.BooleanField(default=False)

    parent = models.ForeignKey("self", blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-version_updated_at"]
        permissions = (("can_train", "Can train models"),)

    def __str__(self):
        return self.name

    @cached_property
    def accuracy_percent(self):
        return self.training_accuracy * 100

    def clone_for_training(self, owner, name=None):
        children_count = OcrModel.objects.filter(parent=self).count() + 2
        model = OcrModel.objects.create(
            owner=self.owner or owner,
            name=name or self.name.split(".mlmodel")[0] + f"_v{children_count}",
            job=self.job,
            public=False,
            script=self.script,
            parent=self,
            versions=[],
            file_size=self.file.size,
        )
        model.file = File(self.file, name=os.path.basename(self.file.name))
        model.save()

        if not model.public:
            # Cloning rights to the new model
            OcrModelRight.objects.bulk_create(
                [
                    OcrModelRight(ocr_model=model, user=right.user, group=right.group)
                    for right in self.ocr_model_rights.all()
                ]
            )

        return model

    def segtrain(self, document, parts_qs, user=None):
        segtrain.delay(model_pk=self.pk,
                       part_pks=list(parts_qs.values_list('pk', flat=True)),
                       document_pk=document.pk,
                       user_pk=user and user.pk or None)

    def train(self, parts_qs, transcription, user=None):
        train.delay(transcription_pk=transcription.pk,
                    model_pk=self.pk,
                    part_pks=list(parts_qs.values_list('pk', flat=True)),
                    user_pk=user and user.pk or None)

    def cancel_training(self, revoke_task=True, username=None):
        if revoke_task:
            report = self.reports.last()
            if not report or not report.task_id or report.workflow_state in TASK_FINAL_STATES:
                raise ProcessFailureException(_("Couldn't find the training task."))

            report.cancel(username)

        self.training = False
        self.save()

    # versioning
    def pack(self, **kwargs):
        # we use the name kraken generated
        kwargs["file"] = kwargs.get("file", self.file.name)
        return super().pack(**kwargs)

    def revert(self, revision):
        # we want the file to be swapped but the filename to stay the same
        for version in self.versions:
            if version["revision"] == revision:
                current_filename = self.file.path
                target_filename = os.path.join(
                    settings.MEDIA_ROOT, version["data"]["file"]
                )
                tmp_filename = current_filename + ".tmp"
                break
        else:
            raise ValueError("Revision %s not found for %s" % (revision, self))
        os.rename(current_filename, tmp_filename)
        os.rename(target_filename, current_filename)
        os.rename(tmp_filename, target_filename)
        super().revert(revision)

    def delete_revision(self, revision):
        for version in self.versions:
            if version["revision"] == revision:
                os.remove(os.path.join(settings.MEDIA_ROOT, version["data"]["file"]))
                break
        super().delete_revision(revision)


class OcrModelDocument(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="ocr_model_documents"
    )
    ocr_model = models.ForeignKey(
        OcrModel, on_delete=models.CASCADE, related_name="ocr_model_documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    trained_on = models.DateTimeField(null=True, blank=True)
    executed_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["document", "ocr_model"]


class OcrModelRight(models.Model):
    ocr_model = models.ForeignKey(
        OcrModel, on_delete=models.CASCADE, related_name="ocr_model_rights"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ocr_model_rights",
        null=True,
        blank=True,
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="ocr_model_rights",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "group", "ocr_model"], name="right_unique_target"
            ),
            # User XOR Group is the owner of this access right
            models.CheckConstraint(
                name="user_xor_group",
                check=(
                    models.Q(group_id__isnull=False, user_id__isnull=True)
                    | models.Q(group_id__isnull=True, user_id__isnull=False)
                )
            )
        ]


class TextualWitness(models.Model):
    """
    A known reference text to use in text alignment along with an automated or uncertain transcription.
    """

    # This model is needed so that we can pass the uploaded file through Celery's JSON serialization.
    file = models.FileField(
        upload_to="witnesses/",
        null=False,
        validators=[FileExtensionValidator(allowed_extensions=["txt"])],
    )
    name = models.CharField(
        max_length=256,
        null=False,
        blank=False,
    )
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} (id: {self.pk})"


@receiver(pre_delete, sender=DocumentPart, dispatch_uid="thumbnails_delete_signal")
def delete_thumbnails(sender, instance, using, **kwargs):
    thumbnailer = get_thumbnailer(instance.image)
    thumbnailer.delete_thumbnails()
    thumbnailer = get_thumbnailer(instance.bw_image)
    thumbnailer.delete_thumbnails()
