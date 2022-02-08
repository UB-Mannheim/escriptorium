import os
import json
import logging
import numpy as np
import os.path
import shutil
from itertools import groupby

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F, Q
from django.utils.text import slugify
from django.utils.translation import gettext as _

from celery import shared_task
from celery.signals import before_task_publish, task_prerun, task_success, task_failure
from django_redis import get_redis_connection
from easy_thumbnails.files import get_thumbnailer
from kraken.lib import train as kraken_train

from reporting.tasks import create_task_reporting
from users.consumers import send_event

logger = logging.getLogger(__name__)
User = get_user_model()
redis_ = get_redis_connection()


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

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
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
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to convert innexistant DocumentPart : %d', instance_pk)
        return
    part.convert()


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=5 * 60)
def lossless_compression(instance_pk=None, user_pk=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        return
    part.compress()


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def binarize(instance_pk=None, user_pk=None, binarizer=None, threshold=None, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to binarize innexistant DocumentPart : %d', instance_pk)
        return

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
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
        'baselines': [{'script': line.typology and line.typology.name or 'default',
                       'baseline': line.baseline}
                      for line in part.lines.only('baseline', 'typology')
                      if line.baseline],
        'regions':  {typo: list(reg.box for reg in regs)
                     for typo, regs in groupby(
                        part.blocks.only('box', 'typology').order_by('typology'),
                        key=lambda reg: reg.typology and reg.typology.name or 'default')}
    }
    return data


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
                if user.cpu_minutes_limit() != None:
                    assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
                if user.gpu_minutes_limit() != None:
                    assert user.has_free_gpu_minutes(), f"User {user.id} doesn't have any GPU minutes left"
                if user.disk_storage_limit() != None:
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
        load = settings.KRAKEN_DEFAULT_SEGMENTATION_MODEL
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

        DEVICE = getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu')
        LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)
        trainer = kraken_train.KrakenTrainer.segmentation_train_gen(
            message=msg,
            output=os.path.join(model_dir, 'version'),
            format_type=None,
            device=DEVICE,
            load=load,
            training_data=training_data,
            evaluation_data=evaluation_data,
            threads=LOAD_THREADS,
            augment=True,
            resize='both',
            hyper_params={'epochs': 30},
            load_hyper_parameters=True,
            topline=topline
        )

        def _print_eval(epoch=0, accuracy=0, mean_acc=0, mean_iu=0, freq_iu=0,
                        val_metric=0):
            model.refresh_from_db()
            model.training_epoch = epoch
            model.training_accuracy = float(val_metric)
            # model.training_total = chars
            # model.training_errors = error
            relpath = os.path.relpath(model_dir, settings.MEDIA_ROOT)
            model.new_version(file=f'{relpath}/version_{epoch}.mlmodel')
            model.save()

            send_event('document', document_pk, "training:eval", {
                "id": model.pk,
                'versions': model.versions,
                'epoch': epoch,
                'accuracy': float(val_metric)
                # 'chars': chars,
                # 'error': error
            })

        trainer.run(_print_eval)

        best_version = os.path.join(model_dir,
                                    f'version_{trainer.stopper.best_epoch}.mlmodel')

        try:
            shutil.copy(best_version, model.file.path)  # os.path.join(model_dir, filename)
        except FileNotFoundError as e:
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
        if user:
            user.notify(_("Training finished!"),
                        id="training-success",
                        level='success')
    finally:
        model.training = False
        model.file_size = model.file.size
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
    except DocumentPart.DoesNotExist as e:
        logger.error('Trying to segment innexistant DocumentPart : %d', instance_pk)
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
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
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
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist as e:
        logger.error('Trying to recalculate masks of innexistant DocumentPart : %d', instance_pk)
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

    DEVICE = getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu')
    LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)
    trainer = (kraken_train.KrakenTrainer
               .recognition_train_gen(device=DEVICE,
                                      load=load,
                                      output=os.path.join(model_dir, 'version'),
                                      format_type=None,
                                      training_data=training_data,
                                      evaluation_data=evaluation_data,
                                      resize='add',
                                      threads=LOAD_THREADS,
                                      augment=False,
                                      hyper_params={'batch_size': 1},
                                      load_hyper_parameters=True))

    def _print_eval(epoch=0, accuracy=0, chars=0, error=0, val_metric=0):
        model.refresh_from_db()
        model.training_epoch = epoch
        model.training_accuracy = float(accuracy.item())
        model.training_total = int(chars)
        model.training_errors = int(error)
        relpath = os.path.relpath(model_dir, settings.MEDIA_ROOT)
        model.new_version(file=f'{relpath}/version_{epoch}.mlmodel')
        model.save()

        send_event('document', document.pk, "training:eval", {
            "id": model.pk,
            'versions': model.versions,
            'epoch': epoch,
            'accuracy': float(accuracy.item()),
            'chars': int(chars),
            'error': int(error)})

    trainer.run(_print_eval)
    best_version = os.path.join(model_dir, f'version_{trainer.stopper.best_epoch}.mlmodel')
    shutil.copy(best_version, model.file.path)


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def train(task, transcription_pk, model_pk=None, part_pks=None, user_pk=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes, GPU minutes and disk storage
            if not settings.DISABLE_QUOTAS:
                if user.cpu_minutes_limit() != None:
                    assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
                if user.gpu_minutes_limit() != None:
                    assert user.has_free_gpu_minutes(), f"User {user.id} doesn't have any GPU minutes left"
                if user.disk_storage_limit() != None:
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
        send_event('document', document.pk, "training:error", {
            "id": model.pk,
        })
        if user:
            user.notify(_("Something went wrong during the training process!"),
                        id="training-error", level='danger')
        logger.exception(e)
    else:
        if user:
            user.notify(_("Training finished!"),
                        id="training-success",
                        level='success')
    finally:
        model.training = False
        model.file_size = model.file.size
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

        logger.error('Trying to transcribe innexistant DocumentPart : %d', instance_pk)
        return

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
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


def check_signal_order(old_signal, new_signal):
    SIGNAL_ORDER = ['before_task_publish', 'task_prerun', 'task_failure', 'task_success']
    return SIGNAL_ORDER.index(old_signal) < SIGNAL_ORDER.index(new_signal)


@before_task_publish.connect
def before_publish_state(sender=None, body=None, **kwargs):
    if not sender.startswith('core.tasks') or sender.endswith('train'):
        return
    instance_id = body[1]["instance_pk"]
    data = json.loads(redis_.get('process-%d' % instance_id) or '{}')

    signal_name = kwargs['signal'].name

    try:
        # protects against signal race condition
        if (data[sender]['task_id'] == sender.request.id and
            not check_signal_order(data[sender]['status'], signal_name)):
            return
    except (KeyError, AttributeError):
        pass

    data[sender] = {
        "task_id": kwargs['headers']['id'],
        "status": 'before_task_publish'
    }
    redis_.set('process-%d' % instance_id, json.dumps(data))
    try:
        update_client_state(instance_id, sender, 'pending')
    except NameError:
        pass


@task_prerun.connect
@task_success.connect
@task_failure.connect
def done_state(sender=None, body=None, **kwargs):
    if not sender.name.startswith('core.tasks') or sender.name.endswith('train'):
        return
    instance_id = sender.request.kwargs["instance_pk"]

    try:
        data = json.loads(redis_.get('process-%d' % instance_id) or '{}')
    except TypeError as e:
        logger.exception(e)
        return

    signal_name = kwargs['signal'].name

    try:
        # protects against signal race condition
        if (data[sender.name]['task_id'] == sender.request.id and
            not check_signal_order(data[sender.name]['status'], signal_name)):
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
    redis_.set('process-%d' % instance_id, json.dumps(data))

    if status == 'done':
        result = kwargs.get('result', None)
    else:
        result = None
    update_client_state(instance_id, sender.name, status, task_id=sender.request.id, data=result)
