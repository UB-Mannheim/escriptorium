import json

from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext as _
from django.utils.functional import cached_property

from bootstrap.forms import BootstrapFormMixin
from imports.models import Import
from imports.parsers import make_parser, ParseError
from imports.tasks import xml_import


class ImportForm(BootstrapFormMixin, forms.Form):
    parts = forms.CharField(required=False)
    xml_file = forms.FileField(
        required=False,
        help_text=_("Alto or Abbyy XML."))
    resume_import = forms.BooleanField(
        required=False,
        label=_("Resume previous import"),
        initial=True)
    
    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        self.current_import = self.document.import_set.order_by('started_on').last()
        super().__init__(*args, **kwargs)
    
    def clean_xml_file(self):
        tmpfile = self.cleaned_data.get('xml_file')
        # check its alto or abbyy
        return tmpfile
    
    def clean_parts(self):
        try:
            data = json.loads(self.cleaned_data.get('parts'))
        except json.decoder.JSONDecodeError:
            data = []
        return data
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data["resume_import"] and not cleaned_data['xml_file']:
            raise forms.ValidationError(_("Choose one type of import."))
        if cleaned_data['xml_file']:
            try:
                parser = make_parser(cleaned_data['xml_file'])
            except ParseError:
                raise forms.ValidationError(_("Couldn't parse the given xml file."))
            if parser and len(parser.pages) != len(cleaned_data['parts']):
                raise forms.ValidationError(
                    _("The number of pages in the import file doesn't match the number of selected images, respectively %d and %d." %
                      (len(parser.pages), len(cleaned_data['parts']))))
        return cleaned_data
    
    def save(self):
        if self.cleaned_data['resume_import'] and self.current_import.failed:
            self.instance = self.current_import
        else:
            self.instance = Import.objects.create(
                document = self.document,
                started_by = self.user,
                parts=self.cleaned_data['parts'],
                import_file=self.cleaned_data['xml_file'])
        
        return self.instance
    
    def process(self):
        xml_import.delay(self.instance.pk)
