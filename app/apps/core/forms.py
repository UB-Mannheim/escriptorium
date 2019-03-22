import json

from django import forms
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.utils.functional import cached_property
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
    username = forms.CharField(required=False)
    
    class Meta:
        model = Document
        fields = ['shared_with_groups', 'shared_with_users', 'username']
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['shared_with_users'].widget = forms.CheckboxSelectMultiple()
        self.fields['shared_with_users'].queryset = (User.objects.filter(
            Q(groups__in=self.request.user.groups.all())
            | Q(pk__in=self.instance.shared_with_users.values_list('pk', flat=True))
        ).exclude(pk=self.request.user.pk))
        self.fields['shared_with_groups'].widget = forms.CheckboxSelectMultiple()
        self.fields['shared_with_groups'].queryset = self.request.user.groups
    
    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            user = None
        return user
    
    def save(self, commit=True):
        doc = super().save(commit=commit)
        if self.cleaned_data['username']:
            doc.shared_with_users.add(self.cleaned_data['username'])
        return doc
        

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


class DocumentProcessForm(BootstrapFormMixin, forms.ModelForm):
    task = forms.ChoiceField(choices=(
        ('binarize', 1),
        ('segment', 2),
        ('train', 3),
        ('transcribe', 4)))
    parts = forms.CharField()
    bw_image = forms.ImageField(required=False)
    segmentation_steps = forms.ChoiceField(choices=(
        ('regions', _('Regions')),
        ('lines', _('Lines')),
        ('both', _('Lines and regions'))
    ), initial='lines', required=False)
    new_model = forms.CharField(required=False, label=_('Name'))
    upload_model = forms.FileField(required=False,
                                   validators=[FileExtensionValidator(
                                       allowed_extensions=['pronn'])])
    
    class Meta:
        model = DocumentProcessSettings
        fields = '__all__'
    
    def __init__(self, document, user, *args, **kwargs):
        self.user = user
        self.document = document
        super().__init__(*args, **kwargs)
        # self.fields['typology'].widget = forms.HiddenInput()  # for now
        # self.fields['typology'].initial = Typology.objects.get(name="Page")
        # self.fields['typology'].widget.attrs['title'] = _("Default Typology")
        self.fields['binarizer'].widget.attrs['disabled'] = True
        self.fields['binarizer'].required = False
        self.fields['text_direction'].required = False
        self.fields['train_model'].queryset = OcrModel.objects.filter(document=self.document)
        self.fields['ocr_model'].queryset = OcrModel.objects.filter(
            Q(document=None) | Q(document=self.document), trained=True)
    
    @cached_property
    def parts(self):
        pks = self.data.getlist('parts')
        pks = json.loads(self.data.get('parts'))
        parts = DocumentPart.objects.filter(document=self.document, pk__in=pks)
        parts = DocumentPart.objects.filter(
            document=self.document, pk__in=pks)
        return parts
    
    def clean_bw_image(self):
        img = self.cleaned_data.get('bw_image')
        if not img:
            return
        if len(self.parts) != 1:
            raise forms.ValidationError(_("Uploaded image with more than one selected image."))
        # Beware: don't close the file here !
        fh = Image.open(img)
        if fh.mode not in ['1', 'L']:
            raise forms.ValidationError(_("Uploaded image should be black and white."))
        isize = (self.parts[0].image.width, self.parts[0].image.height) 
        if fh.size != isize:
            raise forms.ValidationError(_("Uploaded image should be the same size as original image {}.").format(isize))
        return img
    
    def process(self):
        task = self.cleaned_data.get('task')
        if task == 'binarize':
            if len(self.parts) == 1 and self.cleaned_data.get('bw_image'):
                self.parts[0].bw_image = self.cleaned_data['bw_image']
                self.parts[0].save()
            else:
                for part in self.parts:
                    part.task_binarize(user_pk=self.user.pk)
        elif task == 'segment':
            for part in self.parts:
                part.task_segment(user_pk=self.user.pk,
                             steps=self.cleaned_data['segmentation_steps'],
                             text_direction=self.cleaned_data['text_direction'])
        elif task == 'train':
            if self.cleaned_data.get('new_model'):
                # create model and corresponding OcrModel
                pass

            # part.train(user_pk=self.user.pk, model=None)
        elif task == 'transcribe':
            if self.cleaned_data.get('upload_model'):
                model = OcrModel.objects.create(
                    name=self.cleaned_data['upload_model'].name,
                    file=self.cleaned_data['upload_model'],
                    trained=True, document=self.parts[0].document)
                self.instance.ocr_model = model  # save to settings
            elif self.cleaned_data['ocr_model']:
                model = self.cleaned_data['ocr_model']
            else:
                model = None
            
            for part in self.parts:
                part.task_transcribe(user_pk=self.user.pk, model=model)
        
        self.save()  # save settings


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
