import os.path
import time
import zipfile
from datetime import datetime

import oitei
from django.apps import apps
from django.conf import settings
from django.db.models import Avg, Prefetch
from django.template import loader
from django.utils.text import slugify

from core.models import Block

TEXT_FORMAT = "text"
PAGEXML_FORMAT = "pagexml"
ALTO_FORMAT = "alto"
OPENITI_MARKDOWN_FORMAT = "openitimarkdown"
TEI_XML_FORMAT = "teixml"


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
        user,
        document,
        report,
        transcription,
    ):
        self.part_pks = part_pks
        self.region_types = region_types
        self.include_images = include_images
        self.user = user
        self.document = document
        self.report = report
        self.transcription = transcription

        self.prepare_for_rendering()

    def prepare_for_rendering(self):
        base_filename = "export_doc%d_%s_%s_%s" % (
            self.document.pk,
            slugify(self.document.name).replace("-", "_")[:32],
            self.file_format,
            datetime.now().strftime("%Y%m%d%H%M"),
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
            .filter(region_filters)
            .exclude(content="")
            .order_by(
                "line__document_part", "line__document_part__order", "line__order"
            )
        )
        with open(self.filepath, "w") as fh:
            fh.writelines(["%s\n" % line.content for line in lines])
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
                            "valid_block_types": self.document.valid_block_types.all(),
                            "valid_line_types": self.document.valid_line_types.all(),
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
                except Exception as e:
                    self.report.append(
                        "Skipped {element}({image}) because '{reason}'.".format(
                            element=part.name, image=part.filename, reason=str(e)
                        )
                    )
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
