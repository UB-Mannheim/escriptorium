import json
import os
from shutil import copyfile
from unittest.mock import patch

from django.conf import settings

from core.models import LineTranscription, Transcription
from core.tests.factory import CoreFactoryTestCase


class DocumentPartTestCase(CoreFactoryTestCase):
    """Unit tests for DocumentPart model"""
    reset_sequences = True  # ensure pks are reset after each test

    def makeTranscriptionContent(self):
        """Set up transcription content, witness"""
        self.part = self.factory.make_part()
        self.factory.make_part(document=self.part.document)
        self.factory.make_part(document=self.part.document)
        self.transcription = self.factory.make_transcription(document=self.part.document)
        self.factory.make_content(self.part, transcription=self.transcription)
        self.user = self.factory.make_user()
        self.witness = self.factory.make_witness(document=self.part.document, owner=self.user)
        self.n_gram = 4

        ppk = self.part.pk
        tpk = self.transcription.pk
        dpk = self.part.document.pk
        wpk = self.witness.pk
        self.outdir = f"{settings.MEDIA_ROOT}/alignments/document-{dpk}/p{ppk}-t{tpk}+w{wpk}-{self.n_gram}gram"

    @patch("core.models.subprocess")
    def test_align(self, mock_subprocess):
        """Unit tests for DocumentPart text alignment function"""
        self.makeTranscriptionContent()

        # should call subprocess.check_call with passim (seriatim), n-gram of 4, correct input
        # file/output directory
        self.part.align(self.transcription.pk, self.witness.pk, self.n_gram)
        # mocking subprocess because we don't expect test runner to run java, but this test will
        # use real passim output later
        mock_subprocess.check_call.assert_called_with([
            "seriatim",
            "--linewise",
            "--floating-ngrams",
            "-n", f"{self.n_gram}",
            "--fields", "ref",
            "--filterpairs", "ref = 1 AND ref2 = 0",
            f"{self.outdir}.json",
            self.outdir,
        ])

        # mock file cleanup-related modules so we can read the input json
        with patch("core.models.remove") as mock_remove:
            with patch("core.models.shutil") as mock_shutil:
                # should produce an input json file (json.load will error otherwise)
                self.part.align(self.transcription.pk, self.witness.pk, self.n_gram)
                infile = open(f"{self.outdir}.json")
                in_json = json.load(infile)

                # should be a list of length 31 (30 transcription lines + witness txt)
                self.assertEqual(len(in_json), 31)

                # should have an entry with id "witness" and text of witness txt
                witness_dict = next(filter(lambda d: d["id"] == "witness", in_json))
                f = open(os.path.join(os.path.dirname(__file__), "assets", "alignment/witness.txt"), "r")
                self.assertEqual(witness_dict["text"], f.read())

                # should remove the input json
                mock_remove.assert_called_with(f"{self.outdir}.json")
                # should remove the output directory
                mock_shutil.rmtree.assert_called_with(self.outdir)

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
        self.assertEqual(self.part.workflow_state, self.part.WORKFLOW_STATE_ALIGNED)

    @patch("core.models.subprocess")
    def test_align_deleted_line(self, _):
        """Unit tests for DocumentPart text alignment when a line is missing a LineTranscription"""
        self.makeTranscriptionContent()
        # if we delete one of the LineTranscriptions and run again, should set content of the new
        # LineTranscription for that line to an empty string
        lt_to_remove = LineTranscription.objects.get(line=self.part.lines.first(), transcription=self.transcription)
        lt_to_remove.delete()
        self.part.align(self.transcription.pk, self.witness.pk, self.n_gram)
        new_trans = Transcription.objects.get(
            name="Aligned: fake_textual_witness + test trans",
            document=self.part.document,
        )
        new_lt = LineTranscription.objects.get(line=self.part.lines.first(), transcription=new_trans)
        self.assertEqual(new_lt.content, "")

    @patch("core.models.subprocess")
    def test_align_real_data(self, _):
        """Unit tests for DocumentPart text alignment with real output data from passim"""
        self.makeTranscriptionContent()

        # save some real passim output from our fixture into the outdir
        alignment = os.path.join(os.path.dirname(__file__), "assets", "alignment/out.json")
        os.makedirs(f"{self.outdir}/out.json")
        copyfile(alignment, f"{self.outdir}/out.json/out.json")  # mimicking actual passim output format

        # re-run the alignment with the real passim output
        self.part.align(self.transcription.pk, self.witness.pk, self.n_gram)

        # line we know should have changed content based on witness.txt and out.json
        new_trans = Transcription.objects.get(
            name=f"Aligned: fake_textual_witness + test trans ({self.n_gram}gram)",
            document=self.part.document,
        )
        line = self.part.lines.get(pk=30)
        new_lt = LineTranscription.objects.get(line=line, transcription=new_trans)
        old_lt = LineTranscription.objects.get(line=line, transcription=self.transcription)
        self.assertNotEqual(new_lt.content, old_lt.content)
        self.assertEqual(new_lt.content, "NoSAYQctujgZ! eAiFtfdymtfsX REKIA P g jm naYstrtUuCqsaiCNXaHR")

    @patch("core.models.subprocess")
    def test_align_exception(self, mock_subprocess):
        """Test exception raised during subprocess"""
        self.makeTranscriptionContent()

        mock_subprocess.check_call.side_effect = Exception("error")

        # should cleanup files on exception
        with patch("core.models.remove") as mock_remove:
            with patch("core.models.shutil") as mock_shutil:
                with self.assertRaises(Exception):
                    # should still raise the exception
                    self.part.align(self.transcription.pk, self.witness.pk, self.n_gram)
                # should remove the input json
                mock_remove.assert_called_with(f"{self.outdir}.json")
                # should remove the output directory
                mock_shutil.rmtree.assert_called_with(self.outdir)
