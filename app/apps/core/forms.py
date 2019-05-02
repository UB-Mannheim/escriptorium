import json
import logging

from django import forms
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

from bootstrap.forms import BootstrapFormMixin
from core.models import *
from core.serializers import AltoParser, ParseError

logger = logging.getLogger(__name__)


class DocumentForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
    
    class Meta:
        model = Document
        fields = ['name', 'read_direction', 'main_script']  # 'typology'


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
    key = forms.CharField()
    
    class Meta:
        model = DocumentMetadata
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        self.choices = kwargs.pop('choices', None)
        super().__init__(*args, **kwargs)
        if 'key' in self.initial:
            # feels like a hack but changes the display value to the name rather than the pk
            self.initial['key'] = next(md.name for md in self.choices
                                       if md.pk == self.initial['key'])
    
    def clean_key(self):
        key, created = Metadata.objects.get_or_create(name=self.cleaned_data['key'])
        return key


MetadataFormSet = inlineformset_factory(Document, DocumentMetadata, form=MetadataForm,
                                        extra=1, can_delete=True)


class DocumentProcessForm(BootstrapFormMixin, forms.ModelForm):
    TASK_BINARIZE = 'binarize'
    TASK_SEGMENT = 'segment'
    TASK_TRAIN = 'train'
    TASK_TRANSCRIBE  = 'transcribe'
    task = forms.ChoiceField(choices=(
        (TASK_BINARIZE, 1),
        (TASK_SEGMENT, 2),
        (TASK_TRAIN, 3),
        (TASK_TRANSCRIBE, 4),
    ))
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
                                       allowed_extensions=['mlmodel'])])
    
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
        if self.document.read_direction == self.document.READ_DIRECTION_RTL:
            self.initial['text_direction'] = 'horizontal-rl'
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
        if task == self.TASK_BINARIZE:
            if len(self.parts) == 1 and self.cleaned_data.get('bw_image'):
                self.parts[0].bw_image = self.cleaned_data['bw_image']
                self.parts[0].save()
            else:
                for part in self.parts:
                    part.task('binarize', user_pk=self.user.pk)
        elif task == self.TASK_SEGMENT:
            for part in self.parts:
                part.task('segment',
                          user_pk=self.user.pk,
                          steps=self.cleaned_data['segmentation_steps'],
                          text_direction=self.cleaned_data['text_direction'])
        elif task == self.TASK_TRAIN:
            if self.cleaned_data.get('new_model'):
                # create model and corresponding OcrModel
                pass
            
            # part.train(user_pk=self.user.pk, model=None)
        elif task == self.TASK_TRANSCRIBE:
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
                part.task('transcribe', user_pk=self.user.pk, model=model)
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
