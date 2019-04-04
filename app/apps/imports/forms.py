import json

from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext as _
from django.utils.functional import cached_property

from bootstrap.forms import BootstrapFormMixin
from imports.models import Import
from imports.parsers import AltoParser, ParseError
from imports.tasks import xml_import


class ImportForm(BootstrapFormMixin, forms.Form):
    parts = forms.CharField()
    xml_file = forms.FileField(
        required=False,
        help_text=_("Alto xml."))
    
    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_xml_file(self):
        tmpfile = self.cleaned_data.get('xml_file')
        # check its alto
        return tmpfile
    
    def clean_parts(self):
        data = json.loads(self.cleaned_data.get('parts'))
        return data
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data['xml_file']:
            raise forms.ValidationError(_("Choose one type of import."))
        try:
            parser = AltoParser(cleaned_data['xml_file'])
        except ParseError:
            raise forms.ValidationError(_("Couldn't parse the given xml file."))
        if parser and len(parser.pages) != len(cleaned_data['parts']):
            raise forms.ValidationError(
                _("The number of pages in the import file doesn't match the number of selected images, respectively %d and %d." %
                  (len(parser.pages), len(cleaned_data['parts']))))
        return cleaned_data
    
    def save(self):
        self.instance = Import.objects.create(
            document = self.document,
            started_by = self.user,
            parts=self.cleaned_data['parts'],
            import_file=self.cleaned_data['xml_file'])
        return self.instance
    
    def process(self):
        xml_import.delay(self.instance.pk)
