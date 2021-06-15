import json
import logging
from PIL import Image

from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.utils import timezone
from django.utils.functional import cached_property
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

        self.fields['project'].queryset = Project.objects.for_user(self.request.user)
        self.fields['project'].empty_label = None
        if self.instance.pk and self.instance.owner != self.request.user:
            self.fields['project'].disabled = True

        self.fields['valid_block_types'].queryset = block_qs.order_by('name')
        self.fields['valid_line_types'].queryset = line_qs.order_by('name')

    class Meta:
        model = Document
        fields = ['project', 'name', 'read_direction', 'main_script',
                  'valid_block_types', 'valid_line_types']
        widgets = {
            'valid_block_types': forms.CheckboxSelectMultiple,
            'valid_line_types': forms.CheckboxSelectMultiple
        }


class ProjectShareForm(BootstrapFormMixin, forms.ModelForm):
    username = forms.CharField(required=False)

    class Meta:
        model = Project
        fields = ['shared_with_groups', 'shared_with_users', 'username']

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

    def save(self, commit=True):
        proj = super().save(commit=commit)
        if self.cleaned_data['username']:
            proj.shared_with_users.add(self.cleaned_data['username'])
        return proj


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
        allowed_extensions=['mlmodel'])]
    )

    class Meta:
        model = OcrModel
        fields = ('name', 'file')

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


class DocumentProcessForm1(BootstrapFormMixin, forms.Form):
    parts = forms.CharField()

    @cached_property
    def parts(self):
        pks = json.loads(self.data.get('parts'))
        parts = DocumentPart.objects.filter(
            document=self.document, pk__in=pks)
        return parts

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)
        # self.fields['typology'].widget = forms.HiddenInput()  # for now
        # self.fields['typology'].initial = Typology.objects.get(name="Page")
        # self.fields['typology'].widget.attrs['title'] = _("Default Typology")
        if self.document.read_direction == self.document.READ_DIRECTION_RTL:
            self.initial['text_direction'] = 'horizontal-rl'
        self.fields['binarizer'].widget.attrs['disabled'] = True

        # Limit querysets to models owned by the user or already linked to this document
        for field in ['train_model', 'segtrain_model', 'seg_model', 'ocr_model']:
            self.fields[field].queryset = self.fields[field].queryset.filter(
                Q(owner=self.user)
                | Q(documents=self.document)
            )

        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)

    def process(self):
        model = self.cleaned_data.get('model')


class DocumentSegmentForm(DocumentProcessForm1):
    SEG_STEPS_CHOICES = (
        ('both', _('Lines and regions')),
        ('lines', _('Lines Baselines and Masks')),
        ('masks', _('Only lines Masks')),
        ('regions', _('Regions')),
    )
    segmentation_steps = forms.ChoiceField(choices=SEG_STEPS_CHOICES,
                                           initial='both', required=False)
    seg_model = forms.ModelChoiceField(queryset=OcrModel.objects.filter(job=OcrModel.MODEL_JOB_SEGMENT),
                                       label=_("Model"), empty_label="default ({name})".format(
            name=settings.KRAKEN_DEFAULT_SEGMENTATION_MODEL.rsplit('/')[-1]),
                                       required=False)
    override = forms.BooleanField(required=False, initial=True,
                                  help_text=_(
                                      "If checked, deletes existing segmentation <b>and bound transcriptions</b> first!"))
    TEXT_DIRECTION_CHOICES = (('horizontal-lr', _("Horizontal l2r")),
                              ('horizontal-rl', _("Horizontal r2l")),
                              ('vertical-lr', _("Vertical l2r")),
                              ('vertical-rl', _("Vertical r2l")))
    text_direction = forms.ChoiceField(initial='horizontal-lr', required=False,
                                       choices=TEXT_DIRECTION_CHOICES)

    def clean(self):
        data = super().clean()
        model_job = OcrModel.MODEL_JOB_SEGMENT

        if data.get('seg_model'):
            model = data.get('seg_model')
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                ocr_model=model,
                document=self.parts[0].document,
                defaults={'executed_on': timezone.now()}
            )
            if not created:
                ocr_model_document.executed_on = timezone.now()
                ocr_model_document.save()
        else:
            model = None

        data['model'] = model
        return data

    def process(self):
        super().process()

        for part in self.parts:
            part.task('segment',
                      user_pk=self.user.pk,
                      steps=self.cleaned_data.get('segmentation_steps'),
                      text_direction=self.cleaned_data.get('text_direction'),
                      model_pk=model and model.pk or None,
                      override=self.cleaned_data.get('override'))


class DocumentTrainForm(DocumentProcessForm1):
    new_model = forms.CharField(required=False, label=_('Model name'))
    train_model = forms.ModelChoiceField(queryset=OcrModel.objects
                                         .filter(job=OcrModel.MODEL_JOB_RECOGNIZE),
                                         label=_("Model"), required=False)

    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all(), required=False)

    def clean_train_model(self):
        model = self.cleaned_data['train_model']
        if model and model.training:
            raise AlreadyProcessingException
        return model

    def clean(self):
        data = super().clean()

        model_job = OcrModel.MODEL_JOB_RECOGNIZE

        if data.get('train_model'):
            model = data.get('train_model')
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                ocr_model=model,
                document=self.parts[0].document,
                defaults={'trained_on': timezone.now()}
            )
            if not created:
                ocr_model_document.trained_on = timezone.now()
                ocr_model_document.save()

        elif data.get('new_model'):
            # file will be created by the training process
            model = OcrModel.objects.create(
                owner=self.user,
                name=data['new_model'],
                job=model_job)
            OcrModelDocument.objects.create(
                document=self.parts[0].document,
                ocr_model=model,
                trained_on=timezone.now(),
            )

        else:
            raise forms.ValidationError(
                    _("Either select a name for your new model or an existing one."))

        data['model'] = model
        return data


    def process(self):
        super().process()

        model.train(self.parts,
                    self.cleaned_data['transcription'],
                    user=self.user)


class DocumentSegtrainForm(DocumentProcessForm1):
    segtrain_model = forms.ModelChoiceField(queryset=OcrModel.objects
                                            .filter(job=OcrModel.MODEL_JOB_SEGMENT),
                                            label=_("Model"), required=False)
    new_model = forms.CharField(required=False, label=_('Model name'))

    def clean(self):
        data = super().clean()


        model_job = OcrModel.MODEL_JOB_SEGMENT
        if len(self.parts) < 2:
            raise forms.ValidationError("Segmentation training requires at least 2 images.")

        if data.get('segtrain_model'):
            model = data.get('segtrain_model')
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                ocr_model=model,
                document=self.parts[0].document,
                defaults={'trained_on': timezone.now()}
            )
            if not created:
                ocr_model_document.trained_on = timezone.now()
                ocr_model_document.save()

        elif data.get('new_model'):
            # file will be created by the training process
            model = OcrModel.objects.create(
                owner=self.user,
                name=data['new_model'],
                job=model_job)
            OcrModelDocument.objects.create(
                document=self.parts[0].document,
                ocr_model=model,
                trained_on=timezone.now(),
            )

        else:

            raise forms.ValidationError(
                _("Either select a name for your new model or an existing one."))

        data['model'] = model
        return data

    def process(self):
        super().process()
        model.segtrain(self.document,
                       self.parts,
                       user=self.user)


class DocumentTranscribeForm(DocumentProcessForm1):

    ocr_model = forms.ModelChoiceField(queryset=OcrModel.objects
                                       .filter(job=OcrModel.MODEL_JOB_RECOGNIZE),
                                       label=_("Model"), required=False)

    def clean(self):
        data = super().clean()

        model_job = OcrModel.MODEL_JOB_RECOGNIZE

        model = data['ocr_model']
        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            ocr_model=model,
            document=self.parts[0].document,
            defaults={'executed_on': timezone.now()}
        )
        if not created:
            ocr_model_document.executed_on = timezone.now()
            ocr_model_document.save()

        data['model'] = model
        return data

    def process(self):
        super().process()
        for part in self.parts:
            part.task('transcribe',
                  user_pk=self.user.pk,
                  model_pk=model and model.pk or None)


class DocumentProcessForm(BootstrapFormMixin, forms.Form):
    # TODO: split this form into one for each process?!
    TASK_BINARIZE = 'binarize'
    TASK_SEGMENT = 'segment'
    TASK_TRAIN = 'train'
    TASK_SEGTRAIN = 'segtrain'
    TASK_TRANSCRIBE = 'transcribe'
    task = forms.ChoiceField(choices=(
        (TASK_BINARIZE, 1),
        (TASK_SEGMENT, 2),
        (TASK_TRAIN, 3),
        (TASK_TRANSCRIBE, 4),
        (TASK_SEGTRAIN, 5),
    ))
    parts = forms.CharField()

    # binarization
    bw_image = forms.ImageField(required=False)
    BINARIZER_CHOICES = (('kraken', _("Kraken")),)
    binarizer = forms.ChoiceField(required=False,
                                  choices=BINARIZER_CHOICES,
                                  initial='kraken')
    threshold = forms.FloatField(
        required=False, initial=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(1)],
        help_text=_('Increase it for low contrast documents, if the letters are not visible enough.'),
        widget=forms.NumberInput(
            attrs={'type': 'range', 'step': '0.05',
                   'min': '0.1', 'max': '1'}))
    # segment
    SEGMENTATION_STEPS_CHOICES = (
        ('both', _('Lines and regions')),
        ('lines', _('Lines Baselines and Masks')),
        ('masks', _('Only lines Masks')),
        ('regions', _('Regions')),
    )
    segmentation_steps = forms.ChoiceField(choices=SEGMENTATION_STEPS_CHOICES,
                                           initial='both', required=False)
    seg_model = forms.ModelChoiceField(queryset=OcrModel.objects.filter(job=OcrModel.MODEL_JOB_SEGMENT),
                                       label=_("Model"), empty_label="default ({name})".format(
                                           name=settings.KRAKEN_DEFAULT_SEGMENTATION_MODEL.rsplit('/')[-1]),
                                       required=False)
    override = forms.BooleanField(required=False, initial=True,
                                  help_text=_("If checked, deletes existing segmentation <b>and bound transcriptions</b> first!"))
    TEXT_DIRECTION_CHOICES = (('horizontal-lr', _("Horizontal l2r")),
                              ('horizontal-rl', _("Horizontal r2l")),
                              ('vertical-lr', _("Vertical l2r")),
                              ('vertical-rl', _("Vertical r2l")))
    text_direction = forms.ChoiceField(initial='horizontal-lr', required=False,
                                       choices=TEXT_DIRECTION_CHOICES)
    # transcribe
    ocr_model = forms.ModelChoiceField(queryset=OcrModel.objects
                                       .filter(job=OcrModel.MODEL_JOB_RECOGNIZE),
                                       label=_("Model"), required=False)

    # train
    new_model = forms.CharField(required=False, label=_('Model name'))
    train_model = forms.ModelChoiceField(queryset=OcrModel.objects
                                         .filter(job=OcrModel.MODEL_JOB_RECOGNIZE),
                                         label=_("Model"), required=False)
    transcription = forms.ModelChoiceField(queryset=Transcription.objects.all(), required=False)

    # segtrain
    segtrain_model = forms.ModelChoiceField(queryset=OcrModel.objects
                                            .filter(job=OcrModel.MODEL_JOB_SEGMENT),
                                            label=_("Model"), required=False)

    # typology = forms.ModelChoiceField(Typology, required=False,
    #                              limit_choices_to={'target': Typology.TARGET_PART})

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)
        # self.fields['typology'].widget = forms.HiddenInput()  # for now
        # self.fields['typology'].initial = Typology.objects.get(name="Page")
        # self.fields['typology'].widget.attrs['title'] = _("Default Typology")
        if self.document.read_direction == self.document.READ_DIRECTION_RTL:
            self.initial['text_direction'] = 'horizontal-rl'
        self.fields['binarizer'].widget.attrs['disabled'] = True

        # Only the owner of a model can train on an existing model
        for field in ['train_model', 'segtrain_model']:
            self.fields[field].queryset = self.fields[field].queryset.filter(owner=self.user)

        # The user can run public models, models he owns and models he has a right on
        for field in ['seg_model', 'ocr_model']:
            self.fields[field].queryset = self.fields[field].queryset.filter(
                Q(public=True) |
                Q(owner=self.user) |
                Q(ocr_model_rights__user=self.user) |
                Q(ocr_model_rights__group__user=self.user)
            ).distinct()

        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)

    @cached_property
    def parts(self):
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
            raise forms.ValidationError(_("Uploaded image should be the same size as original image {size}.").format(size=isize))
        return img

    def clean_train_model(self):
        model = self.cleaned_data['train_model']
        if model and model.training:
            raise AlreadyProcessingException
        return model

    def clean(self):
        data = super().clean()
        task = data.get('task')

        if task == self.TASK_SEGMENT:
            model_job = OcrModel.MODEL_JOB_SEGMENT
        elif task == self.TASK_SEGTRAIN:
            model_job = OcrModel.MODEL_JOB_SEGMENT
            if len(self.parts) < 2:
                raise forms.ValidationError("Segmentation training requires at least 2 images.")
        else:
            model_job = OcrModel.MODEL_JOB_RECOGNIZE

        if task == self.TASK_TRAIN and data.get('train_model'):
            model = data.get('train_model')
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                ocr_model=model,
                document=self.parts[0].document,
                defaults={'trained_on': timezone.now()}
            )
            if not created:
                ocr_model_document.trained_on = timezone.now()
                ocr_model_document.save()

        elif task == self.TASK_SEGTRAIN and data.get('segtrain_model'):
            model = data.get('segtrain_model')
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                ocr_model=model,
                document=self.parts[0].document,
                defaults={'trained_on': timezone.now()}
            )
            if not created:
                ocr_model_document.trained_on = timezone.now()
                ocr_model_document.save()

        elif data.get('new_model'):
            # file will be created by the training process
            model = OcrModel.objects.create(
                owner=self.user,
                name=data['new_model'],
                job=model_job)
            OcrModelDocument.objects.create(
                document=self.parts[0].document,
                ocr_model=model,
                trained_on=timezone.now(),
            )
        elif data.get('ocr_model'):
            model = data.get('ocr_model')
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                ocr_model=model,
                document=self.parts[0].document,
                defaults={'executed_on': timezone.now()}
            )
            if not created:
                ocr_model_document.executed_on = timezone.now()
                ocr_model_document.save()
        elif data.get('seg_model'):
            model = data.get('seg_model')
            ocr_model_document, created = OcrModelDocument.objects.get_or_create(
                ocr_model=model,
                document=self.parts[0].document,
                defaults={'executed_on': timezone.now()}
            )
            if not created:
                ocr_model_document.executed_on = timezone.now()
                ocr_model_document.save()
        else:
            if task in (self.TASK_TRAIN, self.TASK_SEGTRAIN):
                raise forms.ValidationError(
                    _("Either select a name for your new model or an existing one."))
            else:
                model = None

        data['model'] = model
        return data

    def process(self):
        task = self.cleaned_data.get('task')
        model = self.cleaned_data.get('model')

        if task == self.TASK_BINARIZE:
            if len(self.parts) == 1 and self.cleaned_data.get('bw_image'):
                self.parts[0].bw_image = self.cleaned_data['bw_image']
                self.parts[0].save()
            else:
                for part in self.parts:
                    part.task('binarize',
                              user_pk=self.user.pk,
                              threshold=self.cleaned_data.get('threshold'))

        elif task == self.TASK_SEGMENT:
            for part in self.parts:
                part.task('segment',
                          user_pk=self.user.pk,
                          steps=self.cleaned_data.get('segmentation_steps'),
                          text_direction=self.cleaned_data.get('text_direction'),
                          model_pk=model and model.pk or None,
                          override=self.cleaned_data.get('override'))

        elif task == self.TASK_TRANSCRIBE:
            for part in self.parts:
                part.task('transcribe',
                          user_pk=self.user.pk,
                          model_pk=model and model.pk or None)

        elif task == self.TASK_TRAIN:
            model.train(self.parts,
                        self.cleaned_data['transcription'],
                        user=self.user)

        elif task == self.TASK_SEGTRAIN:
            model.segtrain(self.document,
                           self.parts,
                           user=self.user)


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
