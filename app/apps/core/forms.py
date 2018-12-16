import json

from django import forms
from django.forms.models import inlineformset_factory
from django.utils.translation import gettext as _

from bootstrap.forms import BootstrapFormMixin
from core.models import Document, DocumentPart, DocumentMetadata, Typology, Line


class DocumentForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        
    class Meta:
        model = Document
        fields = ['name', 'typology']


class DocumentShareForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['shared_with_groups'].widget = forms.CheckboxSelectMultiple()
        self.fields['shared_with_groups'].queryset = self.request.user.groups
    
    class Meta:
        model = Document
        fields = ['shared_with_groups']  # shared_with_users


class MetadataForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DocumentMetadata
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attrs = self.fields['key'].widget.attrs
        # attrs.update({'autocomplete':"off", 'list': "metadataKeys"})
        attrs['class'] += ' input-group-text px-5'
        self.fields['key'].empty_label = '-'
        self.fields['key'].widget.need_label = False


MetadataFormSet = inlineformset_factory(Document, DocumentMetadata, form=MetadataForm,
                                        extra=1, can_delete=True)

class DocumentPartUpdateForm(forms.ModelForm):
    index = forms.IntegerField(required=False, min_value=0)
    lines = forms.CharField(required=False)
    
    class Meta:
        model = DocumentPart
        fields = ('name', 'index')
        
    def save(self, *args, **kwargs):
        if 'index' in self.cleaned_data and self.cleaned_data['index'] is not None:
            self.instance.to(self.cleaned_data['index'])
        if 'lines' in self.cleaned_data and self.cleaned_data['lines']:
            lines = json.loads(self.cleaned_data['lines'])
            for line_ in lines:
                if line_['pk'] is None:
                    Line.objects.create(document_part=self.instance,
                                        box = line_['box'])
                else:
                    line = Line.objects.get(pk=line_['pk'])
                    if 'delete' in line_ and line_['delete'] is True:
                        line.delete()
                    else:
                        line.box = line_['box']
                        line.save()
        
        return super().save(*args, **kwargs)


class UploadImageForm(BootstrapFormMixin, forms.ModelForm):
    auto_process = forms.BooleanField(initial=True, required=False,
                                      label=_("Automatically process"))
    text_direction = forms.ChoiceField(required=False, initial='horizontal-lr',
                                       label=_("Text direction"),
                                       choices=(('horizontal-lr', _("Horizontal")),
                                                ('vertical-lr', _("Vertical"))))
    binarizer = forms.ChoiceField(required=False, label=_("Binarizer"),
                                  choices=(('kraken', _("Kraken")),))
    
    class Meta:
        model = DocumentPart
        fields = ('image', 'auto_process', 'text_direction', 'typology', 'binarizer')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['typology'].initial = Typology.objects.get(name="Page")
        self.fields['binarizer'].widget.attrs['disabled'] = True
