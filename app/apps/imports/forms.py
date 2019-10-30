from datetime import datetime
import json
import os, io
import requests
from lxml import etree
from zipfile import ZipFile

from django import forms
from django.core.validators import FileExtensionValidator
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Prefetch
from django.http import StreamingHttpResponse, HttpResponse
from django.template import loader
from django.utils.translation import gettext as _
from django.utils.functional import cached_property
from django.utils.text import slugify

from bootstrap.forms import BootstrapFormMixin
from core.models import Transcription, LineTranscription, DocumentPart
from imports.models import DocumentImport
from imports.parsers import make_parser, ParseError
from imports.tasks import document_import


class ImportForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField(
        required=False,
        max_length=256,
        help_text=_("The name of the target transcription. Will default to '{format} Import'."))
    upload_file = forms.FileField(
        required=False,
        help_text=_("A single Alto XML file, or a zip file."))
    override = forms.BooleanField(
        initial=True, required=False,
        label=_("Override existing segmentation."),
        help_text=_("Destroys existing regions and lines before importing."))
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
        self.current_import = (self.document.documentimport_set
                               .filter(workflow_state__in=[
                                   DocumentImport.WORKFLOW_STATE_ERROR,
                                   DocumentImport.WORKFLOW_STATE_STARTED,
                                   DocumentImport.WORKFLOW_STATE_CREATED])
                               .order_by('started_on').last())
        super().__init__(*args, **kwargs)
    
    def clean_iiif_uri(self):
        uri = self.cleaned_data.get('iiif_uri')
        
        if uri:
            try:
                content = requests.get(uri).content
                buf = io.BytesIO(content)
                buf.name = 'tmp.json'
                parser = make_parser(self.document, buf)
                parser.validate()
                self.cleaned_data['total'] = parser.total
                return content
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
            and not cleaned_data['iiif_uri']):
            raise forms.ValidationError(_("Choose one type of import."))
        
        return cleaned_data
    
    def save(self):
        if self.cleaned_data['resume_import'] and self.current_import.failed:
            self.instance = self.current_import
        else:
            imp = DocumentImport(
                document = self.document,
                name=self.cleaned_data['name'],
                override=self.cleaned_data['override'],
                total=self.cleaned_data['total'],  # added to the dict by clean_*()
                started_by = self.user)
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


class ExportForm(BootstrapFormMixin, forms.Form):
    FORMAT_CHOICES = (
        ('alto', 'Alto'),
        ('text', 'Text'),
        ('pagexml', 'Pagexml')
    )
    parts = forms.CharField()
    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all())
    file_format = forms.ChoiceField(choices=FORMAT_CHOICES)
    
    def __init__(self, document, *args, **kwargs):
        self.document = document
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)
    
    def clean_parts(self):
        pks = json.loads(self.data.get('parts'))
        if len(pks) < 1:
            raise forms.ValidationError(_("Select at least one image to export."))
        parts = DocumentPart.objects.filter(
            document=self.document, pk__in=pks)
        return parts

    def stream(self):
        file_format = self.cleaned_data['file_format']
        parts = self.cleaned_data['parts']
        transcription = self.cleaned_data['transcription']
        
        if file_format == 'text':
            content_type = 'text/plain'
            lines = (LineTranscription.objects
                     .filter(transcription=transcription, line__document_part__in=parts)
                     .exclude(content="")
                     .order_by('line__document_part', 'line__document_part__order', 'line__order'))
            return StreamingHttpResponse(['%s\n' % line.content for line in lines],
                                         content_type=content_type)
        
        elif file_format == 'alto':
            content_type = 'text/xml'
            extension = 'xml'
            tplt = loader.get_template('export/alto.xml')
            filename="export_%s_%s_%s.zip" % (slugify(self.document.name).replace('-', '_'),
                                            file_format,
                                           datetime.now().strftime('%Y%m%d%H%M'))
            buff = io.BytesIO()
            with ZipFile(buff, 'w') as zip_:
                for part in parts:
                    page = tplt.render({
                        'part': part,
                        'lines': part.lines
                        .order_by('block__order', 'order')
                        .prefetch_related(
                            Prefetch('transcriptions',
                                     to_attr='transcription',
                                     queryset=LineTranscription.objects.filter(
                                         transcription=transcription)))})
                    zip_.writestr('%s.xml' % part.filename, page)
            # TODO: add METS file
            response = HttpResponse(buff.getvalue(),content_type='application/x-zip-compressed')
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            return response

        elif file_format == 'pagexml':
            tplt = loader.get_template('export/pagexml.xml')
            filename = "export_%s_%s_%s.zip" % (slugify(self.document.name).replace('-', '_'),
                                                file_format,
                                                datetime.now().strftime('%Y%m%d%H%M'))
            buff = io.BytesIO()
            with ZipFile(buff, 'w') as zip_:
                for part in parts:
                    page = tplt.render({
                        'part': part,
                        'lines': part.lines
                            .order_by('block__order', 'order')
                            .prefetch_related(
                            Prefetch('transcriptions',
                                     to_attr='transcription',
                                     queryset=LineTranscription.objects.filter(
                                         transcription=transcription)))})
                    zip_.writestr('%s.xml' % part.filename, page)
            response = HttpResponse(buff.getvalue(), content_type='application/x-zip-compressed')
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            return response
        else:
            response = HttpResponse('we cannot export to this format')
            return response

