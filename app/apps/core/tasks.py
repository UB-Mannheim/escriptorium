import json
import logging
import os
import os.path
import shutil
from itertools import groupby

import numpy as np
from celery import shared_task
from celery.signals import before_task_publish, task_failure, task_prerun, task_success
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F, Q
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django_redis import get_redis_connection
from easy_thumbnails.files import get_thumbnailer
from kraken.kraken import SEGMENTATION_DEFAULT_MODEL
from kraken.lib.default_specs import RECOGNITION_HYPER_PARAMS, SEGMENTATION_HYPER_PARAMS
from kraken.lib.train import KrakenTrainer, RecognitionModel, SegmentationModel
from pytorch_lightning.callbacks import Callback

# DO NOT REMOVE THIS IMPORT, it will break celery tasks located in this file
from reporting.tasks import create_task_reporting  # noqa F401
from users.consumers import send_event

logger = logging.getLogger(__name__)
User = get_user_model()
redis_ = get_redis_connection()


# tasks for which to keep track of the state and update the front end
# options:
#   multipart - set True if task uses array of part_pks instead of instance_pk of a single part
STATE_TASKS = {
    'core.tasks.binarize': {'multipart': False},
    'core.tasks.segment': {'multipart': False},
    'core.tasks.transcribe': {'multipart': False},
    'core.tasks.align': {'multipart': True},
}


def update_client_state(part_id, task, status, task_id=None, data=None):
    DocumentPart = apps.get_model('core', 'DocumentPart')
    part = DocumentPart.objects.get(pk=part_id)
    task_name = task.split('.')[-1]
    send_event('document', part.document.pk, "part:workflow", {
        "id": part.pk,
        "process": task_name,
        "status": status,
        "task_id": task_id,
        "data": data or {}
    })


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60)
def generate_part_thumbnails(instance_pk=None, user_pk=None, **kwargs):
    if not getattr(settings, 'THUMBNAIL_ENABLE', True):
        return

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress non-existent DocumentPart : %d', instance_pk)
        return

    aliases = {}
    thbnr = get_thumbnailer(part.image)
    for alias, config in settings.THUMBNAIL_ALIASES[''].items():
        aliases[alias] = thbnr.get_thumbnail(config).url
    return aliases


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=3 * 60)
def convert(instance_pk=None, user_pk=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to convert non-existent DocumentPart : %d', instance_pk)
        return
    part.convert()


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=5 * 60)
def lossless_compression(instance_pk=None, user_pk=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress non-existent DocumentPart : %d', instance_pk)
        return
    part.compress()


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def binarize(instance_pk=None, user_pk=None, binarizer=None, threshold=None, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to binarize non-existent DocumentPart : %d', instance_pk)
        return

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    try:
        part.binarize(threshold=threshold)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the binarization!"),
                        id="binarization-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_CREATED
        part.save()
        logger.exception(e)
        raise e
    else:
        if user:
            user.notify(_("Binarization done!"),
                        id="binarization-success", level='success')


def make_segmentation_training_data(part):
    data = {
        'image': part.image.path,
        'baselines': [{'tags': {'type': line.typology and line.typology.name or 'default'},
                       'baseline': line.baseline}
                      for line in part.lines.only('baseline', 'typology')
                      if line.baseline],
        'regions': {typo: list(reg.box for reg in regs)
                    for typo, regs in groupby(
            part.blocks.only('box', 'typology').order_by('typology'),
            key=lambda reg: reg.typology and reg.typology.name or 'default')}
    }
    return data


class FrontendFeedback(Callback):
    """
    Callback that sends websocket messages to the front for feedback display
    """
    def __init__(self, es_model, model_directory, document_pk, *args, **kwargs):
        self.es_model = es_model
        self.model_directory = model_directory
        self.document_pk = document_pk
        super().__init__(*args, **kwargs)

    def on_train_epoch_end(self, trainer, pl_module) -> None:
        self.es_model.refresh_from_db()
        self.es_model.training_epoch = trainer.current_epoch
        val_metric = float(trainer.logged_metrics['val_metric'])
        self.es_model.training_accuracy = val_metric
        # model.training_total = chars
        # model.training_errors = error
        relpath = os.path.relpath(self.model_directory, settings.MEDIA_ROOT)
        self.es_model.new_version(file=f'{relpath}/version_{trainer.current_epoch}.mlmodel')
        self.es_model.save()

        send_event('document', self.document_pk, "training:eval", {
            "id": self.es_model.pk,
            'versions': self.es_model.versions,
            'epoch': trainer.current_epoch,
            'accuracy': val_metric
            # 'chars': chars,
            # 'error': error
        })


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def segtrain(task, model_pk, part_pks, document_pk=None, user_pk=None, **kwargs):
    # # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes, GPU minutes and disk storage
            if not settings.DISABLE_QUOTAS:
                if user.cpu_minutes_limit() is not None:
                    assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
                if user.gpu_minutes_limit() is not None:
                    assert user.has_free_gpu_minutes(), f"User {user.id} doesn't have any GPU minutes left"
                if user.disk_storage_limit() is not None:
                    assert user.has_free_disk_storage(), f"User {user.id} doesn't have any disk storage left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    def msg(txt, fg=None, nl=False):
        logger.info(txt)

    redis_.set('segtrain-%d' % model_pk, json.dumps({'task_id': task.request.id}))

    Document = apps.get_model('core', 'Document')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    OcrModel = apps.get_model('core', 'OcrModel')

    model = OcrModel.objects.get(pk=model_pk)

    try:
        load = model.file.path
    except ValueError:  # model is empty
        load = SEGMENTATION_DEFAULT_MODEL
        model.file = model.file.field.upload_to(model, slugify(model.name) + '.mlmodel')

    model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    try:
        model.training = True
        model.save()
        send_event('document', document_pk, "training:start", {
            "id": model.pk,
        })
        qs = DocumentPart.objects.filter(pk__in=part_pks).prefetch_related('lines')

        ground_truth = list(qs)
        if ground_truth[0].document.line_offset == Document.LINE_OFFSET_TOPLINE:
            topline = True
        elif ground_truth[0].document.line_offset == Document.LINE_OFFSET_CENTERLINE:
            topline = None
        else:
            topline = False

        np.random.default_rng(241960353267317949653744176059648850006).shuffle(ground_truth)
        partition = max(1, int(len(ground_truth) / 10))

        training_data = []
        evaluation_data = []
        for part in qs[partition:]:
            training_data.append(make_segmentation_training_data(part))
        for part in qs[:partition]:
            evaluation_data.append(make_segmentation_training_data(part))

        device_ = getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu')
        if device_ == 'cpu':
            device = None
        elif device_.startswith('cuda'):
            device = [int(device_.split(':')[-1])]

        LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)

        kraken_model = SegmentationModel(SEGMENTATION_HYPER_PARAMS,
                                         output=os.path.join(model_dir, 'version'),
                                         # spec=spec,
                                         model=load,
                                         format_type=None,
                                         training_data=training_data,
                                         evaluation_data=evaluation_data,
                                         partition=partition,
                                         num_workers=LOAD_THREADS,
                                         load_hyper_parameters=True,
                                         # force_binarization=force_binarization,
                                         # suppress_regions=suppress_regions,
                                         # suppress_baselines=suppress_baselines,
                                         # valid_regions=valid_regions,
                                         # valid_baselines=valid_baselines,
                                         # merge_regions=merge_regions,
                                         # merge_baselines=merge_baselines,
                                         # bounding_regions=bounding_regions,
                                         resize='both',
                                         topline=topline)

        trainer = KrakenTrainer(gpus=device,
                                # max_epochs=2,
                                # min_epochs=5,
                                enable_progress_bar=False,
                                val_check_interval=1,
                                callbacks=[FrontendFeedback(model, model_dir, document_pk)])

        trainer.fit(kraken_model)

        best_version = os.path.join(model_dir,
                                    f'version_{kraken_model.best_epoch}.mlmodel')

        try:
            shutil.copy(best_version, model.file.path)  # os.path.join(model_dir, filename)
        except FileNotFoundError:
            user.notify(_("Training didn't get better results than base model!"),
                        id="seg-no-gain-error", level='warning')
            shutil.copy(load, model.file.path)

    except Exception as e:
        send_event('document', document_pk, "training:error", {
            "id": model.pk,
        })
        if user:
            user.notify(_("Something went wrong during the segmenter training process!"),
                        id="training-error", level='danger')
        logger.exception(e)
        raise e
    else:
        model.file_size = model.file.size

        if user:
            user.notify(_("Training finished!"),
                        id="training-success",
                        level='success')
    finally:
        model.training = False
        model.save()

        send_event('document', document_pk, "training:done", {
            "id": model.pk,
        })


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=5 * 60)
def segment(instance_pk=None, user_pk=None, model_pk=None,
            steps=None, text_direction=None, override=None,
            **kwargs):
    """
    steps can be either 'regions', 'lines' or 'both'
    """
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to segment non-existent DocumentPart : %d', instance_pk)
        return

    try:
        OcrModel = apps.get_model('core', 'OcrModel')
        model = OcrModel.objects.get(pk=model_pk)
    except OcrModel.DoesNotExist:
        model = None

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    try:
        if steps == 'masks':
            part.make_masks()
        else:
            part.segment(steps=steps,
                         override=override,
                         text_direction=text_direction,
                         model=model)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the segmentation!"),
                        id="segmentation-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_CONVERTED
        part.save()
        logger.exception(e)
        raise e
    else:
        if user:
            user.notify(_("Segmentation done!"),
                        id="segmentation-success", level='success')


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60)
def recalculate_masks(instance_pk=None, user_pk=None, only=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to recalculate masks of non-existent DocumentPart : %d', instance_pk)
        return

    result = part.make_masks(only=only)
    send_event('document', part.document.pk, "part:mask", {
        "id": part.pk,
        "lines": [{'pk': line.pk, 'mask': line.mask} for line in result]
    })


def train_(qs, document, transcription, model=None, user=None):
    # # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    # try to minimize what is loaded in memory for large datasets
    ground_truth = list(qs.values('content',
                                  baseline=F('line__baseline'),
                                  mask=F('line__mask'),
                                  image=F('line__document_part__image')))

    np.random.default_rng(241960353267317949653744176059648850006).shuffle(ground_truth)

    partition = int(len(ground_truth) / 10)

    training_data = [{'image': os.path.join(settings.MEDIA_ROOT, lt['image']),
                      'text': lt['content'],
                      'baseline': lt['baseline'],
                      'boundary': lt['mask']} for lt in ground_truth[partition:]]
    evaluation_data = [{'image': os.path.join(settings.MEDIA_ROOT, lt['image']),
                        'text': lt['content'],
                        'baseline': lt['baseline'],
                        'boundary': lt['mask']} for lt in ground_truth[:partition]]

    load = None
    try:
        load = model.file.path
    except ValueError:  # model is empty
        filename = slugify(model.name) + '.mlmodel'
        model.file = model.file.field.upload_to(model, filename)
        model.save()

    model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    device_ = getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu')
    if device_ == 'cpu':
        device = None
    elif device_.startswith('cuda'):
        device = [int(device_.split(':')[-1])]

    LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)

    if (document.main_script
        and (document.main_script.text_direction == 'horizontal-rl'
             or document.main_script.text_direction == 'vertical-rl')):
        reorder = 'R'
    else:
        reorder = 'L'

    kraken_model = RecognitionModel(hyper_params=RECOGNITION_HYPER_PARAMS,
                                    output=os.path.join(model_dir, 'version'),
                                    # spec=spec,
                                    # append=append,
                                    model=load,
                                    reorder=reorder,
                                    format_type=None,
                                    training_data=training_data,
                                    evaluation_data=evaluation_data,
                                    partition=partition,
                                    # binary_dataset_split=fixed_splits,
                                    num_workers=LOAD_THREADS,
                                    load_hyper_parameters=True,
                                    repolygonize=False,
                                    # force_binarization=force_binarization,
                                    # codec=codec,
                                    resize='add')

    trainer = KrakenTrainer(gpus=device,
                            # max_epochs=,
                            # min_epochs=hyper_params['min_epochs'],
                            enable_progress_bar=False,
                            val_check_interval=1,
                            # deterministic=ctx.meta['deterministic'],
                            callbacks=[FrontendFeedback(model, model_dir, document.pk)])

    trainer.fit(kraken_model)

    if kraken_model.best_epoch != 0:
        best_version = os.path.join(model_dir, f'version_{kraken_model.best_epoch}.mlmodel')
        shutil.copy(best_version, model.file.path)
    else:
        raise ValueError('No model created.')


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def train(task, transcription_pk, model_pk=None, part_pks=None, user_pk=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes, GPU minutes and disk storage
            if not settings.DISABLE_QUOTAS:
                if user.cpu_minutes_limit() is not None:
                    assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
                if user.gpu_minutes_limit() is not None:
                    assert user.has_free_gpu_minutes(), f"User {user.id} doesn't have any GPU minutes left"
                if user.disk_storage_limit() is not None:
                    assert user.has_free_disk_storage(), f"User {user.id} doesn't have any disk storage left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    redis_.set('training-%d' % model_pk, json.dumps({'task_id': task.request.id}))

    Transcription = apps.get_model('core', 'Transcription')
    LineTranscription = apps.get_model('core', 'LineTranscription')
    OcrModel = apps.get_model('core', 'OcrModel')

    try:
        model = OcrModel.objects.get(pk=model_pk)
        model.training = True
        model.save()
        transcription = Transcription.objects.get(pk=transcription_pk)
        document = transcription.document
        send_event('document', document.pk, "training:start", {
            "id": model.pk,
        })
        qs = (LineTranscription.objects
              .filter(transcription=transcription,
                      line__document_part__pk__in=part_pks)
              .exclude(Q(content='') | Q(content=None)))
        train_(qs, document, transcription, model=model, user=user)
    except Exception as e:
        # TODO: catch KrakenInputException specificely?
        send_event('document', document.pk, "training:error", {
            "id": model.pk,
        })
        if user:
            user.notify(_("Something went wrong during the training process!"),
                        id="training-error", level='danger')
        logger.exception(e)
    else:
        model.file_size = model.file.size

        if user:
            user.notify(_("Training finished!"),
                        id="training-success",
                        level='success')
    finally:
        model.training = False
        model.save()

        send_event('document', document.pk, "training:done", {
            "id": model.pk,
        })


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def transcribe(instance_pk=None, model_pk=None, user_pk=None, text_direction=None, **kwargs):

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:

        logger.error('Trying to transcribe non-existent DocumentPart : %d', instance_pk)
        return

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    try:
        OcrModel = apps.get_model('core', 'OcrModel')
        model = OcrModel.objects.get(pk=model_pk)
        part.transcribe(model)

    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the transcription!"),
                        id="transcription-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_SEGMENTED
        part.save()
        logger.exception(e)
        raise e
    else:
        if user and model:
            user.notify(_("Transcription done!"),
                        id="transcription-success",
                        level='success')


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def align(
    task,
    document_pk=None,
    part_pks=[],
    user_pk=None,
    transcription_pk=None,
    witness_pk=None,
    n_gram=25,
    max_offset=0,
    merge=False,
    full_doc=True,
    threshold=0.8,
    region_types=["Orphan", "Undefined"],
    layer_name=None,
    beam_size=20,
    **kwargs
):
    """Start document alignment on the passed parts, using the passed settings"""
    try:
        Document = apps.get_model('core', 'Document')
        doc = Document.objects.get(pk=document_pk)
    except Document.DoesNotExist:
        logger.error('Trying to align text on non-existent Document: %d', document_pk)
        return

    if user_pk:
        try:
            user = get_user_model().objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    # set redis alignment task data
    redis_.set('align-%d' % document_pk, json.dumps({'task_id': task.request.id}))

    try:
        doc.align(
            part_pks,
            transcription_pk,
            witness_pk,
            n_gram,
            max_offset,
            merge,
            full_doc,
            threshold,
            region_types,
            layer_name,
            beam_size,
        )
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the alignment!"),
                        id="alignment-error", level='danger')
        DocumentPart = apps.get_model('core', 'DocumentPart')
        parts = DocumentPart.objects.filter(pk__in=part_pks)
        for part in parts:
            part.workflow_state = part.WORKFLOW_STATE_TRANSCRIBING
            send_event("document", document_pk, "part:workflow", {
                "id": part.pk,
                "process": "align",
                "status": "canceled",
                "task_id": task.request.id,
            })
            redis_.set('process-%d' % part.pk, json.dumps({"core.tasks.align": {"status": "canceled"}}))
        DocumentPart.objects.bulk_update(parts, ["workflow_state"])
        logger.exception(e)
        raise e
    else:
        if user:
            user.notify(_("Alignment done!"),
                        id="alignment-success",
                        level='success')


def check_signal_order(old_signal, new_signal):
    SIGNAL_ORDER = ['before_task_publish', 'task_prerun', 'task_failure', 'task_success']
    return SIGNAL_ORDER.index(old_signal) < SIGNAL_ORDER.index(new_signal)


@before_task_publish.connect
def before_publish_state(sender=None, body=None, **kwargs):
    if sender not in STATE_TASKS.keys():
        return
    if STATE_TASKS[sender]["multipart"] is True:
        # multipart will have array of part_pks instead of instance_pk
        instance_ids = body[1]["part_pks"]
    else:
        instance_pk = body[1]["instance_pk"]
        instance_ids = [instance_pk]

    for instance_id in instance_ids:
        data = json.loads(redis_.get('process-%d' % instance_id) or '{}')

    signal_name = kwargs['signal'].name

    try:
        # protects against signal race condition
        if (data[sender]['task_id'] == sender.request.id
                and not check_signal_order(data[sender]['status'], signal_name)):
            return
    except (KeyError, AttributeError):
        pass

    data[sender] = {
        "task_id": kwargs['headers']['id'],
        "status": 'before_task_publish'
    }
    for instance_id in instance_ids:
        redis_.set('process-%d' % instance_id, json.dumps(data))
        try:
            update_client_state(instance_id, sender, 'pending')
        except NameError:
            pass


@task_prerun.connect
@task_success.connect
@task_failure.connect
def done_state(sender=None, body=None, **kwargs):
    if sender.name not in STATE_TASKS.keys():
        return
    if STATE_TASKS[sender.name]["multipart"] is True:
        # multipart will have array of part_pks instead of instance_pk
        instance_ids = sender.request.kwargs["part_pks"]
    else:
        instance_pk = sender.request.kwargs["instance_pk"]
        instance_ids = [instance_pk]

    try:
        for instance_id in instance_ids:
            data = json.loads(redis_.get('process-%d' % instance_id) or '{}')
    except TypeError as e:
        logger.exception(e)
        return

    signal_name = kwargs['signal'].name

    try:
        # protects against signal race condition
        if (data[sender.name]['task_id'] == sender.request.id
                and not check_signal_order(data[sender.name]['status'], signal_name)):
            return
    except KeyError:
        pass

    data[sender.name] = {
        "task_id": sender.request.id,
        "status": signal_name
    }
    status = {
        'task_success': 'done',
        'task_failure': 'error',
        'task_prerun': 'ongoing'
    }[signal_name]
    if status == 'error':
        # remove any pending task down the chain
        data = {k: v for k, v in data.items() if v['status'] != 'pending'}
    for instance_id in instance_ids:
        redis_.set('process-%d' % instance_id, json.dumps(data))

    if status == 'done':
        result = kwargs.get('result', None)
    else:
        result = None

    for instance_id in instance_ids:
        update_client_state(instance_id, sender.name, status, task_id=sender.request.id, data=result)
