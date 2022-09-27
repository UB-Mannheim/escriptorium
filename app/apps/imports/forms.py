import io
import json

import requests
from bootstrap.forms import BootstrapFormMixin
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _

from core.forms import RegionTypesFormMixin
from core.models import DocumentPart, Transcription
from imports.export import ALTO_FORMAT, ENABLED_EXPORTERS
from imports.models import DocumentImport
from imports.parsers import ParseError, make_parser
from imports.tasks import document_export, document_import
from users.consumers import send_event


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

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        self.current_import = self.document.documentimport_set.order_by('started_on').last()
        super().__init__(*args, **kwargs)

        if not settings.DISABLE_QUOTAS and not self.user.has_free_disk_storage():
            self.fields['upload_file'].help_text = _("A single ALTO or PAGE XML file.")

    def clean_iiif_uri(self):
        uri = self.cleaned_data.get('iiif_uri')
        if uri:
            try:
                resp = requests.get(uri)
                content = resp.content
                buf = io.BytesIO(content)
                buf.name = 'tmp.json'
                parser = make_parser(self.document, buf)
                parser.validate()
                self.cleaned_data['total'] = parser.total
                return content
            except requests.exceptions.RequestException:
                raise forms.ValidationError(_("The document is unreachable, unreadable or the host timed out."))
            except json.decoder.JSONDecodeError:
                raise forms.ValidationError(_("The document pointed to by the given uri doesn't seem to be valid json."))
            except ParseError as e:
                msg = _("Couldn't parse the given file or its validation failed")
                if len(e.args):
                    msg += ": %s" % e.args[0]
                raise forms.ValidationError(msg)

    def clean_upload_file(self):
        upload_file = self.cleaned_data.get('upload_file')
        if upload_file:
            try:
                # If quotas are enforced, define if the user can upload ZIP and PDF files
                allowed = settings.DISABLE_QUOTAS or self.user.has_free_disk_storage()
                parser = make_parser(self.document, upload_file, zip_allowed=allowed, pdf_allowed=allowed)
                parser.validate()
                self.cleaned_data['total'] = parser.total
            except ParseError as e:
                msg = _("Couldn't parse the given file or its validation failed")
                if len(e.args):
                    msg += ": %s" % e.args[0]
                raise forms.ValidationError(msg)
            except ValueError as e:
                raise forms.ValidationError(e)
            return upload_file

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

        if (not cleaned_data['resume_import']
            and not cleaned_data.get('upload_file')
                and not cleaned_data.get('iiif_uri')):
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
            elif self.cleaned_data.get('upload_file'):
                imp.import_file = self.cleaned_data.get('upload_file')

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
