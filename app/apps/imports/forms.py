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
from imports.models import Import
from imports.parsers import make_parser, ParseError
from imports.tasks import document_import


class ImportForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField(
        required=False,
        max_length=256,
        help_text=_("The name of the target transcription. Will default to '{format} Import'."))
    parts = forms.CharField(required=False)
    xml_file = forms.FileField(
        required=False,
        help_text=_("Alto or Abbyy XML."))
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
        self.current_import = self.document.import_set.order_by('started_on').last()
        super().__init__(*args, **kwargs)
    
    def clean_iiif_uri(self):
        uri = self.cleaned_data.get('iiif_uri')
        try:
            if uri:
                return requests.get(uri).json()
        except json.decoder.JSONDecodeError:
            raise forms.ValidationError(_("The document pointed to by the given uri doesn't seem to be valid json."))
    
    def clean_parts(self):
        try:
            data = json.loads(self.cleaned_data.get('parts'))
        except json.decoder.JSONDecodeError:
            data = []
        return data
    
    def clean(self):
        cleaned_data = super().clean()
        xml_file = self.cleaned_data.get('xml_file')
        if (not cleaned_data['resume_import']
            and not xml_file
            and not cleaned_data['iiif_uri']):
            raise forms.ValidationError(_("Choose one type of import."))
        
        if xml_file:
            try:
                parser = make_parser(xml_file,
                                     name=cleaned_data.get('name'),
                                     override=cleaned_data.get('override'))
                parser.validate()
            except ParseError as e:
                msg = _("Couldn't parse the given xml file or its validation failed.")
                if len(e.args):
                    msg += " %s" % e.args[0]
                raise forms.ValidationError(msg)
            if parser and parser.total != len(cleaned_data['parts']):
                raise forms.ValidationError(
                    _("The number of pages in the import {num_pages} file doesn't match the number of selected images {num_images}.").format(
                      num_pages=len(parser.pages), num_images=len(cleaned_data['parts'])))
        
        return cleaned_data
    
    def save(self):
        if self.cleaned_data['resume_import'] and self.current_import.failed:
            self.instance = self.current_import
        else:
            imp = Import(
                document = self.document,
                name=self.cleaned_data['name'],
                override=self.cleaned_data['override'],
                started_by = self.user,
                parts=self.cleaned_data.get('parts'))
            if self.cleaned_data.get('iiif_uri'):
                content = json.dumps(self.cleaned_data.get('iiif_uri'))
                imp.import_file.save(
                    'iiif_manifest.json',
                    ContentFile(content.encode()))
            elif self.cleaned_data.get('xml_file'):
                imp.import_file = self.cleaned_data.get('xml_file')
            
            imp.save()
            self.instance = imp
        return self.instance
    
    def process(self):
        document_import.delay(self.instance.pk)


class ExportForm(BootstrapFormMixin, forms.Form):
    FORMAT_CHOICES = (
        ('alto', 'Alto'),
        ('text', 'Text')
    )
    parts = forms.CharField()
    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all())
    file_format = forms.ChoiceField(choices=FORMAT_CHOICES)
    
    def __init__(self, document, *args, **kwargs):
        self.document = document
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)
    
    def clean_parts(self):
        pks = self.data.getlist('parts')
        pks = json.loads(self.data.get('parts'))
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
            filename="export_%s_%s.zip" % (slugify(self.document.name), datetime.now().strftime('%y%m%d%H%M'))
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
            response = HttpResponse(buff.getvalue())
            response['Content-Type'] = 'application/x-zip-compressed'
            response['Content-Disposition'] = 'attachment; "filename=%s"' % filename
            return response

