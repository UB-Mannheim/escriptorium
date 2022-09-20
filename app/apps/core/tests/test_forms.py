import os
from posixpath import splitext
from unittest.mock import patch

from django.forms import ValidationError

from core.forms import AlignForm, RegionTypesFormMixin
from core.models import BlockType, DocumentPart
from core.tests.factory import CoreFactoryTestCase


class RegionTypesFormMixinTestCase(CoreFactoryTestCase):
    """Unit tests for region types form mixin"""

    def make_doc_and_block(self):
        self.document = self.factory.make_document(name="document")
        self.block_type = BlockType.objects.create(name="Block", public=True, default=True)
        self.document.valid_block_types.add(self.block_type)

    def test_init(self):
        """Should initialize region types choices, selection"""
        self.make_doc_and_block()

        form_mixin = RegionTypesFormMixin(document=self.document)

        # should set choices from document's valid region types
        assert (self.block_type.id, "Block") in form_mixin.fields["region_types"].choices
        # should include undefined choice
        assert ('Undefined', '(Undefined region type)') in form_mixin.fields["region_types"].choices
        # should set all checked by default
        assert self.block_type.id in form_mixin.fields["region_types"].initial


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
        self.witness = self.factory.make_witness(owner=self.user)
        self.witness_2 = self.factory.make_witness(owner=self.user)

    def test_init(self):
        """Test form initialization"""
        self.makeTranscriptionContent()

        align_form = AlignForm(document=self.part.document, user=self.user)

        # queryset should only include transcriptions on self.part.document
        assert self.transcription in align_form.fields["transcription"].queryset.all()
        assert self.transcription_2 not in align_form.fields["transcription"].queryset.all()

    def test_clean(self):
        """Test form validation"""
        self.makeTranscriptionContent()

        align_form = AlignForm(document=self.part.document, user=self.user)

        # should not raise error with witness_file only
        align_form.cleaned_data = {"witness_file": "test.txt", "transcription": self.transcription}
        align_form.clean()

        # should not raise error with existing_witness only
        align_form.cleaned_data = {"existing_witness": self.witness, "transcription": self.transcription}
        align_form.clean()

        # should raise error with existing_witness and witness_file
        align_form.cleaned_data = {
            "witness_file": "test.txt",
            "existing_witness": self.witness,
            "transcription": self.transcription,
        }
        with self.assertRaises(ValidationError):
            align_form.clean()

        # should raise error with neither
        align_form.cleaned_data = {"transcription": self.transcription}
        with self.assertRaises(ValidationError):
            align_form.clean()

        # should raise error when layer name == transcription name
        align_form.cleaned_data = {
            "witness_file": "test.txt",
            "transcription": self.transcription,
            "layer_name": self.transcription.name,
        }
        with self.assertRaises(ValidationError):
            align_form.clean()

        # should not raise error when layer name != transcription name
        align_form.cleaned_data = {
            "witness_file": "test.txt",
            "transcription": self.transcription,
            "layer_name": "example",
        }
        align_form.clean()

        # should raise error when max offset and beam size both present and > 0
        align_form.cleaned_data = {
            "witness_file": "test.txt",
            "transcription": self.transcription,
            "layer_name": "example",
            "max_offset": 20,
            "beam_size": 10,
        }
        with self.assertRaises(ValidationError):
            align_form.clean()

        # should not raise error when max offset and beam size both present, but beam_size is 0
        align_form.cleaned_data = {
            "witness_file": "test.txt",
            "transcription": self.transcription,
            "layer_name": "example",
            "max_offset": 20,
            "beam_size": 0,
        }
        align_form.clean()

    @patch("core.forms.TextualWitness")
    @patch("core.forms.Document.queue_alignment")
    def test_process(self, mock_task, mock_textualwitness_class):
        """Test form processing"""
        self.makeTranscriptionContent()

        align_form = AlignForm(document=self.part.document, user=self.user)
        parts_qs = DocumentPart.objects.filter(pk=self.part.pk)

        align_form.cleaned_data = {
            "transcription": self.transcription,
            "existing_witness": self.witness,
            "n_gram": 2,
            "parts": parts_qs,
            "max_offset": 20,
            "merge": False,
            "full_doc": True,
            "threshold": 0.8,
            "region_types": ["Orphan", "Undefined"],
            "layer_name": "example",
            "beam_size": 10,
        }

        align_form.process()

        # should call align task with passed user, transcription, witness, n_gram, etc
        mock_task.assert_called_with(
            parts_qs=parts_qs,
            user_pk=self.user.pk,
            transcription_pk=self.transcription.pk,
            witness_pk=self.witness.pk,
            n_gram=2,
            max_offset=20,
            merge=False,
            full_doc=True,
            threshold=0.8,
            region_types=["Orphan", "Undefined"],
            layer_name="example",
            beam_size=10,
        )

        # should create a new textual witness from a passed file
        file = open(os.path.join(os.path.dirname(__file__), "assets", "alignment/witness.txt"), "rb")
        align_form.cleaned_data = {
            "transcription": self.transcription,
            "witness_file": file,
            "n_gram": 2,
            "max_offset": 20,
            "parts": parts_qs,
            "merge": False,
            "full_doc": True,
            "threshold": 0.8,
            "region_types": ["Orphan", "Undefined"],
            "layer_name": "example",
        }
        align_form.process()
        mock_textualwitness_class.assert_called_with(
            file=file,
            name=splitext(file.name)[0],
            owner=self.user,
        )

        # should call align task with default n_gram (25), full_doc (True), max_offset (0),
        # region_types, layer_name (None), threshold (0.8), and beam_size (20) when none provided
        align_form.cleaned_data = {
            "transcription": self.transcription,
            "existing_witness": self.witness,
            "parts": parts_qs,
            "merge": False,
        }
        align_form.process()
        mock_task.assert_called_with(
            parts_qs=parts_qs,
            user_pk=self.user.pk,
            transcription_pk=self.transcription.pk,
            witness_pk=self.witness.pk,
            n_gram=25,
            max_offset=0,
            merge=False,
            full_doc=True,
            threshold=0.8,
            region_types=["Orphan", "Undefined"],
            layer_name=None,
            beam_size=20,
        )

        # should respect threshold of 0.0 and not revert to default 0.8
        align_form.cleaned_data = {
            "transcription": self.transcription,
            "existing_witness": self.witness,
            "parts": parts_qs,
            "merge": False,
            "threshold": 0.0,
        }
        align_form.process()
        mock_task.assert_called_with(
            parts_qs=parts_qs,
            user_pk=self.user.pk,
            transcription_pk=self.transcription.pk,
            witness_pk=self.witness.pk,
            n_gram=25,
            max_offset=0,
            merge=False,
            full_doc=True,
            threshold=0.0,
            region_types=["Orphan", "Undefined"],
            layer_name=None,
            beam_size=20,
        )
