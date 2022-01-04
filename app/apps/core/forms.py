import logging
from PIL import Image

from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from bootstrap.forms import BootstrapFormMixin
from core.models import (Project, Document, Metadata, DocumentMetadata,
                         DocumentPart, OcrModel, OcrModelDocument, Transcription,
                         BlockType, LineType, AlreadyProcessingException, OcrModelRight)
from users.models import User
from kraken.lib import vgsl
from kraken.lib.exceptions import KrakenInvalidModelException

logger = logging.getLogger(__name__)


class ProjectForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name']


class DocumentForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        if self.request.method == "POST":
            # we need to accept all types when posting for added ones
            block_qs = BlockType.objects.all()
            line_qs = LineType.objects.all()
        elif self.instance.pk:
            block_qs = BlockType.objects.filter(
                Q(public=True) | Q(valid_in=self.instance)).distinct()
            line_qs = LineType.objects.filter(
                Q(public=True) | Q(valid_in=self.instance)).distinct()
        else:
            block_qs = BlockType.objects.filter(public=True)
            line_qs = LineType.objects.filter(public=True)
            self.initial['valid_block_types'] = BlockType.objects.filter(default=True)
            self.initial['valid_line_types'] = LineType.objects.filter(default=True)

        self.fields['project'].queryset = Project.objects.for_user_read(self.request.user)
        self.fields['project'].empty_label = None
        if self.instance.pk and self.instance.owner != self.request.user:
            self.fields['project'].disabled = True

        self.fields['valid_block_types'].queryset = block_qs.order_by('name')
        self.fields['valid_line_types'].queryset = line_qs.order_by('name')

    class Meta:
        model = Document
        fields = ['project', 'name', 'read_direction', 'line_offset', 'main_script',
                  'valid_block_types', 'valid_line_types']
        widgets = {
            'valid_block_types': forms.CheckboxSelectMultiple,
            'valid_line_types': forms.CheckboxSelectMultiple
        }


class ShareForm(BootstrapFormMixin, forms.ModelForm):
    # abstract form
    username = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['shared_with_users'].widget = forms.CheckboxSelectMultiple()
        self.fields['shared_with_users'].queryset = (User.objects.filter(
            Q(groups__in=self.request.user.groups.all())
            | Q(pk__in=self.instance.shared_with_users.values_list('pk', flat=True))
        ).exclude(pk=self.request.user.pk)).distinct()
        self.fields['shared_with_groups'].widget = forms.CheckboxSelectMultiple()
        self.fields['shared_with_groups'].queryset = self.request.user.groups

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            user = None
        return user


class ProjectShareForm(ShareForm):
    class Meta:
        model = Project
        fields = ['shared_with_groups', 'shared_with_users', 'username']

    def save(self, commit=True):
        proj = super().save(commit=commit)
        if self.cleaned_data['username']:
            proj.shared_with_users.add(self.cleaned_data['username'])
        return proj


class DocumentShareForm(ShareForm):
    class Meta:
        model = Document
        fields = ['shared_with_groups', 'shared_with_users', 'username']

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


MetadataFormSet = inlineformset_factory(Document, DocumentMetadata,
                                        form=MetadataForm,
                                        extra=1, can_delete=True)


class ModelUploadForm(BootstrapFormMixin, forms.ModelForm):
    name = forms.CharField()
    file = forms.FileField(
        validators=[FileExtensionValidator(
            allowed_extensions=['mlmodel'])])

    class Meta:
        model = OcrModel
        fields = ('name', 'file')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_file(self):
        # Early validation of the model loading
        file_field = self.cleaned_data['file']
        try:
            model = vgsl.TorchVGSLModel.load_model(file_field.file.name)
        except KrakenInvalidModelException:
            raise forms.ValidationError(_("The provided model could not be loaded."))
        self._model_job = model.model_type
        if self._model_job not in ('segmentation', 'recognition'):
            raise forms.ValidationError(_("Invalid model (Couldn't determine whether it's a segmentation or recognition model)."))
        elif self._model_job == 'recognition' and model.seg_type == "bbox":
            raise forms.ValidationError(_("eScriptorium is not compatible with bounding box models."))

        try:
            self.model_metadata = model.user_metadata
        except ValueError:
            self.model_metadata = None

        return file_field

    def clean(self):
        # If quotas are enforced, assert that the user still has free disk storage
        if not settings.DISABLE_QUOTAS and not self.user.has_free_disk_storage():
            raise forms.ValidationError(_("You don't have any disk storage left."))

        if not getattr(self, '_model_job', None):
            return super().clean()
        # Update the job field on the instantiated model from the cleaned model field
        if self._model_job == 'segmentation':
            self.instance.job = OcrModel.MODEL_JOB_SEGMENT
        elif self._model_job == 'recognition':
            self.instance.job = OcrModel.MODEL_JOB_RECOGNIZE
        return super().clean()

    def save(self, commit=True):
        model = super().save(commit=False)
        model.file_size = model.file.size
        if self.model_metadata:
            try:
                model.training_accuracy = self.model_metadata.get('accuracy')[-1][1]
            except (IndexError, AttributeError, TypeError):
                pass

            try:
                model.training_epoch = (self.model_metadata
                                        .get('hyper_params')
                                        .get('completed_epochs'))
            except AttributeError:
                pass

        model.save()


class DocumentProcessFormBase(forms.Form):
    CHECK_GPU_QUOTA = False
    CHECK_DISK_QUOTA = False

    parts = forms.ModelMultipleChoiceField(queryset=None)

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def clean(self):
        # If quotas are enforced, assert that the user still has free CPU minutes, GPU minutes and disk storage
        if not settings.DISABLE_QUOTAS:
            if not self.user.has_free_cpu_minutes():
                raise forms.ValidationError(_("You don't have any CPU minutes left."))
            if self.CHECK_GPU_QUOTA and not self.user.has_free_gpu_minutes():
                raise forms.ValidationError(_("You don't have any GPU minutes left."))
            if self.CHECK_DISK_QUOTA and not self.user.has_free_disk_storage():
                raise forms.ValidationError(_("You don't have any disk storage left."))

        return super().clean()


class BinarizeForm(BootstrapFormMixin, DocumentProcessFormBase):
    # binarizer = forms.ChoiceField(required=False,
    #                               choices=BINARIZER_CHOICES,
    #                               initial='kraken')

    bw_image = forms.ImageField(required=False)
    threshold = forms.FloatField(
        required=False, initial=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(1)],
        help_text=_('Increase it for low contrast documents, if the letters are not visible enough.'),
        widget=forms.NumberInput(
            attrs={'type': 'range', 'step': '0.05',
                   'min': '0.1', 'max': '1'}))

    def clean_bw_image(self):
        img = self.cleaned_data.get('bw_image')
        if not img:
            return
        if len(self.cleaned_data.get('parts')) != 1:
            raise forms.ValidationError(_("Uploaded image with more than one selected image."))
        # Beware: don't close the file here !
        fh = Image.open(img)
        if fh.mode not in ['1', 'L']:
            raise forms.ValidationError(_("Uploaded image should be black and white."))
        isize = (self.cleaned_data.get('parts')[0].image.width, self.parts[0].image.height)
        if fh.size != isize:
            raise forms.ValidationError(_("Uploaded image should be the same size as original image {size}.").format(size=isize))
        return img

    def process(self):
        parts = self.cleaned_data.get('parts')
        if len(parts) == 1 and self.cleaned_data.get('bw_image'):
            self.parts[0].bw_image = self.cleaned_data['bw_image']
            self.parts[0].save()
        else:
            for part in parts:
                part.task('binarize',
                          user_pk=self.user.pk,
                          threshold=self.cleaned_data.get('threshold'))


class SegmentForm(BootstrapFormMixin, DocumentProcessFormBase):
    model = forms.ModelChoiceField(
        queryset=OcrModel.objects.filter(job=OcrModel.MODEL_JOB_SEGMENT),
        label=_("Model"),
        empty_label="default ({name})".format(
            name=settings.KRAKEN_DEFAULT_SEGMENTATION_MODEL.rsplit('/')[-1]),
        required=False)

    SEGMENTATION_STEPS_CHOICES = (
        ('both', _('Lines and regions')),
        ('lines', _('Lines Baselines and Masks')),
        ('masks', _('Only lines Masks')),
        ('regions', _('Regions')),
    )
    segmentation_steps = forms.ChoiceField(
        choices=SEGMENTATION_STEPS_CHOICES,
        initial='both', required=False)

    TEXT_DIRECTION_CHOICES = (('horizontal-lr', _("Horizontal l2r")),
                              ('horizontal-rl', _("Horizontal r2l")),
                              ('vertical-lr', _("Vertical l2r")),
                              ('vertical-rl', _("Vertical r2l")))
    text_direction = forms.ChoiceField(
        initial='horizontal-lr',
        required=False,
        choices=TEXT_DIRECTION_CHOICES)

    override = forms.BooleanField(
        required=False, initial=True,
        help_text=_("If checked, deletes existing segmentation <b>and bound transcriptions</b> first!"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.document.read_direction == self.document.READ_DIRECTION_RTL:
            self.initial['text_direction'] = 'horizontal-rl'

        self.fields['model'].queryset = self.fields['model'].queryset.filter(
            Q(public=True) |
            Q(owner=self.user) |
            Q(ocr_model_rights__user=self.user) |
            Q(ocr_model_rights__group__user=self.user)
        ).distinct()

    def process(self):
        model = self.cleaned_data.get('model')

        if model:
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                document=self.document,
                ocr_model=model,
                defaults={'executed_on': timezone.now()}
            )
            if not created:
                ocr_model_document.executed_on = timezone.now()
                ocr_model_document.save()

        for part in self.cleaned_data.get('parts'):
            part.task('segment',
                      user_pk=self.user.pk,
                      steps=self.cleaned_data.get('segmentation_steps'),
                      text_direction=self.cleaned_data.get('text_direction'),
                      model_pk=model and model.pk or None,  # None means default model
                      override=self.cleaned_data.get('override'))


class TranscribeForm(BootstrapFormMixin, DocumentProcessFormBase):
    model = forms.ModelChoiceField(queryset=OcrModel.objects
                                   .filter(job=OcrModel.MODEL_JOB_RECOGNIZE),
                                   required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['model'].queryset = self.fields['model'].queryset.filter(
            Q(public=True) |
            Q(owner=self.user) |
            Q(ocr_model_rights__user=self.user) |
            Q(ocr_model_rights__group__user=self.user)
        ).distinct()

    def process(self):
        model = self.cleaned_data.get('model')

        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=model,
            defaults={'executed_on': timezone.now()}
        )
        if not created:
            ocr_model_document.executed_on = timezone.now()
            ocr_model_document.save()

        for part in self.cleaned_data.get('parts'):
            part.task('transcribe',
                      user_pk=self.user.pk,
                      model_pk=model.pk)


class TrainMixin():
    CHECK_GPU_QUOTA = True
    CHECK_DISK_QUOTA = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Note: Only a owner should be able to train on top of an existing model
        # if the model is public, the user can only clone it (override=False)
        self.fields['model'].queryset = (self.fields['model'].queryset
                                         .filter(Q(public=True) | Q(owner=self.user)))

    @property
    def model_job(self):
        raise NotImplementedError

    def clean(self):
        cleaned_data = super().clean()

        model = cleaned_data['model']
        if model and model.training:
            raise AlreadyProcessingException

        override = cleaned_data['override']
        if model and model.owner != self.user and override:
            raise forms.ValidationError(
                "You can't overwrite the existing file of a model you don't own."
            )

        # TODO: Should be created by the task too to prevent creating empty OcrModel instances ?!
        if not model:
            cleaned_data['model'] = OcrModel.objects.create(
                owner=self.user,
                name=self.cleaned_data.get('model_name'),
                job=self.model_job,
                file_size=0)
        elif not override:
            cleaned_data['model'] = model.clone_for_training(
                self.user, name=self.cleaned_data.get('model_name'))

        return cleaned_data

    def process(self):
        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=self.cleaned_data.get('model'),
            defaults={'trained_on': timezone.now()}
        )
        if not created:
            ocr_model_document.trained_on = timezone.now()
            ocr_model_document.save()


class SegTrainForm(BootstrapFormMixin, TrainMixin, DocumentProcessFormBase):
    model_name = forms.CharField(required=False)
    model = forms.ModelChoiceField(queryset=OcrModel.objects.filter(job=OcrModel.MODEL_JOB_SEGMENT),
                                   required=False)
    override = forms.BooleanField(required=False, label="Overwrite existing model file")

    @property
    def model_job(self):
        return OcrModel.MODEL_JOB_SEGMENT

    def clean(self):
        cleaned_data = super().clean()
        if len(cleaned_data.get('parts')) < 2:
            raise forms.ValidationError("Segmentation training requires at least 2 images.")
        # check that we have lines
        return cleaned_data

    def process(self):
        model = self.cleaned_data.get('model')
        model.segtrain(self.document,
                       self.cleaned_data.get('parts'),
                       user=self.user)
        super().process()


class RecTrainForm(BootstrapFormMixin, TrainMixin, DocumentProcessFormBase):
    model_name = forms.CharField(required=False)
    model = forms.ModelChoiceField(queryset=OcrModel.objects.filter(job=OcrModel.MODEL_JOB_RECOGNIZE),
                                   required=False)
    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all(), required=False)
    override = forms.BooleanField(required=False, label="Overwrite existing model file")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)

    @property
    def model_job(self):
        return OcrModel.MODEL_JOB_RECOGNIZE

    def process(self):
        model = self.cleaned_data.get('model')
        model.train(self.cleaned_data.get('parts'),
                    self.cleaned_data['transcription'],
                    user=self.user)
        super().process()


class UploadImageForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DocumentPart
        fields = ('image',)

    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('document')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean(self):
        # If quotas are enforced, assert that the user still has free disk storage
        if not settings.DISABLE_QUOTAS and not self.user.has_free_disk_storage():
            raise forms.ValidationError(_("You don't have any disk storage left."))

        return super().clean()

    def save(self, commit=True):
        part = super().save(commit=False)
        part.document = self.document
        if commit:
            part.save()
        return part


class ModelRightsForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        model = OcrModel.objects.get(id=kwargs.pop('ocr_model_id'))
        super().__init__(*args, **kwargs)

        self.fields['user'].label = ''
        self.fields['user'].empty_label = 'Choose an user'
        self.fields['user'].queryset = self.fields['user'].queryset.exclude(
            Q(id=model.owner.id) | Q(ocr_model_rights__ocr_model=model)
        ).filter(groups__in=model.owner.groups.all()).distinct()
        self.fields['group'].label = ''
        self.fields['group'].empty_label = 'Choose a group'
        self.fields['group'].queryset = self.fields['group'].queryset.exclude(
            ocr_model_rights__ocr_model=model
        ).filter(id__in=model.owner.groups.all())

    class Meta:
        model = OcrModelRight
        fields = ('user', 'group')
        widgets = {
            'ocr_model': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        group = cleaned_data.get("group")
        if (not user and not group) or (user and group):
            self.add_error('user', 'You must either choose an user OR a group')
            self.add_error('group', 'You must either choose an user OR a group')
        return cleaned_data
