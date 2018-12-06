from django import forms
from django.forms.models import inlineformset_factory

from bootstrap.forms import BootstrapFormMixin
from core.models import Document, DocumentPart, DocumentMetadata


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
        attrs['class'] += ' input-group-text'
        self.fields['key'].empty_label = '-'
        self.fields['key'].widget.need_label = False
        

MetadataFormSet = inlineformset_factory(Document, DocumentMetadata, form=MetadataForm,
                                        extra=1, can_delete=True)
