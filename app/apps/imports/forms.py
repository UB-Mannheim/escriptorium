import io
import json
import os
from urllib.parse import urlparse

import requests
from bootstrap.forms import BootstrapFormMixin
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext as _

from core.forms import RegionTypesFormMixin
from core.models import DocumentPart, Transcription
from imports.export import ALTO_FORMAT, ENABLED_EXPORTERS
from imports.models import DocumentImport
from imports.parsers import ParseError, make_parser
from imports.tasks import document_export, document_import
from users.consumers import send_event


class FileImportError(Exception):
    pass


def clean_uri(uri, document, tempfile, is_mets=False, mets_base_uri=None):
    try:
        resp = requests.get(uri)
        content = resp.content
        buf = io.BytesIO(content)
        buf.name = tempfile
        parser = make_parser(document, buf,
                             mets_describer=is_mets,
                             mets_base_uri=mets_base_uri)
        parser.validate()
        return content, parser.total
    except requests.exceptions.RequestException:
        raise FileImportError(_("The document is unreachable, unreadable or the host timed out."))
    except json.decoder.JSONDecodeError:
        raise FileImportError(_("The document pointed to by the given uri doesn't seem to be valid json."))
    except ParseError as e:
        msg = _("Couldn't parse the given file or its validation failed")
        if len(e.args):
            msg += ": %s" % e.args[0]
        raise FileImportError(msg)


def clean_import_uri(uri, document, tmp_file_name, is_mets=False, mets_base_uri=None):
    domain = urlparse(uri).netloc
    if ('*' not in settings.IMPORT_ALLOWED_DOMAINS and domain not in settings.IMPORT_ALLOWED_DOMAINS):
        raise FileImportError(_("You're not allowed to import files from this domain, please contact your instance administrator."))

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
            uri = self.cleaned_data.get('uri')
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
    parts = forms.ModelMultipleChoiceField(queryset=None)
    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all())
    file_format = forms.ChoiceField(choices=FORMAT_CHOICES, initial=ALTO_FORMAT)
    include_images = forms.BooleanField(
        initial=False, required=False,
        label=_('Include images'),
        help_text=_("Will significantly increase the time to produce and download the export."))

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(archived=False,
                                                                             document=self.document)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def clean_parts(self):
        parts = self.cleaned_data['parts']
        if len(parts) < 1:
            raise forms.ValidationError(_("Select at least one image to export."))
        return parts

    def clean(self):
        # If quotas are enforced, assert that the user still has free CPU minutes
        if not settings.DISABLE_QUOTAS and not self.user.has_free_cpu_minutes():
            raise forms.ValidationError(_("You don't have any CPU minutes left."))

        return super().clean()

    def process(self):
        parts = self.cleaned_data['parts']
        file_format = self.cleaned_data['file_format']
        transcription = self.cleaned_data['transcription']

        document_export.delay(file_format,
                              list(parts.values_list('pk', flat=True)),
                              transcription.pk,
                              self.cleaned_data['region_types'],
                              document_pk=self.document.pk,
                              include_images=self.cleaned_data['include_images'],
                              user_pk=self.user.pk,
                              report_label=_('Export %(document_name)s') % {'document_name': self.document.name})


class DocumentOntologyImportForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(
        required=True,
        help_text=_("A file containing a document ontology in JSON format"),
        widget=forms.FileInput(attrs={"accept": "application/json"}),
        validators=[FileExtensionValidator(allowed_extensions=["json"])]
    )
