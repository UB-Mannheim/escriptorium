import hashlib
import io
import json
import os.path
import re
import tarfile
import time
import zipfile
from datetime import datetime

import oitei
from django.apps import apps
from django.conf import settings
from django.db.models import Avg, Prefetch
from django.template import loader
from django.utils.text import slugify

from core.models import Block, Transcription

TEXT_FORMAT = "text"
PAGEXML_FORMAT = "pagexml"
ALTO_FORMAT = "alto"
OPENITI_MARKDOWN_FORMAT = "openitimarkdown"
TEI_XML_FORMAT = "teixml"
JSON_FORMAT = "json"

DOCUMENT_FILENAME = "document.json"
EXPORT_CONFIG_FILENAME = "export-config.json"
PARTS_FILENAME = "parts.jsonl"
ANNOTATIONS_FILENAME = "annotations.jsonl"


class EsZipFile(zipfile.ZipFile):
    def writestr(self, arcname, data,
                 compress_type=None, compresslevel=None):
        zinfo = zipfile.ZipInfo(filename=arcname,
                                date_time=time.localtime(time.time())[:6])
        zinfo.compress_type = self.compression
        zinfo._compresslevel = self.compresslevel
        zinfo.external_attr = 0o644 << 16
        return super().writestr(zinfo, data, compress_type, compresslevel)


class BaseExporter:
    def __init__(
        self,
        part_pks,
        region_types,
        include_images,
        include_characters,
        user=None,
        document=None,
        report=None,
        transcription=None,
        include_metadata=False,
        include_models=False,
        include_annotations=False,
        all_transcriptions=False,
        anonymize=False,
        archive_format="zip",
    ):
        self.part_pks = part_pks
        self.region_types = region_types
        self.include_images = include_images
        self.include_characters = include_characters
        self.user = user
        self.document = document
        self.report = report
        self.transcription = transcription
        self.include_metadata = include_metadata
        self.include_models = include_models
        self.include_annotations = include_annotations
        self.all_transcriptions = all_transcriptions
        # When True, JsonExporter (and any future format-specific exporter)
        # replaces user identifiers with opaque tokens instead of usernames.
        self.anonymize = anonymize
        # Container format for the packaged archive (JSON exporter only).
        # Accepted values: "zip" (default), "tar.gz".
        self.archive_format = archive_format if archive_format in ("zip", "tar.gz") else "zip"

        self.prepare_for_rendering()

    def prepare_for_rendering(self):
        base_filename = "export_doc%d_%s_%s_%s" % (
            self.document.pk,
            slugify(self.document.name).replace("-", "_")[:32],
            self.file_format,
            datetime.now().strftime("%Y%m%d%H%M%S"),
        )
        assert hasattr(
            self, "file_extension"
        ), "file_extension attribute is mandatory and must be defined on your exporter"
        filename = f"{base_filename}.{self.file_extension}"
        self.filepath = os.path.join(self.user.get_document_store_path(), filename)


class TextExporter(BaseExporter):
    file_format = TEXT_FORMAT
    file_extension = "txt"

    def render(self):
        region_filters = Block.get_filters(block_types=self.region_types, filtering_lines=True)

        LineTranscription = apps.get_model("core", "LineTranscription")
        lines = (
            LineTranscription.objects.filter(
                transcription=self.transcription,
                line__document_part__pk__in=self.part_pks,
            )
            .select_related("line__document_part")
            .filter(region_filters)
            .exclude(content="")
            .order_by(
                "line__document_part", "line__document_part__order", "line__order"
            )
        )
        docid = None
        with open(self.filepath, "w") as fh:
            for trans in lines:
                if trans.line.document_part.pk != docid:
                    fh.write("--------------- %s (%s) ---------------\n" % (
                        trans.line.document_part.title,
                        trans.line.document_part.filename
                    ))
                    docid = trans.line.document_part.pk
                fh.write("%s\n" % trans.content)
            fh.close()


class XMLTemplateExporter(BaseExporter):
    file_extension = "zip"

    def render(self):
        tplt = loader.get_template(self.template_path)

        DocumentPart = apps.get_model("core", "DocumentPart")
        parts = DocumentPart.objects.filter(
            document=self.document, pk__in=self.part_pks
        )

        # since this is filtering Blocks and not LineTranscriptions, it needs to handle orphans
        # separately
        include_orphans = False
        if "Orphan" in self.region_types:
            include_orphans = True
            self.region_types.remove("Orphan")
        region_filters = Block.get_filters(block_types=self.region_types, filtering_lines=False)

        with EsZipFile(self.filepath, "w") as zip_:
            mets_elements = []
            for index, part in enumerate(parts, start=1):
                mets_element = {"id": index, "page": None, "image": None}

                render_orphans = (
                    {}
                    if not include_orphans
                    else {
                        "orphan_lines": part.lines.prefetch_transcription(
                            self.transcription
                        ).filter(block=None)
                    }
                )

                if self.include_images:
                    # Note adds image before the xml file
                    zip_.write(part.image.path, part.filename)
                    mets_element["image"] = part.filename

                try:
                    Line = apps.get_model("core", "Line")
                    page = tplt.render(
                        {
                            "include_characters": self.include_characters,
                            "valid_block_types": self.document.block_types.all(),
                            "valid_line_types": self.document.line_types.all(),
                            "part": part,
                            "blocks": (
                                part.blocks.filter(region_filters)
                                .annotate(avglo=Avg("lines__order"))
                                .order_by("avglo")
                                .prefetch_related(
                                    Prefetch(
                                        "lines",
                                        queryset=Line.objects.prefetch_transcription(
                                            self.transcription
                                        ),
                                    )
                                )
                            ),
                            **render_orphans,
                        }
                    )
                    # Remove empty lines from XML output.
                    page = re.sub(r'\n[ \t]*(?=\n)', '', page)
                except Exception as e:
                    self.report.append(
                        "Skipped {element}({image}) because '{reason}'.".format(
                            element=part.name, image=part.filename, reason=str(e)
                        )
                    )
                    if settings.EXPORT_STRICT:
                        raise e
                else:
                    filename = "%s.xml" % os.path.splitext(part.filename)[0]
                    zip_.writestr(filename, page)
                    mets_element["page"] = filename

                mets_elements.append(mets_element)

            # Adding METS file in the archive
            mets_template = loader.get_template("export/METS.xml")
            mets = mets_template.render({"elements": mets_elements, "include_images": any([element["image"] for element in mets_elements])})
            zip_.writestr("METS.xml", mets)

            zip_.close()


class PageXMLExporter(XMLTemplateExporter):
    file_format = PAGEXML_FORMAT
    template_path = "export/pagexml.xml"


class AltoExporter(XMLTemplateExporter):
    file_format = ALTO_FORMAT
    template_path = "export/alto.xml"


class JsonExporter(BaseExporter):
    file_format = JSON_FORMAT
    file_extension = "json"

    def _anonymize_user(self, username):
        """When self.anonymize is True, replace a username with a stable
        opaque token; otherwise return the username unchanged. The token is
        deterministic per (document, username) pair so re-imports keep the
        cross-record identity but a name never leaves the export.
        """
        if not username or not self.anonymize:
            return username
        key = ("%s:%s" % (self.document.pk, username)).encode("utf-8")
        return "user_" + hashlib.sha256(key).hexdigest()[:12]

    def _serialize_document_metadata(self):
        return [
            {
                "key": md.key.name,
                "value": md.value,
            }
            for md in self.document.documentmetadata_set.select_related("key").all()
        ]

    def _serialize_part_metadata(self, part):
        return [
            {
                "key": md.key.name,
                "value": md.value,
            }
            for md in part.metadata.all()
        ]

    def _transcriptions_prefetch(self):
        # pull every exported layer in one go so lines never query on their own
        LineTranscription = apps.get_model("core", "LineTranscription")
        return Prefetch(
            "transcriptions",
            to_attr="prefetched_transcriptions",
            queryset=LineTranscription.objects.filter(
                transcription_id__in=self.transcription_pks
            ).order_by("transcription_id"),
        )

    def _serialize_transcription(self, lt):
        """one line transcription row or none when the line has no text on that layer"""
        if not lt:
            return None

        data = {
            "pk": lt.pk,
            "transcription_pk": lt.transcription_id,
            "content": lt.content,
            "avg_confidence": lt.avg_confidence,
            "modified_by": self._anonymize_user(lt.version_author) or None,
            "modified_at": lt.version_updated_at.isoformat() if lt.version_updated_at else None,
            "history": [
                {
                    "content": v.get("data", {}).get("content"),
                    "author": self._anonymize_user(v.get("author")),
                    "source": v.get("source"),
                    "created_at": v.get("created_at"),
                    "updated_at": v.get("updated_at"),
                }
                for v in (lt.versions or [])
            ],
        }

        if self.include_characters:
            data["characters"] = lt.graphs

        return data

    def _serialize_line(self, line):
        layers = getattr(line, "prefetched_transcriptions", None) or []

        return {
            "pk": line.pk,
            "external_id": line.external_id,
            "order": line.order,
            "typology": {
                "pk": line.typology_id,
                "name": line.typology.name if line.typology else None,
            },
            "baseline": line.baseline,
            "mask": line.mask,
            "box": line.get_box(),
            "block_pk": line.block_id,
            "transcriptions": [self._serialize_transcription(lt) for lt in layers],
        }

    def _serialize_block(self, block):
        lines = []
        for line in getattr(block, "prefetched_lines", []):
            lines.append(self._serialize_line(line))

        return {
            "pk": block.pk,
            "external_id": block.external_id,
            "order": block.order,
            "typology": {
                "pk": block.typology_id,
                "name": block.typology.name if block.typology else None,
            },
            "box": block.box,
            "bbox": block.coordinates_box,
            "width": block.width,
            "height": block.height,
            "lines": lines,
        }

    def _serialize_part(self, part, include_orphans, region_filters, image_names):
        Line = apps.get_model("core", "Line")

        blocks_qs = (
            part.blocks.filter(region_filters)
            .annotate(avglo=Avg("lines__order"))
            .order_by("avglo", "order", "pk")
            .prefetch_related(
                Prefetch(
                    "lines",
                    queryset=Line.objects.prefetch_related(
                        self._transcriptions_prefetch()
                    )
                    .select_related("typology", "block")
                    .order_by("order", "pk"),
                    to_attr="prefetched_lines",
                )
            )
            .select_related("typology")
        )

        regions = [self._serialize_block(block) for block in blocks_qs]

        orphan_lines = []
        if include_orphans:
            orphan_qs = (
                part.lines.filter(block=None)
                .prefetch_related(self._transcriptions_prefetch())
                .select_related("typology", "block")
                .order_by("order", "pk")
            )
            orphan_lines = [self._serialize_line(line) for line in orphan_qs]

        image_data = {
            "filename": part.filename,
            "original_filename": part.original_filename,
            "archive_filename": image_names.get(part.pk),
            "uri": part.image.url if getattr(part, "image", None) and self.include_images else None,
            "width": getattr(part.image, "width", None) if getattr(part, "image", None) else None,
            "height": getattr(part.image, "height", None) if getattr(part, "image", None) else None,
            "size": [
                getattr(part.image, "width", None),
                getattr(part.image, "height", None),
            ] if getattr(part, "image", None) else None,
        }

        return {
            "pk": part.pk,
            "title": part.title,
            "name": part.name,
            "filename": part.filename,
            "order": part.order,
            "workflow_state": part.workflow_state,
            "transcription_progress": part.transcription_progress,
            "typology": {
                "pk": part.typology_id,
                "name": part.typology.name if part.typology else None,
            },
            "image": image_data,
            "metadata": self._serialize_part_metadata(part),
            "regions": regions,
            "orphan_lines": orphan_lines,
        }

    def render(self):
        DocumentPart = apps.get_model("core", "DocumentPart")

        region_types = list(self.region_types) if self.region_types else []
        include_orphans = "Orphan" in region_types
        region_filters = Block.get_filters(
            block_types=list(region_types),
            filtering_lines=False,
        )

        parts = list(
            DocumentPart.objects.filter(document=self.document, pk__in=self.part_pks)
            .select_related("typology")
            .prefetch_related("metadata__key")
            .order_by("order", "pk")
        )

        if self.all_transcriptions:
            transcriptions = list(
                Transcription.objects.filter(document=self.document).order_by("name", "pk")
            )
        else:
            transcriptions = [self.transcription]

        self.transcription_pks = [t.pk for t in transcriptions]

        image_entries = self._collect_images(parts) if self.include_images else []
        image_names = {part_pk: arcname for arcname, _, part_pk in image_entries}

        document = {
            "pk": self.document.pk,
            "name": self.document.name,
            "read_direction": self.document.read_direction,
            "line_offset": self.document.line_offset,
            "main_script": self.document.main_script.name if self.document.main_script else None,
            "valid_block_types": [
                {"pk": bt.pk, "name": bt.name}
                for bt in self.document.block_types.all().order_by("name")
            ],
            "valid_line_types": [
                {"pk": lt.pk, "name": lt.name}
                for lt in self.document.line_types.all().order_by("name")
            ],
        }

        export_config = {
            "file_format": self.file_format,
            "transcriptions": [
                {"pk": t.pk, "name": t.name}
                for t in transcriptions
            ],
            "part_pks": list(self.part_pks),
            "region_types": region_types,
            "include_images": self.include_images,
            "include_characters": self.include_characters,
        }

        if self.include_metadata:
            document["metadata"] = self._serialize_document_metadata()

        if self.include_models:
            document["models"] = [
                {
                    "pk": m.pk,
                    "name": m.name,
                    "job": m.job,
                }
                for m in self.document.ocr_models.all()
            ]

        entries = [
            (DOCUMENT_FILENAME, None, json.dumps(document, ensure_ascii=False, indent=2)),
            (EXPORT_CONFIG_FILENAME, None,
             json.dumps(export_config, ensure_ascii=False, indent=2)),
            (PARTS_FILENAME, None, self._as_jsonl(
                self._serialize_part(part, include_orphans, region_filters, image_names)
                for part in parts
            )),
        ]

        if self.include_annotations:
            part_pks = [part.pk for part in parts]
            entries.append((ANNOTATIONS_FILENAME, None,
                            self._as_jsonl(self._serialize_annotations(part_pks))))

        # json files first then images under the names recorded in the parts
        entries += [(arcname, path, None) for arcname, path, _ in image_entries]

        archive_path = self._build_archive(entries)

        # Clean up the standalone json placeholder if it lingered.
        if os.path.exists(self.filepath) and self.filepath != archive_path:
            try:
                os.remove(self.filepath)
            except OSError:
                pass
        self.filepath = archive_path

    def _collect_images(self, parts):
        """returns arcname path part_pk triples with duplicate names deduped by part pk"""
        entries = []
        seen = set()
        for part in parts:
            if not part.image:
                continue
            try:
                image_path = part.image.path
            except (ValueError, NotImplementedError):
                continue
            if not os.path.exists(image_path):
                continue
            arcname = os.path.basename(part.image.name)
            if arcname in seen:
                base, ext = os.path.splitext(arcname)
                arcname = f"{base}_{part.pk}{ext}"
            seen.add(arcname)
            entries.append((arcname, image_path, part.pk))
        return entries

    def _as_jsonl(self, rows):
        """one compact json object per line"""
        return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)

    def _build_archive(self, entries):
        """Pack entries into the container format the user picked.

        `entries` is a list of (arcname, path). When `path` is None the
        entry's content is `json_content` (written in-memory).
        Returns the on-disk archive path (self.filepath with a rewritten
        extension: .zip or .tar.gz).
        """
        base_path = os.path.splitext(self.filepath)[0]
        if self.archive_format == "tar.gz":
            archive_path = base_path + ".tar.gz"
            with tarfile.open(archive_path, "w:gz") as tf:
                for arcname, path, content in entries:
                    if path is None:
                        data = content.encode("utf-8")
                        info = tarfile.TarInfo(name=arcname)
                        info.size = len(data)
                        info.mode = 0o644
                        tf.addfile(info, io.BytesIO(data))
                    else:
                        tf.add(path, arcname=arcname)
        else:
            archive_path = base_path + ".zip"
            with EsZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for arcname, path, content in entries:
                    if path is None:
                        zf.writestr(arcname, content)
                    else:
                        zf.write(path, arcname)
        return archive_path

    def _serialize_annotations(self, part_pks):
        ImageAnnotation = apps.get_model("core", "ImageAnnotation")
        TextAnnotation = apps.get_model("core", "TextAnnotation")

        annotations = []
        for ann in ImageAnnotation.objects.filter(part_id__in=part_pks).select_related("taxonomy").prefetch_related("components__component").order_by("part_id", "pk"):
            annotations.append({
                "type": "image",
                "part_pk": ann.part_id,
                "taxonomy": ann.taxonomy.name if ann.taxonomy else None,
                "w3c": ann.as_w3c(),
            })
        for ann in TextAnnotation.objects.filter(part_id__in=part_pks).select_related("taxonomy", "start_line", "end_line").prefetch_related("components__component").order_by("part_id", "pk"):
            annotations.append({
                "type": "text",
                "part_pk": ann.part_id,
                "taxonomy": ann.taxonomy.name if ann.taxonomy else None,
                "w3c": ann.as_w3c(),
            })
        return annotations


class OpenITIMARkdownExporter(BaseExporter):
    file_format = OPENITI_MARKDOWN_FORMAT
    file_extension = "zip"

    def render_part_markdown(self, part, region_filters):
        LineTranscription = apps.get_model("core", "LineTranscription")
        return self.template.render(
            {
                "version": settings.VERSION_DATE,
                "part": part,
                "lines": LineTranscription.objects.filter(
                    transcription=self.transcription,
                    line__document_part=part,
                )
                .filter(region_filters)
                .exclude(content="")
                .order_by("line__order"),
            }
        )

    def render(self, tei_conversion=False):
        self.template = loader.get_template("export/openiti_markdown.mARkdown")

        DocumentPart = apps.get_model("core", "DocumentPart")
        parts = DocumentPart.objects.filter(
            document=self.document, pk__in=self.part_pks
        )

        region_filters = Block.get_filters(block_types=self.region_types, filtering_lines=True)

        with EsZipFile(self.filepath, "w") as zip_:
            for part in parts:
                if self.include_images:
                    # Note adds image before the mARkdown file
                    zip_.write(part.image.path, part.filename)
                try:
                    markdown_content = self.render_part_markdown(part, region_filters)

                    if tei_conversion:
                        content = oitei.convert(markdown_content).tostring()
                    else:
                        content = markdown_content

                except Exception as e:
                    self.report.append(
                        "Skipped {element}({image}) because '{reason}'.".format(
                            element=part.name, image=part.filename, reason=str(e)
                        )
                    )
                else:
                    ext = "xml" if tei_conversion else "mARkdown"
                    zip_.writestr(
                        "%s.%s" % (os.path.splitext(part.filename)[0], ext), content
                    )

            zip_.close()


class TEIXMLExporter(OpenITIMARkdownExporter):
    file_format = TEI_XML_FORMAT

    def render(self):
        # We need an extra TEI conversion after the OpenITI mARkdown generation
        super().render(tei_conversion=True)


ENABLED_EXPORTERS = {
    TEXT_FORMAT: {"class": TextExporter, "label": "Text"},
    PAGEXML_FORMAT: {"class": PageXMLExporter, "label": "PAGE"},
    ALTO_FORMAT: {"class": AltoExporter, "label": "ALTO"},
    JSON_FORMAT: {"class": JsonExporter, "label": "JSON"},
}

if settings.EXPORT_OPENITI_MARKDOWN_ENABLED:
    ENABLED_EXPORTERS[OPENITI_MARKDOWN_FORMAT] = {
        "class": OpenITIMARkdownExporter,
        "label": "OpenITI mARkdown",
    }
if settings.EXPORT_TEI_XML_ENABLED:
    ENABLED_EXPORTERS[TEI_XML_FORMAT] = {
        "class": TEIXMLExporter,
        "label": "OpenITI TEI XML",
    }
