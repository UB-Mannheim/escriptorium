import os
from posixpath import splitext
from unittest.mock import patch

from django.forms import ValidationError

from core.forms import AlignForm
from core.tests.factory import CoreFactoryTestCase


class AlignFormTestCase(CoreFactoryTestCase):
    """Unit tests for text alignment form"""

    def makeTranscriptionContent(self):
        """Set up transcriptions, witnesses"""
        self.part = self.factory.make_part()
        self.factory.make_part(document=self.part.document)
        self.document_2 = self.factory.make_document(name="document 2")
        self.transcription = self.factory.make_transcription(document=self.part.document)
        self.transcription_2 = self.factory.make_transcription(document=self.document_2)
        self.user = self.factory.make_user()
        self.witness = self.factory.make_witness(document=self.part.document, owner=self.user)
        self.witness_2 = self.factory.make_witness(document=self.document_2, owner=self.user)

    def test_init(self):
        """Test form initialization"""
        self.makeTranscriptionContent()

        align_form = AlignForm(document=self.part.document, user=self.user)

        # queryset should only include transcriptions on self.part.document
        assert self.transcription in align_form.fields["transcription"].queryset.all()
        assert self.transcription_2 not in align_form.fields["transcription"].queryset.all()

        # queryset should only include witnesses on self.part.document
        assert self.witness in align_form.fields["existing_witness"].queryset.all()
        assert self.witness_2 not in align_form.fields["existing_witness"].queryset.all()

    def test_clean(self):
        """Test form validation"""
        self.makeTranscriptionContent()

        align_form = AlignForm(document=self.part.document, user=self.user)

        # should not raise error with witness_file only
        align_form.cleaned_data = {"witness_file": "test.txt"}
        align_form.clean()

        # should not raise error with existing_witness only
        align_form.cleaned_data = {"existing_witness": self.witness}
        align_form.clean()

        # should raise error with existing_witness and witness_file
        align_form.cleaned_data = {"witness_file": "test.txt", "existing_witness": self.witness}
        with self.assertRaises(ValidationError):
            align_form.clean()

        # should raise error with neither
        align_form.cleaned_data = {}
        with self.assertRaises(ValidationError):
            align_form.clean()

    @patch("core.forms.TextualWitness")
    @patch("core.forms.DocumentPart.task")
    def test_process(self, mock_task, mock_textualwitness_class):
        """Test form processing"""
        self.makeTranscriptionContent()

        align_form = AlignForm(document=self.part.document, user=self.user)

        align_form.cleaned_data = {
            "transcription": self.transcription,
            "existing_witness": self.witness,
            "n_gram": 2,
            "parts": [self.part],
        }

        align_form.process()

        # should call align task with passed user, transcription, and witness, and set n_gram
        mock_task.assert_called_with(
            "align",
            user_pk=self.user.pk,
            transcription_pk=self.transcription.pk,
            witness_pk=self.witness.pk,
            n_gram=2
        )

        # should create a new textual witness from a passed file
        file = open(os.path.join(os.path.dirname(__file__), "assets", "alignment/witness.txt"), "rb")
        align_form.cleaned_data = {
            "transcription": self.transcription,
            "witness_file": file,
            "n_gram": 2,
            "parts": [self.part],
        }
        align_form.process()
        mock_textualwitness_class.assert_called_with(
            file=file,
            name=splitext(file.name)[0],
            document=self.part.document,
            owner=self.user,
        )

        # should call align task with default n_gram (4) when none provided
        align_form.cleaned_data = {
            "transcription": self.transcription,
            "existing_witness": self.witness,
            "parts": [self.part],
        }
        align_form.process()
        mock_task.assert_called_with(
            "align",
            user_pk=self.user.pk,
            transcription_pk=self.transcription.pk,
            witness_pk=self.witness.pk,
            n_gram=4
        )
