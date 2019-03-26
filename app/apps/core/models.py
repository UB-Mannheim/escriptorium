import re
import math
import logging
import os.path
import functools
import subprocess
from PIL import Image

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.db.models.signals import pre_delete

from celery.result import AsyncResult
from celery import chain
from easy_thumbnails.files import get_thumbnailer
from ordered_model.models import OrderedModel

from versioning.models import Versioned
from core.tasks import *
from users.consumers import send_event

User = get_user_model()
logger = logging.getLogger(__name__)

class ProcessFailureException(Exception):
    pass


class AlreadyProcessingException(Exception):
    pass


class Typology(models.Model):
    """
    Document: map, poem, novel ..
    Part: page, log, cover ..
    Block: main text, floating text, illustration, 
    """
    TARGET_DOCUMENT = 1
    TARGET_PART = 2
    TARGET_BLOCK = 3
    TARGET_CHOICES = (
        (TARGET_DOCUMENT, 'Document'),
        (TARGET_PART, 'Part (eg Page)'),
        (TARGET_BLOCK, 'Block (eg Paragraph)'),
    )
    name = models.CharField(max_length=128)
    target = models.PositiveSmallIntegerField(choices=TARGET_CHOICES)
    
    def __str__(self):
        return self.name


class Metadata(models.Model):
    name = models.CharField(max_length=128, unique=True)
    cidoc_id = models.CharField(max_length=8, null=True, blank=True)
    
    class Meta:
        ordering = ('name',)
    
    def __str__(self):
        return self.name


class DocumentMetadata(models.Model):
    document = models.ForeignKey('core.Document', on_delete=models.CASCADE)
    key = models.ForeignKey(Metadata, on_delete=models.CASCADE)
    value = models.CharField(max_length=512)
    
    def __str__(self):
        return '%s:%s' % (self.document.name, self.key.name)
    

class DocumentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('typology')
    
    def for_user(self, user):
        # return the list of editable documents
        # Note: Monitor this query
        return (Document.objects
                .filter(Q(owner=user)
                        | (Q(workflow_state__gt=Document.WORKFLOW_STATE_DRAFT)
                          & (Q(shared_with_users=user)
                             | Q(shared_with_groups__in=user.groups.all())
                          )))
                .exclude(workflow_state=Document.WORKFLOW_STATE_ARCHIVED)
                .prefetch_related('shared_with_groups')
                .select_related('typology')
                .distinct()
        )


class Document(models.Model):
    WORKFLOW_STATE_DRAFT = 0
    WORKFLOW_STATE_SHARED = 1  # editable a viewable by shared_with people
    WORKFLOW_STATE_PUBLISHED = 2  # viewable by the world
    WORKFLOW_STATE_ARCHIVED = 3  # 
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_DRAFT, _("Draft")),
        (WORKFLOW_STATE_SHARED, _("Shared")),
        (WORKFLOW_STATE_PUBLISHED, _("Published")),
        (WORKFLOW_STATE_ARCHIVED, _("Archived")),
    )
    
    name = models.CharField(max_length=512)
    
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_DRAFT,
        choices=WORKFLOW_STATE_CHOICES)
    shared_with_users = models.ManyToManyField(User, blank=True,
                                               verbose_name=_("Share with users"),
                                               related_name='shared_documents')
    shared_with_groups = models.ManyToManyField(Group, blank=True,
                                                verbose_name=_("Share with teams"),
                                                related_name='shared_documents')
    
    typology = models.ForeignKey(Typology, null=True, blank=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_DOCUMENT})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    metadatas = models.ManyToManyField(Metadata, through=DocumentMetadata, blank=True)
    
    objects = DocumentManager()
    
    class Meta:
        ordering = ('-updated_at',)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)
        Transcription.objects.get_or_create(document=self, name=_('manual'))
        return res
        
    @property
    def is_shared(self):
        return self.workflow_state in [self.WORKFLOW_STATE_PUBLISHED,
                                       self.WORKFLOW_STATE_SHARED]    
    @property
    def is_published(self):
        return self.workflow_state == self.WORKFLOW_STATE_PUBLISHED
    
    @property
    def is_archived(self):
        return self.workflow_state == self.WORKFLOW_STATE_ARCHIVED

    @cached_property
    def is_transcribing(self):
        return self.parts.filter(workflow_state__gte=DocumentPart.WORKFLOW_STATE_TRANSCRIBING).first() is not None


def document_images_path(instance, filename):
    return 'documents/%d/%s' % (instance.document.pk, filename)


class DocumentPart(OrderedModel):
    """
    Represents a physical part of a larger document that is usually a page
    """
    name = models.CharField(max_length=512, blank=True)
    image = models.ImageField(upload_to=document_images_path)
    bw_backend = models.CharField(max_length=128, default='kraken')
    bw_image = models.ImageField(upload_to=document_images_path,
                                 null=True, blank=True,
                                 help_text=_("Binarized image needs to be the same size as original image."))
    typology = models.ForeignKey(Typology, null=True, blank=True,
                                 on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_PART})
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='parts')
    order_with_respect_to = 'document'
    
    WORKFLOW_STATE_CREATED = 0
    WORKFLOW_STATE_COMPRESSING = 1
    WORKFLOW_STATE_COMPRESSED = 2
    WORKFLOW_STATE_BINARIZING = 3
    WORKFLOW_STATE_BINARIZED = 4
    WORKFLOW_STATE_SEGMENTING = 5
    WORKFLOW_STATE_SEGMENTED = 6
    WORKFLOW_STATE_TRANSCRIBING = 7
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_CREATED, _("Created")),
        (WORKFLOW_STATE_COMPRESSING, _("Compressing")),
        (WORKFLOW_STATE_COMPRESSED, _("Compressed")),
        (WORKFLOW_STATE_BINARIZING, _("Binarizing")),
        (WORKFLOW_STATE_BINARIZED, _("Binarized")),
        (WORKFLOW_STATE_SEGMENTING, _("Segmenting")),
        (WORKFLOW_STATE_SEGMENTED, _("Segmented")),
        (WORKFLOW_STATE_TRANSCRIBING, _("Transcribing")),
    )
    workflow_state = models.PositiveSmallIntegerField(
        choices=WORKFLOW_STATE_CHOICES,
        default=WORKFLOW_STATE_CREATED)
    
    # this is denormalized because it's too heavy to calculate on the fly
    transcription_progress = models.PositiveSmallIntegerField(default=0)
    
    class Meta(OrderedModel.Meta):
        pass
    
    def __str__(self):
        if self.name:
            return self.name
        return '%s %d' % (self.typology or _("Element"), self.order + 1)
    
    @property
    def title(self):
        return str(self)
    
    @property
    def compressed(self):
        return self.workflow_state >= self.WORKFLOW_STATE_COMPRESSED
    
    @property
    def binarized(self):
        return self.workflow_state >= self.WORKFLOW_STATE_BINARIZED
    
    @property
    def segmented(self):
        return self.workflow_state >= self.WORKFLOW_STATE_SEGMENTED
    
    def calculate_progress(self):
        if self.workflow_state < self.WORKFLOW_STATE_TRANSCRIBING:
            return 0
        transcribed = LineTranscription.objects.filter(line__document_part=self).count()
        total = Line.objects.filter(document_part=self).count()
        if not total:
            return 0
        self.transcription_progress = min(int(transcribed / total * 100), 100)

    def recalculate_ordering(self, line_level_treshold=1/100):
        """
        Re-order the lines of the DocumentPart depending or text direction.
        Beware 'text direction' is different from reading order,
        it represents the order of the blocks of text.

        line_level_treshold is a percentage of the total size of the image,
        for which blocks should be considered on the same 'line',
        in which case x is used.
        """
        try:
            text_direction = self.document.process_settings.text_direction[-2:]
        except DocumentProcessSettings.DoesNotExist:
            text_direction = 'lr'
        
        def origin_pt(box):
            if text_direction == 'rl':
                return (box[2], box[1])
            else:
                return (box[0], box[1])
        
        imgsize = (self.image.width, self.image.height)
        imgbox = (0, 0) + imgsize
        def cmp_pts(a, b):
            def cmp_(a, b):
                # 2 lines more or less on the same level
                if abs(a[1] - b[1]) < line_level_treshold * imgsize[1]:
                    return abs(a[0] - origin_pt(imgbox)[0]) - abs(b[0]- origin_pt(imgbox)[0])
                return abs(a[1] - origin_pt(imgbox)[1]) - abs(b[1] - origin_pt(imgbox)[1])

            try:
                if a[0] != b[0]:
                    return cmp_(a[0], b[0])
                return cmp_(a[1], b[1])
            except TypeError:  # invalid line
                return 0
        
        # fetch all lines and regroup them by block
        ls = [(l, (origin_pt(l.block.box), origin_pt(l.box))
               if l.block else (origin_pt(l.box), origin_pt(l.box)))
              for l in self.lines.all()]
        
        # sort depending on the distance to the origin
        ls.sort(key=functools.cmp_to_key(lambda a,b: cmp_pts(a[1], b[1])))
        # one query / line, super gory
        for order, line in enumerate(ls):
            if line[0].order != order:
                line[0].order = order
                line[0].save()
    
    def save(self, *args, **kwargs):
        new = self.pk is None
        self.calculate_progress()
        instance = super().save(*args, **kwargs)
        if new:
            self.task_compress()
            send_event('document', self.document.pk, "part:new", {"id": self.pk})
        return instance
    
    def delete(self, *args, **kwargs):
        send_event('document', self.document.pk, "part:delete", {
            "id": self.pk
        })
        return super().delete(*args, **kwargs)
    
    @property
    def tasks(self):
        if not settings.USE_CELERY:
            return {}
        try:
            return json.loads(redis_.get('process-%d' % self.pk) or '{}')
        except json.JSONDecodeError:
            return {}
        
    @property
    def workflow(self):
        w = {}
        tasks = self.tasks  # its not cached
        
        if self.workflow_state == self.WORKFLOW_STATE_BINARIZING:
            w['binarize'] = 'ongoing'
        if self.workflow_state > self.WORKFLOW_STATE_BINARIZING:
            w['binarize'] = 'done'
        if self.workflow_state == self.WORKFLOW_STATE_SEGMENTING:
            w['segment'] = 'ongoing'
        if self.workflow_state > self.WORKFLOW_STATE_SEGMENTING:
            w['segment'] = 'done'
        if self.workflow_state == self.WORKFLOW_STATE_TRANSCRIBING:
            w['transcribe'] = 'done'
        
        # check on redis for reruns
        for task_name in ['core.tasks.binarize', 'core.tasks.segment', 'core.tasks.transcribe']:
            if task_name in tasks and tasks[task_name]['status'] == 'pending':
                w[task_name.split('.')[-1]] = 'pending'
            if task_name in tasks and tasks[task_name]['status'] in ['before_task_publish', 'task_prerun']:
                w[task_name.split('.')[-1]] = 'ongoing'
            elif task_name in tasks and tasks[task_name]['status'] == 'task_failure':
                w[task_name.split('.')[-1]] = 'error'
        
        # client doesnt know about compression
        if ('core.tasks.lossless_compression' in tasks and
            tasks['core.tasks.lossless_compression']['status'] in ['before_task_publish', 'task_prerun']):
            w['binarize'] = 'ongoing'
        
        return w
    
    def tasks_finished(self):
        try:
            return len([t for t in self.tasks.values()
                        if t['status'] not in ['task_success', 'task_failure']]) == 0
        except (KeyError, TypeError):
            return True
    
    def in_queue(self):
        statuses = self.tasks.values()
        try:
            return (len([t for t in statuses if t['status'] == 'ongoing']) == 0 and
                    len([t for t in statuses if t['status']
                         in ['pending', 'before_task_publish']]) > 0)
        except (KeyError, TypeError):
            return False
    
    def recover(self):
        from celery.task.control import inspect
        i = inspect()
        # Important: this is really slow!
        queued = ([task['id'] for queue in i.scheduled().values() for task in queue] +
                  [task['id'] for queue in i.active().values() for task in queue] +
                  [task['id'] for queue in i.reserved().values() for task in queue])
        if self.workflow_state == self.WORKFLOW_STATE_COMPRESSING:
            task_name = 'core.tasks.lossless_compression'
            if (not task_name in self.tasks or
                self.tasks[task_name]['task_id'] not in queued):
                self.workflow_state = self.WORFLOW_STATE_CREATED
                redis_.set('process-%d' % self.pk, json.dumps({task_name: {"status": "error"}}))
        elif self.workflow_state == self.WORKFLOW_STATE_BINARIZING:
            task_name = 'core.tasks.binarize'
            if (not task_name in self.tasks or
                self.tasks[task_name]['task_id'] not in queued):
                self.workflow_state = self.WORFLOW_STATE_COMPRESSED
                redis_.set('process-%d' % self.pk, json.dumps({task_name: {"status": "error"}}))
        elif self.workflow_state == self.WORKFLOW_STATE_SEGMENTING:
            task_name = 'core.tasks.segment'
            if (not task_name in self.tasks or
                self.tasks[task_name]['task_id'] not in queued):
                self.workflow_state = self.WORFLOW_STATE_BINARIZED
                redis_.set('process-%d' % self.pk, json.dumps({task_name: {"status": "error"}}))
        elif self.workflow_state == self.WORKFLOW_STATE_TRANSCRIBING:
            task_name = 'core.tasks.transcribe'
            if (not task_name in self.tasks or
                self.tasks[task_name]['task_id'] not in queued):
                redis_.set('process-%d' % self.pk, json.dumps({task_name: {"status": "error"}}))
        self.save()

    def generate_thumbnails(self):
        from easy_thumbnails.files import generate_all_aliases
        generate_all_aliases(self.image, include_global=True)

    def compress(self):
        if self.workflow_state < self.WORKFLOW_STATE_COMPRESSING:
            self.workflow_state = self.WORKFLOW_STATE_COMPRESSING
            self.save()
        
        convert = False
        old_name = self.image.file.name
        filename, extension = os.path.splitext(old_name)
        if extension != ".png":
            convert = True
            new_name = filename + ".png"
            error = subprocess.check_call(["convert", old_name, new_name])
            if error:
                raise RuntimeError("Error trying to convert file(%s) to png.")
        else:
            new_name = old_name
        opti_name = filename + '_opti.png'

        try:
            subprocess.check_call(["pngcrush", "-q", new_name, opti_name])
        except Exception as e:
            # Note: let it fail it's fine
            logger.exception("png optimization failed.")
        os.rename(opti_name, new_name)
        if convert:
            self.image = new_name.split(settings.MEDIA_ROOT)[1][1:]
            os.remove(old_name)
        
        if self.workflow_state < self.WORKFLOW_STATE_COMPRESSED:
            self.workflow_state = self.WORKFLOW_STATE_COMPRESSED
            self.save()
    
    def binarize(self):
        if self.workflow_state < self.WORKFLOW_STATE_BINARIZING:
            self.workflow_state = self.WORKFLOW_STATE_BINARIZING
            self.save()
        
        fname = os.path.basename(self.image.file.name)
        # should be formated to png already by by lossless_compression but better safe than sorry
        form = None
        f_, ext = os.path.splitext(self.image.file.name)
        if ext[1] in ['.jpg', '.jpeg', '.JPG', '.JPEG', '']:
            if ext:
                logger.warning('jpeg does not support 1bpp images. Forcing to png.')
            form = 'png'
            fname = '%s.%s' % (f_, form)
        bw_file_name = 'bw_' + fname
        bw_file = os.path.join(os.path.dirname(self.image.file.name), bw_file_name)
        with Image.open(self.image.path) as im:
            # threshold, zoom, escale, border, perc, range, low, high
            res = binarization.nlbin(im)
            res.save(bw_file, format=form)

        self.bw_image = document_images_path(self, bw_file_name)
        if self.workflow_state < self.WORKFLOW_STATE_BINARIZED:
            self.workflow_state = self.WORKFLOW_STATE_BINARIZED
            self.save()
    
    def segment(self, steps=None, text_direction=None):
        # cleanup pre-existing
        if steps in ['lines', 'both']:
            self.lines.all().delete()
        if steps in ['regions', 'both']:
            self.blocks.all().delete()
        
        self.workflow_state = self.WORKFLOW_STATE_SEGMENTING
        self.save()
        
        with Image.open(self.bw_image.file.name) as im:
            # text_direction='horizontal-lr', scale=None, maxcolseps=2, black_colseps=False, no_hlines=True, pad=0
            options = {'maxcolseps': 1}
            if text_direction:
                options['text_direction'] = text_direction
            blocks = self.blocks.all()
            if blocks:
                for block in blocks:
                    if block.box[2] < block.box[0] + 10 or block.box[3] < block.box[1] + 10:
                        continue
                    ic = im.crop(block.box)
                    res = pageseg.segment(ic, **options)
                    # if script_detect:
                    #     res = pageseg.detect_scripts(im, res, valid_scripts=allowed_scripts)
                    for line in res['boxes']:
                        Line.objects.create(
                            document_part=self, block=block,
                            box=(line[0]+block.box[0], line[1]+block.box[1],
                                 line[2]+block.box[0], line[3]+block.box[1]))
            else:
                res = pageseg.segment(im, **options)
                res['block'] = None
                for line in res['boxes']:
                    Line.objects.create(document_part=self, box=line)
        
        self.workflow_state = self.WORKFLOW_STATE_SEGMENTED
        self.save()
        self.recalculate_ordering()
    
    def transcribe(self, model=None):
        if model:
            trans, created = Transcription.objects.get_or_create(
                name='kraken:' + model.name,
                document=self.document)
            model_ = kraken_models.load_any(model.file.path)
            lines = self.lines.all()
            try:
                text_direction = self.document.process_settings.text_direction
            except DocumentProcessSettings.DoesNotExist:
                text_direction = None

            with Image.open(self.bw_image.file.name) as im:
                for line in lines:
                    it = rpred.rpred(
                        model_, im,
                        bounds={'boxes': [line.box],
                                'text_direction': text_direction or 'horizontal-lr',
                                'script_detection': False},
                        pad=16,  # TODO: % of the image?
                        bidi_reordering=True)
                    
                    lt, created = LineTranscription.objects.get_or_create(
                        line=line, transcription=trans)
                    for pred in it:
                        lt.content = pred.prediction
                    lt.save()
        else:
            Transcription.objects.get_or_create(
                name='manual',
                document=self.document)
        
        self.workflow_state = self.WORKFLOW_STATE_TRANSCRIBING
        self.save()
        
    def chain_tasks(self, *tasks):
        if settings.USE_CELERY:
            chain(*tasks).delay()
        else:
            chain(*tasks)()
        redis_.set('process-%d' % self.pk, json.dumps({tasks[-1].name: {"status": "pending"}}))
    
    def task_compress(self):
        if not self.tasks_finished():
            raise AlreadyProcessingException
        
        self.chain_tasks(lossless_compression.si(self.pk),
                         generate_part_thumbnails.si(self.pk))
    
    def task_binarize(self, user_pk=None, binarizer=None):
        if not self.tasks_finished():
            raise AlreadyProcessingException
        
        tasks = []
        if not self.compressed:
            tasks.append(lossless_compression.si(self.pk))
            tasks.append(generate_part_thumbnails.si(self.pk))
        tasks.append(binarize.si(self.pk, user_pk=user_pk, binarizer=binarizer))
        self.chain_tasks(*tasks)
    
    def task_segment(self, user_pk=None, steps=None, text_direction=None):
        if not self.tasks_finished():
            raise AlreadyProcessingException
        
        tasks = []
        if not self.compressed:
            tasks.append(lossless_compression.si(self.pk))
            tasks.append(generate_part_thumbnails.si(self.pk))
        if not self.binarized:
            tasks.append(binarize.si(self.pk, user_pk=user_pk))
        tasks.append(segment.si(self.pk, user_pk=user_pk, steps=steps, text_direction=text_direction))
        self.chain_tasks(*tasks)
    
    def task_transcribe(self, user_pk=None, model=None):
        if not self.tasks_finished():
            raise AlreadyProcessingException
        
        tasks = []
        if not self.compressed:
            tasks.append(lossless_compression.si(self.pk))
            tasks.append(generate_part_thumbnails.si(self.pk))
        if not self.binarized:
            tasks.append(binarize.si(self.pk, user_pk=user_pk))
        if not self.segmented:
            tasks.append(segment.si(self.pk, user_pk=user_pk))
        tasks.append(transcribe.si(self.pk, user_pk=user_pk, model_pk=model and model.pk or None))
        self.chain_tasks(*tasks)


class Block(OrderedModel, models.Model):
    """
    Represents a visualy close group of graphemes (characters) bound by the same semantic 
    example: a paragraph, a margin note or floating text
    """
    # box = models.BoxField()  # in case we use PostGIS
    box = JSONField()
    typology = models.ForeignKey(Typology, null=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_BLOCK})
    document_part = models.ForeignKey(DocumentPart, on_delete=models.CASCADE,
                                      related_name='blocks')
    order_with_respect_to = 'document_part'

    class Meta(OrderedModel.Meta):
        pass


class Line(OrderedModel):  # Versioned, 
    """
    Represents a segmented line from a DocumentPart
    """
    # box = models.BoxField()  # in case we use PostGIS
    box = JSONField()
    document_part = models.ForeignKey(DocumentPart, on_delete=models.CASCADE,
                                      related_name='lines')
    block = models.ForeignKey(Block, null=True, on_delete=models.SET_NULL)
    script = models.CharField(max_length=8, null=True, blank=True)  # choices ??
    # text direction
    order_with_respect_to = 'document_part'
    version_ignore_fields = ('document_part', 'order')
    
    class Meta(OrderedModel.Meta):
        pass
    
    def __str__(self):
        return '%s#%d' % (self.document_part, self.order)
    
    
class Transcription(models.Model):
    name = models.CharField(max_length=512)
    document = models.ForeignKey(Document, on_delete=models.CASCADE,
                                 related_name='transcriptions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('name', 'document'),)


class LineTranscription(Versioned, models.Model):
    """
    Represents a transcribded line of a document part in a given transcription
    """
    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)
    content = models.CharField(null=True, max_length=2048)
    # graphs = [  # WIP
    # {c: <graph_code>, bbox: ((x1, y1), (x2, y2)), confidence: 0-1}
    # ]
    graphs = JSONField(null=True, blank=True)  # on postgres it maps to jsonb!
    
    # nullable in case we re-segment ?? for now we lose data.
    line = models.ForeignKey(Line, null=True, on_delete=models.CASCADE,
                             related_name='transcriptions')
    version_ignore_fields = ('line', 'transcription')
    
    class Meta:
        unique_together = (('line', 'transcription'),)
    
    @property
    def text(self):
        return re.sub('<[^<]+?>', '', self.content)


class OcrModel(models.Model):
    name = models.CharField(max_length=256)
    file = models.FileField(upload_to='models/',
                            validators=[FileExtensionValidator(
                                allowed_extensions=['mlmodel'])])
    trained = models.BooleanField(default=False)
    document = models.ForeignKey(Document, blank=True, null=True,
                                 default=None, on_delete=models.SET_NULL)
    
    def __str__(self):
        return self.name


class DocumentProcessSettings(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE,
                                    related_name='process_settings')
    text_direction = models.CharField(max_length=64, default='horizontal-lr',
                                      choices=(('horizontal-lr', _("Horizontal l2r")),
                                               ('horizontal-rl', _("Horizontal r2l")),
                                               ('vertical-lr', _("Vertical l2r")),
                                               ('vertical-rl', _("Vertical r2l"))))
    binarizer = models.CharField(max_length=64,
                                 choices=(('kraken', _("Kraken")),),
                                 default='kraken')
    ocr_model = models.ForeignKey(OcrModel, verbose_name=_("Model"),
                                  related_name='settings_ocr',
                                  null=True, blank=True, on_delete=models.SET_NULL)
    train_model = models.ForeignKey(OcrModel, verbose_name=_("Model"),
                                    related_name='settings_train',
                                    null=True, blank=True, on_delete=models.SET_NULL)
    typology = models.ForeignKey(Typology,
                                 null=True, blank=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_PART})
    
    def __str__(self):
        return 'Processing settings for %s' % self.document


@receiver(pre_delete, sender=DocumentPart, dispatch_uid='thumbnails_delete_signal')
def delete_thumbnails(sender, instance, using, **kwargs):
    thumbnailer = get_thumbnailer(instance.image)
    thumbnailer.delete_thumbnails()
    thumbnailer = get_thumbnailer(instance.bw_image)
    thumbnailer.delete_thumbnails()
