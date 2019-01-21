import json

from django import forms
from django.forms.models import inlineformset_factory
from django.utils.translation import gettext as _

from bootstrap.forms import BootstrapFormMixin
from core.models import *


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
        fields = ('name', 'typology', 'index')
        
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


class DocumentProcessForm(BootstrapFormMixin, forms.ModelForm):
    task = forms.ChoiceField(choices=(
        ('binarize', 'test'),
        ('segment', 'test'),
        ('train', 'test'),
        ('transcribe', 'test')))
    parts = forms.CharField()
    bw_image = forms.ImageField(required=False)
    
    class Meta:
        model = DocumentProcessSettings
        fields = '__all__'
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['document'].widget = forms.HiddenInput()
        self.fields['typology'].widget = forms.HiddenInput()  # for now
        self.fields['typology'].initial = Typology.objects.get(name="Page")
        self.fields['typology'].widget.attrs['title'] = _("Default Typology")
        self.fields['binarizer'].widget.attrs['disabled'] = True
        self.fields['binarizer'].required = False
        self.fields['text_direction'].required = False
    
    def clean_bw_img(self):
        img = self.cleaned_data.get('bw_image')
        with Image.open(img) as fh:
            if fh.mode not in ['1', 'L']:
                raise forms.ValidationError(_("Uploaded image should be black and white."))
        return img
    
    def process(self):
        self.save()  # save settings
        task = self.cleaned_data.get('task')
        document = self.cleaned_data.get('document')
        pks = json.loads(self.cleaned_data.get('parts'))
        parts = DocumentPart.objects.filter(document=document, pk__in=pks)
        if task == 'binarize':
            if len(parts) == 1 and self.cleaned_data.get('bw_image'):
                parts[0].bw_image = self.cleaned_data['bw_image']
                parts[0].save()
            else:
                for part in parts:
                    part.binarize(user_pk=self.user.pk)
        elif task == 'segment':
            for part in parts:
                part.segment(user_pk=self.user.pk,
                             text_direction=self.cleaned_data['text_direction'])
        elif task == 'transcribe':
            for part in parts:
                part.transcribe(user_pk=self.user.pk)


class UploadImageForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DocumentPart
        fields = ('image',)
    
    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('document')
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        part = super().save(commit=False)
        part.document = self.document
        if commit:
            part.save()
        return part
