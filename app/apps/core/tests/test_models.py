import json
import os
import subprocess
from shutil import copyfile
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from core.models import LineTranscription, Transcription
from core.tests.factory import CoreFactoryTestCase


class DocumentPartTestCase(CoreFactoryTestCase):
    """Unit tests for DocumentPart model"""
    reset_sequences = True  # ensure pks are reset after each test

    def makeTranscriptionContent(self):
        """Set up transcription content, witness"""
        self.part = self.factory.make_part()
        self.part_2 = self.factory.make_part(document=self.part.document)
        self.part_3 = self.factory.make_part(document=self.part.document)
        self.transcription = self.factory.make_transcription(document=self.part.document)
        self.factory.make_content(self.part, transcription=self.transcription)
        self.factory.make_content(self.part_2, transcription=self.transcription)
        self.factory.make_content(self.part_3, transcription=self.transcription)
        self.user = self.factory.make_user()
        self.witness = self.factory.make_witness(owner=self.user)
        self.n_gram = 4
        self.max_offset = 20
        self.beam_size = 10
        self.gap = 600
        self.region_types = [rt.id for rt in self.part.document.valid_block_types.all()] + ["Orphan", "Undefined"]

        tpk = self.transcription.pk
        dpk = self.part.document.pk
        wpk = self.witness.pk
        self.outdir = f"{settings.MEDIA_ROOT}/alignments/document-{dpk}/t{tpk}+w{wpk}"

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_align(self, mock_subprocess, mock_hex):
        """Unit tests for DocumentPart text alignment function"""
        self.makeTranscriptionContent()

        # mock hex output so that we can get consistent file naming
        mock_hex.return_value = "0x1"

        # should call subprocess.check_call with passim (seriatim), n-gram of 4, correct input
        # file/output directory
        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=True,
            full_doc=False,
            threshold=0.0,
            region_types=self.region_types,
            layer_name=None,
            beam_size=0,
            gap=self.gap,
        )
        # mocking subprocess because we don't expect test runner to run java, but this test will
        # use real passim output later
        mock_subprocess.check_call.assert_called_with([
            "seriatim",
            "--docwise",
            "--floating-ngrams",
            "-n", str(self.n_gram),
            "--max-offset", str(self.max_offset),
            "--gap", str(self.gap),
            "--fields", "ref",
            "--filterpairs", "ref = 1 AND ref2 = 0",
            f"{self.outdir}-1.json",
            f"{self.outdir}-1",
        ])

        # mock file cleanup-related modules so we can read the input json
        with patch("core.models.shutil") as mock_shutil:
            # should produce an input json file (json.load will error otherwise)
            self.part.document.align(
                [self.part.pk],
                self.transcription.pk,
                self.witness.pk,
                self.n_gram,
                self.max_offset,
                merge=True,
                full_doc=False,
                threshold=0.0,
                region_types=self.region_types,
                layer_name=None,
                beam_size=0,
                gap=self.gap,
            )
            infile = open(f"{self.outdir}-1.json")
            in_lines = infile.readlines()
            in_json = []
            for line in in_lines:
                in_json.append(json.loads(line))

            # should be a list of length 2 (1 input document + 1 witness txt)
            self.assertEqual(len(in_json), 2)

            # since full_doc = False, should have 30 lines (1980 chars) from only single page
            for entry in in_json:
                if entry["id"] != "witness":
                    self.assertEqual(len(entry["lineIDs"]), 30)
                    self.assertEqual(len(entry["text"]), 1950)

            # should have an entry with id "witness" and text of witness txt
            witness_dict = next(filter(lambda d: d["id"] == "witness", in_json))
            f = open(os.path.join(os.path.dirname(__file__), "assets", "alignment/witness.txt"), "r")
            self.assertEqual(witness_dict["text"], f.read())

            # should remove the output directory
            mock_shutil.rmtree.assert_called_with(f"{self.outdir}-1", ignore_errors=True)

        # should create a new transcription layer--will raise error if not
        new_trans = Transcription.objects.get(
            name="Aligned: fake_textual_witness + test trans",
            document=self.part.document,
        )

        # should create LineTranscriptions with the old content of each line, since we do not have
        # any real passim output yet
        for line in self.part.lines.all():
            new_lt = LineTranscription.objects.get(line=line, transcription=new_trans)
            old_lt = LineTranscription.objects.get(line=line, transcription=self.transcription)
            self.assertEqual(new_lt.content, old_lt.content)

        # should set workflow state after completion
        self.part.refresh_from_db()
        self.assertEqual(self.part.workflow_state, self.part.WORKFLOW_STATE_ALIGNED)

    @patch("core.models.subprocess")
    def test_align_deleted_line(self, _):
        """Unit tests for DocumentPart text alignment when a line is missing a LineTranscription"""
        self.makeTranscriptionContent()
        # if we delete one of the LineTranscriptions and run again, should set content of the new
        # LineTranscription for that line to an empty string
        lt_to_remove = LineTranscription.objects.get(line=self.part.lines.first(), transcription=self.transcription)
        lt_to_remove.delete()
        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=True,
            full_doc=False,
            threshold=0.0,
            region_types=self.region_types,
            layer_name=None,
            beam_size=0,
            gap=self.gap,
        )
        new_trans = Transcription.objects.get(
            name="Aligned: fake_textual_witness + test trans",
            document=self.part.document,
        )
        with self.assertRaises(LineTranscription.DoesNotExist):
            # should not have created a LineTranscription for the missing line
            LineTranscription.objects.get(line=self.part.lines.first(), transcription=new_trans)

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_align_real_data(self, _, mock_hex):
        """Unit tests for DocumentPart text alignment with real output data from passim"""
        self.makeTranscriptionContent()
        mock_hex.return_value = "0x1"

        # save some real passim output from our fixture into the outdir
        alignment = os.path.join(os.path.dirname(__file__), "assets", "alignment/out.json")
        os.makedirs(f"{self.outdir}-1/out.json")
        copyfile(alignment, f"{self.outdir}-1/out.json/out.json")  # mimicking actual passim output format

        # re-run the alignment with the real passim output
        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=True,
            full_doc=False,
            threshold=0.0,
            region_types=self.region_types,
            layer_name=None,
            beam_size=0,
            gap=self.gap,
        )

        # line we know should have changed content based on witness.txt and out.json
        new_trans = Transcription.objects.get(
            name="Aligned: fake_textual_witness + test trans",
            document=self.part.document,
        )
        line = self.part.lines.get(pk=30)
        new_lt = LineTranscription.objects.get(line=line, transcription=new_trans)
        old_lt = LineTranscription.objects.get(line=line, transcription=self.transcription)
        self.assertNotEqual(new_lt.content, old_lt.content)
        self.assertEqual(new_lt.content, "NoSAYQctujgZ! eAiFtfdymtfsX REKIA P g jm naYstrtUuCqsaiCNXaHR")

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_align_no_merge(self, _, mock_hex):
        """Test alignment without merging original transcription (i.e. not using original text for non-matching lines)"""
        self.makeTranscriptionContent()
        mock_hex.return_value = "0x1"

        # save some real passim output from our fixture into the outdir
        alignment = os.path.join(os.path.dirname(__file__), "assets", "alignment/out.json")
        os.makedirs(f"{self.outdir}-1/out.json")
        copyfile(alignment, f"{self.outdir}-1/out.json/out.json")  # mimicking actual passim output format

        # run the alignment with the real passim output, and merge = False
        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=False,
            full_doc=False,
            threshold=0.0,
            region_types=self.region_types,
            layer_name=None,
            beam_size=0,
            gap=self.gap,
        )
        new_trans = Transcription.objects.get(
            name="Aligned: fake_textual_witness + test trans",
            document=self.part.document,
        )
        # line we know should have NO transcription based on witness.txt and out.json
        line = self.part.lines.get(pk=23)
        with self.assertRaises(LineTranscription.DoesNotExist):
            LineTranscription.objects.get(line=line, transcription=new_trans)

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_align_exception(self, mock_subprocess, mock_hex):
        """Test exception raised during subprocess"""
        self.makeTranscriptionContent()
        mock_hex.return_value = "0x1"

        mock_subprocess.check_call.side_effect = subprocess.CalledProcessError(2, "test")

        # should cleanup files on exception
        with patch("core.models.shutil") as mock_shutil:
            with self.assertRaises(Exception):
                # should still raise the exception
                self.part.document.align(
                    [self.part.pk],
                    self.transcription.pk,
                    self.witness.pk,
                    self.n_gram,
                    self.max_offset,
                    merge=True,
                    full_doc=False,
                    threshold=0.0,
                    region_types=self.region_types,
                    layer_name=None,
                    beam_size=0,
                    gap=self.gap,
                )
            # should remove the output directory
            mock_shutil.rmtree.assert_called_with(f"{self.outdir}-1", ignore_errors=True)

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_align_fulldoc(self, _, mock_hex):
        """Test alignment using the full document transcription instead of each page in Passim"""
        self.makeTranscriptionContent()
        mock_hex.return_value = "0x1"

        # mock file cleanup-related modules so we can read the input json
        with patch("core.models.shutil"):
            # should produce an input json file (json.load will error otherwise)
            self.part.document.align(
                [self.part.pk],
                self.transcription.pk,
                self.witness.pk,
                self.n_gram,
                self.max_offset,
                merge=True,
                full_doc=True,
                threshold=0.0,
                region_types=self.region_types,
                layer_name=None,
                beam_size=0,
                gap=self.gap,
            )
            infile = open(f"{self.outdir}-1.json")
            in_lines = infile.readlines()
            in_json = []
            for line in in_lines:
                in_json.append(json.loads(line))

            # since full_doc = False, should have 90 lines, 5940 chars, combining pages from whole document
            for entry in in_json:
                if entry["id"] != "witness":
                    self.assertEqual(len(entry["lineIDs"]), 90)
                    self.assertEqual(len(entry["text"]), 5850)

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_align_threshold(self, _, mock_hex):
        """Test alignment with a threshold higher than 0.0 for match length comparisons"""
        self.makeTranscriptionContent()
        mock_hex.return_value = "0x1"

        # save some real passim output from our fixture into the outdir
        alignment = os.path.join(os.path.dirname(__file__), "assets", "alignment/out.json")
        os.makedirs(f"{self.outdir}-1/out.json")
        copyfile(alignment, f"{self.outdir}-1/out.json/out.json")  # mimicking actual passim output format

        # run the alignment with the real passim output, and threshold = 0.8
        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=False,
            full_doc=False,
            threshold=0.8,
            region_types=self.region_types,
            layer_name=None,
            beam_size=0,
            gap=self.gap,
        )
        new_trans = Transcription.objects.get(
            name="Aligned: fake_textual_witness + test trans",
            document=self.part.document,
        )
        # line we know should not get transcription based on the match threshold (its length in witness.txt is much shorter)
        line = self.part.lines.get(pk=7)
        with self.assertRaises(LineTranscription.DoesNotExist):
            LineTranscription.objects.get(line=line, transcription=new_trans)

        # re-copy real alignment output for second alignment
        os.makedirs(f"{self.outdir}-1/out.json")
        copyfile(alignment, f"{self.outdir}-1/out.json/out.json")

        # run the alignment with threshold = 0.2
        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=False,
            full_doc=False,
            threshold=0.2,
            region_types=self.region_types,
            layer_name=None,
            beam_size=0,
            gap=self.gap,
        )
        new_trans = Transcription.objects.get(
            name="Aligned: fake_textual_witness + test trans",
            document=self.part.document,
        )
        # the same line should now have some content based on the lowered threshold
        line = self.part.lines.get(pk=7)
        new_lt = LineTranscription.objects.get(line=line, transcription=new_trans)
        old_lt = LineTranscription.objects.get(line=line, transcription=self.transcription)
        self.assertNotEqual(new_lt.content, old_lt.content)
        self.assertNotEqual(new_lt.content, "")

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_region_filters(self, _, mock_hex):
        """Test region filters in alignment function"""
        self.makeTranscriptionContent()
        mock_hex.return_value = "0x1"

        # mock file cleanup-related modules so we can read the input json
        with patch("core.models.shutil"):
            # when region_types is empty, should have 0 lines (exclude all region types)
            self.part.document.align(
                [self.part.pk],
                self.transcription.pk,
                self.witness.pk,
                self.n_gram,
                self.max_offset,
                merge=True,
                full_doc=True,
                threshold=0.0,
                region_types=[],
                layer_name=None,
                beam_size=0,
                gap=self.gap,
            )
            infile = open(f"{self.outdir}-1.json")
            in_lines = infile.readlines()
            in_json = []
            for line in in_lines:
                in_json.append(json.loads(line))
            for entry in in_json:
                if entry["id"] != "witness":
                    self.assertEqual(len(entry["lineIDs"]), 0)

            # when region_types includes exactly one of the three we created in
            # makeTranscriptionContent, should have 30 lines
            self.part.document.align(
                [self.part.pk],
                self.transcription.pk,
                self.witness.pk,
                self.n_gram,
                self.max_offset,
                merge=True,
                full_doc=True,
                threshold=0.0,
                region_types=[self.part.document.valid_block_types.first().id],
                layer_name=None,
                beam_size=0,
                gap=self.gap,
            )
            infile = open(f"{self.outdir}-1.json")
            in_lines = infile.readlines()
            in_json = []
            for line in in_lines:
                in_json.append(json.loads(line))
            for entry in in_json:
                if entry["id"] != "witness":
                    self.assertEqual(len(entry["lineIDs"]), 30)

            # when region_types is all the valid ones for the document, should have 90 lines
            self.part.document.align(
                [self.part.pk],
                self.transcription.pk,
                self.witness.pk,
                self.n_gram,
                self.max_offset,
                merge=True,
                full_doc=True,
                threshold=0.0,
                region_types=self.region_types,
                layer_name=None,
                beam_size=0,
                gap=self.gap,
            )
            infile = open(f"{self.outdir}-1.json")
            in_lines = infile.readlines()
            in_json = []
            for line in in_lines:
                in_json.append(json.loads(line))
            for entry in in_json:
                if entry["id"] != "witness":
                    self.assertEqual(len(entry["lineIDs"]), 90)

    @patch("core.models.subprocess")
    def test_layer_name(self, _):
        """Unit test for text alignment layer name setting"""
        self.makeTranscriptionContent()

        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=True,
            full_doc=False,
            threshold=0.0,
            region_types=self.region_types,
            layer_name="test layer",
            beam_size=0,
            gap=self.gap,
        )

        # Should not use default naming scheme
        with self.assertRaises(ObjectDoesNotExist):
            Transcription.objects.get(
                name="Aligned: fake_textual_witness + test trans",
                document=self.part.document,
            )

        # should use specified layer name and not raise error
        Transcription.objects.get(
            name="test layer",
            document=self.part.document,
        )

    @patch("core.models.hex")
    @patch("core.models.subprocess")
    def test_beam_size(self, mock_subprocess, mock_hex):
        """Unit tests for DocumentPart text alignment function"""
        self.makeTranscriptionContent()

        # mock hex output so that we can get consistent file naming
        mock_hex.return_value = "0x1"

        # should call subprocess.check_call with the correct beam_size and ignore max_offset
        self.part.document.align(
            [self.part.pk],
            self.transcription.pk,
            self.witness.pk,
            self.n_gram,
            self.max_offset,
            merge=True,
            full_doc=False,
            threshold=0.0,
            region_types=self.region_types,
            layer_name=None,
            beam_size=self.beam_size,
            gap=self.gap,
        )
        # mocking subprocess because we don't expect test runner to run java, but this test will
        # use real passim output later
        mock_subprocess.check_call.assert_called_with([
            "seriatim",
            "--docwise",
            "--floating-ngrams",
            "-n", str(self.n_gram),
            "--beam", str(self.beam_size),
            "--gap", str(self.gap),
            "--fields", "ref",
            "--filterpairs", "ref = 1 AND ref2 = 0",
            f"{self.outdir}-1.json",
            f"{self.outdir}-1",
        ])
