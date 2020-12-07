import json
import io
import requests

from django import forms
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _

from bootstrap.forms import BootstrapFormMixin
from core.models import Transcription
from imports.models import DocumentImport
from imports.parsers import make_parser, ParseError
from imports.tasks import document_import, document_export
from reporting.models import TaskReport
from users.consumers import send_event


class ImportForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField(
        required=False,
        max_length=256,
        help_text=_("The name of the target transcription. Will default to '{format} Import'."))
    upload_file = forms.FileField(
        required=False,
        help_text=_("A single AltoXML, PageXML file, or a zip file."))
    override = forms.BooleanField(
        initial=True, required=False,
        label=_("Override existing segmentation."),
        help_text=_("Destroys existing regions, lines and any bound transcription before importing."))
    iiif_uri = forms.URLField(
        required=False,
        label=_("IIIF manifesto uri"),
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
                parser = make_parser(self.document, upload_file)
                parser.validate()
                self.cleaned_data['total'] = parser.total
            except ParseError as e:
                msg = _("Couldn't parse the given file or its validation failed")
                if len(e.args):
                    msg += ": %s" % e.args[0]
                raise forms.ValidationError(msg)
            return upload_file

    def clean(self):
        cleaned_data = super().clean()
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
        document_import.delay(self.instance.pk)
        send_event('document', self.document.pk, "import:queued", {
            "id": self.document.pk
        })


class ExportForm(BootstrapFormMixin, forms.Form):
    ALTO_FORMAT = "alto"
    PAGEXML_FORMAT = "pagexml"
    TEXT_FORMAT = "text"

    FORMAT_CHOICES = (
        (ALTO_FORMAT, 'Alto'),
        (TEXT_FORMAT, 'Text'),
        (PAGEXML_FORMAT, 'Pagexml')
    )
    parts = forms.CharField()
    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all())
    file_format = forms.ChoiceField(choices=FORMAT_CHOICES)
    include_images = forms.BooleanField(
        initial=False, required=False,
        label=_('Include images'),
        help_text=_("Will significantly increase the time to produce and download the export."))

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)

    def clean_parts(self):
        pks = json.loads(self.data.get('parts'))
        if len(pks) < 1:
            raise forms.ValidationError(_("Select at least one image to export."))
        return pks

    def process(self):
        parts = self.cleaned_data['parts']
        file_format = self.cleaned_data['file_format']
        transcription = self.cleaned_data['transcription']

        report = TaskReport.objects.create(
            user=self.user,
            label=_('Export %(document_name)s') % {
                'document_name': self.document.name})
        document_export.delay(file_format, self.user.pk, self.document.pk,
                              parts, transcription.pk, report.pk,
                              include_images=self.cleaned_data['include_images'])
