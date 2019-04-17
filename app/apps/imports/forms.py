import json
import requests

from django import forms
from django.core.validators import FileExtensionValidator
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import gettext as _
from django.utils.functional import cached_property

from bootstrap.forms import BootstrapFormMixin
from imports.models import Import
from imports.parsers import make_parser, ParseError
from imports.tasks import document_import


class ImportForm(BootstrapFormMixin, forms.Form):
    parts = forms.CharField(required=False)
    xml_file = forms.FileField(
        required=False,
        help_text=_("Alto or Abbyy XML."))
    iiif_uri = forms.URLField(
        required=False,
        label=_("iiif manifesto"),
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
    
    # def clean_xml_file(self):
    #     tmpfile = self.cleaned_data.get('xml_file')
    #     # check its alto or abbyy
    #     return tmpfile
    
    def clean_iiif_uri(self):
        uri = self.cleaned_data.get('iiif_uri')
        try:
            if uri:
                return requests.get(uri).json()
        except json.decoder.JSONDecodeError:
            raise ValidationError(_("The document pointed to by the given uri doesn't seem to be valid json."))
    
    def clean_parts(self):
        try:
            data = json.loads(self.cleaned_data.get('parts'))
        except json.decoder.JSONDecodeError:
            data = []
        return data
    
    def clean(self):
        cleaned_data = super().clean()
        if (not cleaned_data["resume_import"]
            and not cleaned_data['xml_file']
            and not cleaned_data['iiif_uri']):
            raise forms.ValidationError(_("Choose one type of import."))
        
        if cleaned_data['xml_file']:
            try:
                parser = make_parser(cleaned_data['xml_file'])
            except ParseError:
                raise forms.ValidationError(_("Couldn't parse the given xml file."))
            if parser and parser.total != len(cleaned_data['parts']):
                raise forms.ValidationError(
                    _("The number of pages in the import file doesn't match the number of selected images, respectively %d and %d." %
                      (len(parser.pages), len(cleaned_data['parts']))))
        
        return cleaned_data
    
    def save(self):
        if self.cleaned_data['resume_import'] and self.current_import.failed:
            self.instance = self.current_import
        else:
            imp = Import(
                document = self.document,
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
