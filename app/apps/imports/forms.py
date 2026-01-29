import io
import json
import os

import requests
from bootstrap.forms import BootstrapFormMixin
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext as _

from core.forms import RegionTypesFormMixin
from core.models import DocumentPart, Transcription
from imports import fetch
from imports.export import ALTO_FORMAT, ENABLED_EXPORTERS
from imports.models import DocumentImport
from imports.parsers import ParseError, make_parser
from imports.tasks import document_export, document_import
from users.consumers import send_event


class FileImportError(Exception):
    pass


def clean_uri(uri, document, tempfile, is_mets=False, mets_base_uri=None,
              check_domain=True):
    try:
        headers = {
            'User-Agent': 'eScriptorium'
        }
        resp = fetch.get(uri, headers=headers, check_domain=check_domain)
        resp.raise_for_status()
        content = resp.content
        buf = io.BytesIO(content)
        buf.name = tempfile
        parser = make_parser(document, buf,
                             mets_describer=is_mets,
                             mets_base_uri=mets_base_uri)
        parser.validate()
        return content, parser.total
    except requests.exceptions.HTTPError as e:
        raise FileImportError(_("Failed to download the document pointed to by the given uri ({error}).").format(error=e))
    except requests.exceptions.RequestException:
        raise FileImportError(_("The document is unreachable, unreadable or the host timed out."))
    except requests.exceptions.SSLError:
        raise forms.ValidationError(_("The document cannot be downloaded, certificate verify failed."))
    except json.decoder.JSONDecodeError:
        raise FileImportError(_("The document pointed to by the given uri doesn't seem to be valid json."))
    except fetch.UnsafeUriError as e:
        raise FileImportError(e.args[0])
    except ParseError as e:
        msg = _("Couldn't parse the given file or its validation failed")
        if len(e.args):
            msg += ": %s" % e.args[0]
        raise FileImportError(msg)


def clean_import_uri(uri, document, tmp_file_name, is_mets=False, mets_base_uri=None):
    # the domain allowlist, the scheme and the address checks all live in
    # fetch.validate_uri now, so they apply to redirect targets too
    return clean_uri(uri, document, tmp_file_name, is_mets=is_mets, mets_base_uri=mets_base_uri)


def clean_upload_file(upload_file, document, user):
    try:
        # If quotas are enforced, define if the user can upload ZIP and PDF files
        allowed = settings.DISABLE_QUOTAS or user.has_free_disk_storage()
        parser = make_parser(document, upload_file, zip_allowed=allowed, pdf_allowed=allowed)
        parser.validate()
    except ParseError as e:
        msg = _("Couldn't parse the given file or its validation failed")
        if len(e.args):
            msg += ": %s" % e.args[0]
        raise FileImportError(msg)
    except ValueError as e:
        raise FileImportError(repr(e))
    return parser


class ImportForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField(
        required=False,
        max_length=256,
        help_text=_("The name of the target transcription. Will default to '{format} Import'."))
    upload_file = forms.FileField(
        required=False,
        help_text=_("A single ALTO or PAGE XML file, or a zip file."))
    override = forms.BooleanField(
        initial=False, required=False,
        label=_("Override existing segmentation."),
        help_text=_("Destroys existing regions, lines and any bound transcription before importing."))
    iiif_uri = forms.URLField(
        required=False,
        label=_("IIIF manifest URI"),
        help_text=_("exp: https://gallica.bnf.fr/iiif/ark:/12148/btv1b10224708f/manifest.json"))
    resume_import = forms.BooleanField(
        required=False,
        label=_("Resume previous import"),
        initial=True)
    mets = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(),
        initial=True)
    mets_uri = forms.URLField(
        required=False,
        label=_("METS file URI"))

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        self.current_import = self.document.documentimport_set.order_by('started_on').last()
        self.mets_uri = None
        super().__init__(*args, **kwargs)

        if not settings.DISABLE_QUOTAS and not self.user.has_free_disk_storage():
            self.fields['upload_file'].help_text = _("A single ALTO or PAGE XML file.")

    def clean_iiif_uri(self):
        try:
            uri = self.cleaned_data.get('iiif_uri')
            if uri:
                content, total = clean_import_uri(uri, self.document, 'tmp.json')
                self.cleaned_data['total'] = total
                return content
        except FileImportError as e:
            raise forms.ValidationError(repr(e))

    def clean_mets_uri(self):
        try:
            uri = self.cleaned_data.get('mets_uri')
            self.mets_uri = os.path.dirname(uri)
            if uri:
                content, total = clean_import_uri(uri, self.document, 'tmp.xml',
                                                  is_mets=True,
                                                  mets_base_uri=self.mets_uri)
                self.cleaned_data['total'] = total
                return content
        except FileImportError as e:
            raise forms.ValidationError(repr(e))

    def clean_upload_file(self):
        upload_file = self.cleaned_data.get('upload_file')
        if upload_file:
            try:
                parser = clean_upload_file(upload_file, self.document, self.user)
                self.cleaned_data['total'] = parser.total
                return parser.file
            except FileImportError as e:
                raise forms.ValidationError(repr(e))

    def clean(self):
        cleaned_data = super().clean()
        # If quotas are enforced, assert that the user still has free CPU minutes and disk storage
        if not settings.DISABLE_QUOTAS:
            if not self.user.has_free_cpu_minutes():
                raise forms.ValidationError(_("You don't have any CPU minutes left."))
            if not self.user.has_free_disk_storage() and (
                cleaned_data.get('iiif_uri') or cleaned_data['resume_import']
            ):
                raise forms.ValidationError(_("You don't have any disk storage left."))

        if (
            not cleaned_data['resume_import']
            and not cleaned_data.get('upload_file')
            and not cleaned_data.get('iiif_uri')
            and not cleaned_data.get('mets_uri')
        ):
            raise forms.ValidationError(_("Choose one type of import."))

        return cleaned_data

    def save(self):
        if self.cleaned_data['resume_import'] and self.current_import.failed:
            self.instance = self.current_import
        else:
            imp = DocumentImport(
                document=self.document,
                name=self.cleaned_data['name'],
                override=self.cleaned_data['override'],
                total=self.cleaned_data['total'],  # added to the dict by clean_*()
                started_by=self.user)
            if self.cleaned_data.get('iiif_uri'):
                content = self.cleaned_data.get('iiif_uri')
                imp.import_file.save(
                    'iiif_manifest.json',
                    ContentFile(content))
            elif self.cleaned_data.get('mets_uri'):
                content = self.cleaned_data.get('mets_uri')
                imp.import_file.save(
                    'mets.xml',
                    ContentFile(content))
                imp.mets_base_uri = self.mets_uri
            elif self.cleaned_data.get('upload_file'):
                imp.import_file = self.cleaned_data.get('upload_file')
                if self.cleaned_data.get('mets'):
                    imp.with_mets = True

            imp.save()
            self.instance = imp

        return self.instance

    def process(self):
        document_import.delay(
            document_pk=self.document.pk,
            import_pk=self.instance.pk,
            user_pk=self.user.pk,
            report_label=_('Import in %(document_name)s') % {'document_name': self.document.name}
        )
        send_event('document', self.document.pk, "import:queued", {
            "id": self.document.pk
        })


class ExportForm(RegionTypesFormMixin, BootstrapFormMixin, forms.Form):
    FORMAT_CHOICES = (
        (export_format, export["label"])
        for export_format, export in ENABLED_EXPORTERS.items()
    )
    parts = forms.ModelMultipleChoiceField(queryset=None, required=False)
    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all())
    file_format = forms.ChoiceField(choices=FORMAT_CHOICES, initial=ALTO_FORMAT)
    include_images = forms.BooleanField(
        initial=False, required=False,
        label=_('Include images'),
        help_text=_("Will significantly increase the time to produce and download the export."))
    include_characters = forms.BooleanField(
        initial=False, required=False,
        label=_("Include character bounding boxes."),
        help_text=_("This data is only present for transcriptions coming from automatic recognition and is invalidated by manual edition."))

    include_metadata = forms.BooleanField(required=False, initial=False, label=_("Include metadata"), help_text=_("Includes document metadata and part metadata."))
    include_models = forms.BooleanField(required=False, initial=False, label=_("Include OCR models"), help_text=_("Includes the OCR models used to produce the transcriptions."))
    all_transcriptions = forms.BooleanField(required=False, initial=False, label=_("Include all transcriptions"), help_text=_("Includes all transcriptions of the document, not only the one selected."))
    include_graph = forms.BooleanField(required=False, initial=False, label=_("Include graph"), help_text=_("Includes the graph of the document with all its regions and lines."))
    include_annotations = forms.BooleanField(required=False, initial=False, label=_("Include annotations"), help_text=_("Includes image and text annotations."))
    include_comments = forms.BooleanField(required=False, initial=False, label=_("Include user comments"), help_text=_("Includes user comments on annotations."))
    anonymize = forms.BooleanField(required=False, initial=False, label=_("Anonymize users"), help_text=_("Replaces user identifiers in the export with opaque tokens."))
    archive_format = forms.ChoiceField(
        choices=(('zip', 'ZIP'), ('tar.gz', 'Gzipped tar')),
        initial='zip', required=False,
        label=_("Archive format"),
        help_text=_("Container format for the downloaded archive. Only applies to the JSON exporter."),
    )

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(archived=False,
                                                                             document=self.document)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def clean(self):
        # If quotas are enforced, assert that the user still has free CPU minutes
        if not settings.DISABLE_QUOTAS and not self.user.has_free_cpu_minutes():
            raise forms.ValidationError(_("You don't have any CPU minutes left."))

        return super().clean()

    def process(self):
        # allow no parts = all parts
        parts = self.cleaned_data['parts'] or self.document.parts.all()
        file_format = self.cleaned_data['file_format']
        transcription = self.cleaned_data['transcription']

        document_export.delay(file_format,
                              list(parts.values_list('pk', flat=True)),
                              transcription.pk,
                              self.cleaned_data['region_types'],
                              document_pk=self.document.pk,
                              include_images=self.cleaned_data['include_images'],
                              include_characters=self.cleaned_data['include_characters'],
                              include_metadata=self.cleaned_data['include_metadata'],
                              include_models=self.cleaned_data['include_models'],
                              include_graph=self.cleaned_data['include_graph'],
                              include_annotations=self.cleaned_data['include_annotations'],
                              include_comments=self.cleaned_data['include_comments'],
                              all_transcriptions=self.cleaned_data['all_transcriptions'],
                              anonymize=self.cleaned_data['anonymize'],
                              archive_format=self.cleaned_data.get('archive_format') or 'zip',
                              user_pk=self.user.pk,
                              report_label=self._report_label())

    def _report_label(self):
        # A JSON export with everything switched on + anonymize is the
        # Download-Archive quick action; label it distinctly so users can tell
        # a full backup apart from a regular export in the Tasks list.
        is_full_archive = (
            self.cleaned_data.get('file_format') == 'json'
            and self.cleaned_data.get('anonymize')
            and self.cleaned_data.get('all_transcriptions')
            and self.cleaned_data.get('include_annotations')
            and self.cleaned_data.get('include_comments')
            and self.cleaned_data.get('include_metadata')
            and self.cleaned_data.get('include_graph')
            and self.cleaned_data.get('include_characters')
        )
        template = (_('Download Archive %(document_name)s') if is_full_archive
                    else _('Export %(document_name)s'))
        return template % {'document_name': self.document.name}


class DocumentOntologyImportForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(
        required=True,
        help_text=_("A file containing a document ontology in JSON or YAML format"),
        widget=forms.FileInput(attrs={"accept": ".json,.yaml,.yml"}),
        validators=[FileExtensionValidator(allowed_extensions=["json", "yaml", "yml"])]
    )
