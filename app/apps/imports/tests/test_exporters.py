import datetime
import os
import shutil
from unittest.mock import patch
from zipfile import ZipFile

from django.test import override_settings
from lxml import etree

from core.models import Block, BlockType, Line, LineTranscription
from core.tests.factory import CoreFactoryTestCase
from escriptorium.test_settings import MEDIA_ROOT
from imports.export import (
    AltoExporter,
    OpenITIMARkdownExporter,
    PageXMLExporter,
    TEIXMLExporter,
    TextExporter,
)
from reporting.models import TaskReport

SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "samples",
)

CONTENTS = [
    {
        "title": "A simple test for eScriptorium",
        "body": "Some text to be exported during a document_export Celery task.",
        "signature": "A beautiful signature",
    },
    {
        "title": "Another simple test for eScriptorium",
        "body": "More text to be exported during a document_export Celery task.",
        "signature": "Another beautiful signature",
    },
]

xml_parser = etree.XMLParser(remove_blank_text=True)


def get_xml_str(file_content):
    return etree.tostring(etree.XML(file_content, parser=xml_parser))


def format_xml_contents(generated_content, expected_filename):
    return [
        get_xml_str(generated_content),
        get_xml_str(open(f"{SAMPLES_DIR}/{expected_filename}", "rb").read()),
    ]


@patch(
    "imports.templatetags.export_tags.timezone.now",
    return_value=datetime.datetime.fromtimestamp(1640995200),
)
class ExportersTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()

        user = self.factory.make_user()
        doc = self.factory.make_document(owner=user)
        self.part = self.factory.make_part(document=doc)
        self.part_xml_export_filename = f"{os.path.splitext(self.part.filename)[0]}.xml"
        self.part_md_export_filename = (
            f"{os.path.splitext(self.part.filename)[0]}.mARkdown"
        )
        self.part2 = self.factory.make_part(
            document=doc, image_asset="segmentation/default2.png"
        )
        self.part2_xml_export_filename = (
            f"{os.path.splitext(self.part2.filename)[0]}.xml"
        )
        self.part2_md_export_filename = (
            f"{os.path.splitext(self.part2.filename)[0]}.mARkdown"
        )
        self.all_parts_pks = [self.part.pk, self.part2.pk]
        transcription = self.factory.make_transcription(document=doc)

        title = BlockType.objects.create(id=1, name="title")
        self.body = BlockType.objects.create(id=2, name="body")
        signature = BlockType.objects.create(id=3, name="signature")

        # Creating content that will be exported
        for index, part in enumerate([self.part, self.part2]):
            title_block = Block.objects.create(
                box=[[190, 25], [510, 65]],
                document_part=part,
                typology=title,
                external_id=f"eSc_textblock_{index}1",
            )
            body_block = Block.objects.create(
                box=[[90, 125], [560, 215]],
                document_part=part,
                typology=self.body,
                external_id=f"eSc_textblock_{index}2",
            )
            signature_block = Block.objects.create(
                box=[[390, 245], [610, 275]],
                document_part=part,
                typology=signature,
                external_id=f"eSc_textblock_{index}3",
            )

            LineTranscription.objects.create(
                transcription=transcription,
                line=Line.objects.create(
                    baseline=[[200, 45], [500, 45]],
                    mask=[[200, 30], [500, 30], [500, 60], [200, 60]],
                    document_part=part,
                    block=title_block,
                    external_id=f"eSc_line_{index}1",
                ),
                content=CONTENTS[index].get("title"),
            )
            for i in range(3):
                padding = 30 * i
                LineTranscription.objects.create(
                    transcription=transcription,
                    line=Line.objects.create(
                        baseline=[[100, 140 + padding], [550, 140 + padding]],
                        mask=[
                            [100, 130 + padding],
                            [550, 130 + padding],
                            [550, 150 + padding],
                            [100, 150 + padding],
                        ],
                        document_part=part,
                        block=body_block,
                        external_id=f"eSc_line_{index}{2 + i}",
                    ),
                    content=CONTENTS[index].get("body"),
                )
            LineTranscription.objects.create(
                transcription=transcription,
                line=Line.objects.create(
                    baseline=[[400, 260], [600, 260]],
                    mask=[[400, 250], [600, 250], [600, 270], [400, 270]],
                    document_part=part,
                    block=signature_block,
                    external_id=f"eSc_line_{index}5",
                ),
                content=CONTENTS[index].get("signature"),
            )

        self.all_regions_types = [title.pk, self.body.pk, signature.pk]

        self.include_images = False

        report = TaskReport.objects.create(
            user=user,
            label="Test report for export task",
            document=doc,
            method="imports.tasks.document_export",
        )

        self.params = [user, doc, report, transcription]

    def tearDown(self):
        shutil.rmtree(MEDIA_ROOT)

    def test_text_exporter_render(self, timezone_mock):
        exporter = TextExporter(
            self.all_parts_pks,
            self.all_regions_types,
            self.include_images,
            *self.params,
        )
        exporter.render()

        self.assertEqual(
            open(exporter.filepath).read(),
            open(f"{SAMPLES_DIR}/text_export_full.txt").read(),
        )

    def test_text_exporter_render_only_one_part(self, timezone_mock):
        parts_pk = [self.part.pk]
        exporter = TextExporter(
            parts_pk, self.all_regions_types, self.include_images, *self.params
        )
        exporter.render()

        self.assertEqual(
            open(exporter.filepath).read(),
            open(f"{SAMPLES_DIR}/text_export_only_first_part.txt").read(),
        )

    def test_text_exporter_render_only_one_region(self, timezone_mock):
        region_types = [self.body.pk]
        exporter = TextExporter(
            self.all_parts_pks, region_types, self.include_images, *self.params
        )
        exporter.render()

        self.assertEqual(
            open(exporter.filepath).read(),
            open(f"{SAMPLES_DIR}/text_export_only_body.txt").read(),
        )

        os.remove

    def test_pagexml_exporter_render(self, timezone_mock):
        exporter = PageXMLExporter(
            self.all_parts_pks,
            self.all_regions_types,
            self.include_images,
            *self.params,
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_xml_export_filename, self.part2_xml_export_filename, "METS.xml"],
            )
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "pagexml_export_full_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read(self.part2_xml_export_filename),
                "pagexml_export_full_part2.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_without_images.xml"
            ))

    def test_pagexml_exporter_render_only_one_part(self, timezone_mock):
        parts_pk = [self.part.pk]
        exporter = PageXMLExporter(
            parts_pk, self.all_regions_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(archive.namelist(), [self.part_xml_export_filename, "METS.xml"])
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "pagexml_export_full_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_only_part1_without_images.xml"
            ))

    def test_pagexml_exporter_render_only_one_region(self, timezone_mock):
        region_types = [self.body.pk]
        exporter = PageXMLExporter(
            self.all_parts_pks, region_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_xml_export_filename, self.part2_xml_export_filename, "METS.xml"],
            )
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "pagexml_export_only_body_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read(self.part2_xml_export_filename),
                "pagexml_export_only_body_part2.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_without_images.xml"
            ))

    def test_pagexml_exporter_render_with_images(self, timezone_mock):
        include_images = True
        exporter = PageXMLExporter(
            self.all_parts_pks, self.all_regions_types, include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [
                    self.part.filename,
                    self.part_xml_export_filename,
                    self.part2.filename,
                    self.part2_xml_export_filename,
                    "METS.xml"
                ],
            )
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "pagexml_export_full_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read(self.part2_xml_export_filename),
                "pagexml_export_full_part2.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_with_images.xml"
            ))

    def test_alto_exporter_render(self, timezone_mock):
        exporter = AltoExporter(
            self.all_parts_pks,
            self.all_regions_types,
            self.include_images,
            *self.params,
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_xml_export_filename, self.part2_xml_export_filename, "METS.xml"],
            )
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "alto_export_full_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read(self.part2_xml_export_filename),
                "alto_export_full_part2.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_without_images.xml"
            ))

    def test_alto_exporter_render_only_one_part(self, timezone_mock):
        parts_pk = [self.part.pk]
        exporter = AltoExporter(
            parts_pk, self.all_regions_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(archive.namelist(), [self.part_xml_export_filename, "METS.xml"])
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "alto_export_full_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_only_part1_without_images.xml"
            ))

    def test_alto_exporter_render_only_one_region(self, timezone_mock):
        region_types = [self.body.pk]
        exporter = AltoExporter(
            self.all_parts_pks, region_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_xml_export_filename, self.part2_xml_export_filename, "METS.xml"],
            )
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "alto_export_only_body_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read(self.part2_xml_export_filename),
                "alto_export_only_body_part2.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_without_images.xml"
            ))

    def test_alto_exporter_render_with_images(self, timezone_mock):
        include_images = True
        exporter = AltoExporter(
            self.all_parts_pks, self.all_regions_types, include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [
                    self.part.filename,
                    self.part_xml_export_filename,
                    self.part2.filename,
                    self.part2_xml_export_filename,
                    "METS.xml"
                ],
            )
            self.assertEqual(*format_xml_contents(
                archive.read(self.part_xml_export_filename),
                "alto_export_full_part1.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read(self.part2_xml_export_filename),
                "alto_export_full_part2.xml"
            ))
            self.assertEqual(*format_xml_contents(
                archive.read("METS.xml"),
                "mets_with_images.xml"
            ))

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_openiti_markdown_exporter_render(self, timezone_mock):
        exporter = OpenITIMARkdownExporter(
            self.all_parts_pks,
            self.all_regions_types,
            self.include_images,
            *self.params,
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_md_export_filename, self.part2_md_export_filename],
            )
            self.assertEqual(
                archive.read(self.part_md_export_filename),
                open(
                    f"{SAMPLES_DIR}/openiti_markdown_export_full_part1.mARkdown", "rb"
                ).read(),
            )
            self.assertEqual(
                archive.read(self.part2_md_export_filename),
                open(
                    f"{SAMPLES_DIR}/openiti_markdown_export_full_part2.mARkdown", "rb"
                ).read(),
            )

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_openiti_markdown_exporter_render_only_one_part(self, timezone_mock):
        parts_pk = [self.part.pk]
        exporter = OpenITIMARkdownExporter(
            parts_pk, self.all_regions_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(archive.namelist(), [self.part_md_export_filename])
            self.assertEqual(
                archive.read(self.part_md_export_filename),
                open(
                    f"{SAMPLES_DIR}/openiti_markdown_export_full_part1.mARkdown", "rb"
                ).read(),
            )

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_openiti_markdown_exporter_render_only_one_region(self, timezone_mock):
        region_types = [self.body.pk]
        exporter = OpenITIMARkdownExporter(
            self.all_parts_pks, region_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_md_export_filename, self.part2_md_export_filename],
            )
            self.assertEqual(
                archive.read(self.part_md_export_filename),
                open(
                    f"{SAMPLES_DIR}/openiti_markdown_export_only_body_part1.mARkdown",
                    "rb",
                ).read(),
            )
            self.assertEqual(
                archive.read(self.part2_md_export_filename),
                open(
                    f"{SAMPLES_DIR}/openiti_markdown_export_only_body_part2.mARkdown",
                    "rb",
                ).read(),
            )

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_openiti_markdown_exporter_render_with_images(self, timezone_mock):
        include_images = True
        exporter = OpenITIMARkdownExporter(
            self.all_parts_pks, self.all_regions_types, include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [
                    self.part.filename,
                    self.part_md_export_filename,
                    self.part2.filename,
                    self.part2_md_export_filename,
                ],
            )
            self.assertEqual(
                archive.read(self.part_md_export_filename),
                open(
                    f"{SAMPLES_DIR}/openiti_markdown_export_full_part1.mARkdown", "rb"
                ).read(),
            )
            self.assertEqual(
                archive.read(self.part2_md_export_filename),
                open(
                    f"{SAMPLES_DIR}/openiti_markdown_export_full_part2.mARkdown", "rb"
                ).read(),
            )

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_tei_xml_exporter_render(self, timezone_mock):
        exporter = TEIXMLExporter(
            self.all_parts_pks,
            self.all_regions_types,
            self.include_images,
            *self.params,
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_xml_export_filename, self.part2_xml_export_filename],
            )
            self.assertEqual(
                archive.read(self.part_xml_export_filename),
                open(f"{SAMPLES_DIR}/tei_xml_export_full_part1.xml", "rb").read(),
            )
            self.assertEqual(
                archive.read(self.part2_xml_export_filename),
                open(f"{SAMPLES_DIR}/tei_xml_export_full_part2.xml", "rb").read(),
            )

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_tei_xml_exporter_render_only_one_part(self, timezone_mock):
        parts_pk = [self.part.pk]
        exporter = TEIXMLExporter(
            parts_pk, self.all_regions_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(archive.namelist(), [self.part_xml_export_filename])
            self.assertEqual(
                archive.read(self.part_xml_export_filename),
                open(f"{SAMPLES_DIR}/tei_xml_export_full_part1.xml", "rb").read(),
            )

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_tei_xml_exporter_render_only_one_region(self, timezone_mock):
        region_types = [self.body.pk]
        exporter = TEIXMLExporter(
            self.all_parts_pks, region_types, self.include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [self.part_xml_export_filename, self.part2_xml_export_filename],
            )
            self.assertEqual(
                archive.read(self.part_xml_export_filename),
                open(
                    f"{SAMPLES_DIR}/tei_xml_export_only_body_part1.xml",
                    "rb",
                ).read(),
            )
            self.assertEqual(
                archive.read(self.part2_xml_export_filename),
                open(
                    f"{SAMPLES_DIR}/tei_xml_export_only_body_part2.xml",
                    "rb",
                ).read(),
            )

    @override_settings(VERSION_DATE="1.0.0-testing")
    def test_tei_xml_exporter_render_with_images(self, timezone_mock):
        include_images = True
        exporter = TEIXMLExporter(
            self.all_parts_pks, self.all_regions_types, include_images, *self.params
        )
        exporter.render()

        with ZipFile(exporter.filepath, "r") as archive:
            self.assertListEqual(
                archive.namelist(),
                [
                    self.part.filename,
                    self.part_xml_export_filename,
                    self.part2.filename,
                    self.part2_xml_export_filename,
                ],
            )
            self.assertEqual(
                archive.read(self.part_xml_export_filename),
                open(f"{SAMPLES_DIR}/tei_xml_export_full_part1.xml", "rb").read(),
            )
            self.assertEqual(
                archive.read(self.part2_xml_export_filename),
                open(f"{SAMPLES_DIR}/tei_xml_export_full_part2.xml", "rb").read(),
            )
