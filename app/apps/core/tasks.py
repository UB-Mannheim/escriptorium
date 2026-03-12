import logging
import os
import os.path
import shutil
import tempfile
from collections import defaultdict
from itertools import groupby
from pathlib import Path
from typing import List

import numpy as np
from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F, Q
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.translation import gettext as _
from easy_thumbnails.files import get_thumbnailer
from kraken.configs import (
    BLLASegmentationTrainingConfig,
    BLLASegmentationTrainingDataConfig,
    RecognitionInferenceConfig,
    VGSLRecognitionTrainingConfig,
    VGSLRecognitionTrainingDataConfig,
)
from kraken.containers import BaselineLine, Region, Segmentation
from kraken.kraken import SEGMENTATION_DEFAULT_MODEL
from kraken.lib.arrow_dataset import build_binary_dataset
from kraken.models import convert_models
from kraken.tasks import ForcedAlignmentTaskModel
from kraken.train import (
    BLLASegmentationDataModule,
    BLLASegmentationModel,
    KrakenTrainer,
    VGSLRecognitionDataModule,
    VGSLRecognitionModel,
)
from lightning.pytorch.callbacks import Callback

from core.search import (
    REGEX_SEARCH_MODE,
    WORD_BY_WORD_SEARCH_MODE,
    build_highlighted_replacement_psql,
    search_content_psql_regex,
    search_content_psql_word,
)

# DO NOT REMOVE THIS IMPORT, it will break celery tasks located in this file
from reporting.tasks import create_task_reporting  # noqa F401
from users.consumers import send_event

logger = logging.getLogger(__name__)
User = get_user_model()


class DidNotConverge(Exception):
    pass


def _chunks(lst, n):
    """Yield successive n-sized chunks from lst. If n<0 yields one chunk of whole list."""
    if n < 0:
        yield lst
    else:
        for i in range(0, len(lst), n):
            yield lst[i:i + n]


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


def make_recognition_segmentation(lines) -> List[Segmentation]:
    """
    Groups training data by image for optimized compilation and returns a list
    of Segmentation objects.
    """
    lines_by_img = defaultdict(list)
    for i, lt in enumerate(lines):
        lines_by_img[lt['image']].append(BaselineLine(id=str(i),
                                                      baseline=lt['baseline'],
                                                      boundary=lt['mask'],
                                                      text=lt['content'],
                                                      language=None))
    segs = []
    for img, lines in lines_by_img.items():
        segs.append(Segmentation(text_direction='horizontal-lr',
                                 imagename=os.path.join(settings.MEDIA_ROOT, img),
                                 type='baselines',
                                 lines=lines,
                                 script_detection=False,
                                 language=None))
    return segs


def make_segmentation_training_data(parts) -> List[dict]:
    """
    Converts eScriptorium data model to list of {'doc': Segmentation} dicts
    as expected by BLLASegmentationDataModule with format_type=None.
    """
    segs = []
    for part in parts:
        blls = []
        for line in part.lines.only('baseline', 'typology'):
            if line.baseline:
                tag_name = line.typology.name if line.typology else 'default'
                blls.append(BaselineLine(id=str(line.pk),
                                         baseline=line.baseline,
                                         boundary=line.mask,
                                         tags={'type': [{'type': tag_name}]},
                                         language=None))

        regions = {}
        for typo, regs in groupby(part.blocks.only('box',
                                                   'typology').order_by('typology'),
                                  key=lambda reg: reg.typology and reg.typology.name or 'default'):
            regions[typo] = [Region(id='bar',
                                    boundary=reg.box,
                                    tags={'type': [{'type': typo}]},
                                    language=None) for reg in regs]

        segs.append({'doc': Segmentation(text_direction='horizontal-lr',
                                         imagename=part.image.path,
                                         type='baselines',
                                         lines=blls,
                                         regions=regions,
                                         script_detection=False,
                                         language=None)})
    return segs


class FrontendFeedback(Callback):
    """
    Lightning callback that sends websocket messages to the front for feedback
    display.
    """
    def __init__(self, es_model, model_directory, room_pk, room_name='document', *args, **kwargs):
        self.es_model = es_model
        self.model_directory = model_directory
        self.room_pk = room_pk
        self.room_name = room_name
        super().__init__(*args, **kwargs)

    def on_train_epoch_end(self, trainer, pl_module) -> None:
        self.es_model.refresh_from_db()
        self.es_model.training_epoch = trainer.current_epoch
        # metric key varies by model type
        val_metric = float(
            trainer.logged_metrics.get('val_accuracy')
            or trainer.logged_metrics.get('val_mean_iu')
            or 0.0
        )
        logger.info(f'Epoch {trainer.current_epoch} finished.')
        self.es_model.training_accuracy = val_metric
        relpath = os.path.relpath(self.model_directory, settings.MEDIA_ROOT)
        self.es_model.new_version(file=f'{relpath}/checkpoint_epoch={trainer.current_epoch}.ckpt')
        self.es_model.save()

        send_event(self.room_name, self.room_pk, "training:eval", {
            "id": self.es_model.pk,
            'versions': self.es_model.versions,
            'epoch': trainer.current_epoch,
            'accuracy': val_metric
        })


def _to_ptl_device(device: str):
    if device in ['cpu', 'mps']:
        return device, 'auto'
    elif any([device.startswith(x) for x in ['tpu', 'cuda', 'hpu', 'ipu']]):
        dev, idx = device.split(':')
        if dev == 'cuda':
            dev = 'gpu'
        return dev, [int(idx)]
    raise Exception(f'Invalid device {device} specified')


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def segtrain(model_pk=None, part_pks=[], document_pk=None, task_group_pk=None, user_pk=None, **kwargs):
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

    Document = apps.get_model('core', 'Document')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    OcrModel = apps.get_model('core', 'OcrModel')

    model = OcrModel.objects.get(pk=model_pk)

    try:
        load = model.file.path
    except ValueError:  # model is empty
        load = SEGMENTATION_DEFAULT_MODEL
        model.file = model.file.field.upload_to(model, slugify(model.name) + '.safetensors')

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

        training_data = make_segmentation_training_data(qs[partition:])
        evaluation_data = make_segmentation_training_data(qs[:partition])

        accelerator, device = _to_ptl_device(getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu'))

        LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)
        AMP_MODE = getattr(settings, 'KRAKEN_TRAINING_PRECISION', '32')

        logger.info(f'Starting segmentation training on {accelerator}/{device} '
                    f'(precision: {AMP_MODE}, workers: {LOAD_THREADS}) with '
                    f'{len(training_data)} files')

        if load:
            from kraken.models import load_models
            loaded_nets = load_models(load, tasks=['segmentation'])
            loaded_net = loaded_nets[0] if loaded_nets else None
        else:
            loaded_net = None

        net_class = type(loaded_net).__name__ if loaded_net is not None else None

        if net_class == 'DFINEModel':
            try:
                from dfine.configs import (
                    DFINESegmentationTrainingConfig,
                    DFINESegmentationTrainingDataConfig,
                )
                from dfine.model import (
                    DFINESegmentationDataModule,
                    DFINESegmentationModel,
                )
            except ImportError:
                raise RuntimeError('dfine_kraken package is required to train D-FINE models. '
                                   'Install it with: pip install git+https://github.com/mittagessen/dfine_kraken.git')
            seg_data_config = DFINESegmentationTrainingDataConfig(
                training_data=[item['doc'] for item in training_data],
                evaluation_data=[item['doc'] for item in evaluation_data],
                format_type=None,
                num_workers=LOAD_THREADS,
            )
            seg_train_config = DFINESegmentationTrainingConfig(
                resize='union',
                load_hyper_parameters=True,
            )
            seg_dm = DFINESegmentationDataModule(seg_data_config)
            kraken_model = DFINESegmentationModel.load_from_weights(load, seg_train_config)
        else:
            seg_data_config = BLLASegmentationTrainingDataConfig(
                training_data=training_data,
                evaluation_data=evaluation_data,
                format_type=None,
                num_workers=LOAD_THREADS,
            )
            seg_train_config = BLLASegmentationTrainingConfig(
                resize='union',
                topline=topline,
                load_hyper_parameters=True,
            )
            seg_dm = BLLASegmentationDataModule(seg_data_config)
            if load:
                kraken_model = BLLASegmentationModel.load_from_weights(load, seg_train_config)
            else:
                kraken_model = BLLASegmentationModel(seg_train_config)

        trainer = KrakenTrainer(accelerator=accelerator,
                                devices=device,
                                # max_epochs=2,
                                # min_epochs=5,
                                precision=AMP_MODE,
                                enable_summary=False,
                                enable_progress_bar=False,
                                val_check_interval=1.0,
                                callbacks=[FrontendFeedback(model, model_dir, document_pk)])

        trainer.fit(kraken_model, seg_dm)

        # best checkpoint path from lightning's ModelCheckpoint callback
        best_path = getattr(getattr(trainer, 'checkpoint_callback', None), 'best_model_path', None)
        best_score = getattr(getattr(trainer, 'checkpoint_callback', None), 'best_model_score', None)

        if not best_path:
            logger.info(f'Model {os.path.split(model.file.path)[0]} did not improve.')
            raise DidNotConverge

        try:
            best_score_val = float(best_score) if best_score is not None else 0.0
            logger.info(f'Converting best model {best_path} (accuracy: {best_score_val}) to {model.file.path}.')
            convert_models([best_path], model.file.path)
            model.training_accuracy = best_score_val
        except FileNotFoundError:
            logger.info(f'Model {os.path.split(model.file.path)[0]} did not improve.')
            if user:
                user.notify(_("Training didn't get better results than base model!"),
                            id="seg-no-gain-error", level='warning')
            shutil.copy(load, model.file.path)

    except DidNotConverge:
        send_event('document', ground_truth[0].document.pk, "training:error", {
            "id": model.pk,
        })
        user.notify(_("The model did not converge, probably because of lack of data."),
                    id="training-warning", level='warning')
        model.delete()

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


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60)
def segment(self, instance_pks, user_pk=None, model_pk=None, steps=None, text_direction=None, override=None, task_group_pk=None, **kwargs):
    """
    steps can be either 'regions', 'lines' or 'both'
    """
    DocumentPart = apps.get_model('core', 'DocumentPart')
    OcrModel = apps.get_model('core', 'OcrModel')

    # load model
    try:
        model = OcrModel.objects.get(pk=model_pk)
    except OcrModel.DoesNotExist:
        model = None

    # load user & quota‐check
    user = None
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    for pk in instance_pks:
        # fetch part
        try:
            part = DocumentPart.objects.get(pk=pk)
        except DocumentPart.DoesNotExist:
            logger.error('Trying to segment non-existent DocumentPart : %s', pk)
            continue

        # actual segmentation call
        try:
            if steps == 'masks':
                part.make_masks()
            else:
                part.segment(
                    steps=steps,
                    override=override,
                    text_direction=text_direction,
                    model=model
                )
        except Exception as e:
            # on failure, rollback state & notify
            if user:
                user.notify(
                    _("Something went wrong during the segmentation!"),
                    id="segmentation-error",
                    level='danger'
                )
            part.workflow_state = part.WORKFLOW_STATE_CONVERTED
            part.save()
            send_event(
                "document", part.document.pk, "part:workflow",
                {
                    "id": part.pk,
                    "process": "segment",
                    "status": "canceled",
                    "task_id": self.request.id,
                }
            )
            logger.exception(e)
            # re-raise to allow retry of the batch if desired
            raise
        else:
            # on success, notify & send done event
            if user:
                user.notify(
                    _("Segmentation done!"),
                    id="segmentation-success",
                    level='success'
                )
            send_event(
                "document", part.document.pk, "part:workflow",
                {
                    "id": part.pk,
                    "process": "segment",
                    "status": "done",
                    "task_id": self.request.id,
                }
            )


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=600)
def transcribe(self, instance_pks, model_pk=None, user_pk=None, transcription_pk=None, text_direction=None, task_group_pk=None, **kwargs):
    """
    Run recognition on multiple pages in one celery task.
    """
    DocumentPart = apps.get_model('core', 'DocumentPart')
    OcrModel = apps.get_model('core', 'OcrModel')
    Transcription = apps.get_model('core', 'Transcription')

    # load model
    try:
        model = OcrModel.objects.get(pk=model_pk)
    except OcrModel.DoesNotExist:
        model = None

    # load transcription
    transcription = Transcription.objects.get(pk=transcription_pk)

    # load user & quota‐check
    user = None
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    for pk in instance_pks:
        # fetch part
        try:
            part = DocumentPart.objects.get(pk=pk)
        except DocumentPart.DoesNotExist:
            logger.error('Trying to transcribe non-existent DocumentPart : %s', pk)
            continue

        # actual transcription call
        try:
            part.transcribe(model, transcription, user=user)
        except Exception as e:
            # on failure, rollback state & notify
            if user:
                user.notify(
                    _("Something went wrong during the transcription!"),
                    id="transcription-error",
                    level='danger'
                )
            part.workflow_state = part.WORKFLOW_STATE_SEGMENTED
            part.save()
            send_event(
                "document", part.document.pk, "part:workflow",
                {
                    "id": part.pk,
                    "process": "transcribe",
                    "status": "canceled",
                    "task_id": self.request.id,
                }
            )
            logger.exception(e)
            raise
        else:
            # on success, notify & send done event
            if user:
                user.notify(
                    _("Transcription done!"),
                    id="transcription-success",
                    level='success'
                )
            send_event(
                "document", part.document.pk, "part:workflow",
                {
                    "id": part.pk,
                    "process": "transcribe",
                    "status": "done",
                    "task_id": self.request.id,
                }
            )


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


def train_(qs, document=None, transcription=None, model=None, user=None, collection_pk=None):
    # # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    # try to minimize what is loaded in memory for large datasets
    ground_truth = list(qs.values('content',
                                  baseline=F('line__baseline'),
                                  mask=F('line__mask'),
                                  image=F('line__document_part__image')))

    # shuffle ground truth lines
    np.random.default_rng(241960353267317949653744176059648850006).shuffle(ground_truth)
    partition = int(len(ground_truth) / 10)

    LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)

    AMP_MODE = getattr(settings, 'KRAKEN_TRAINING_PRECISION', '32')

    BATCH_SIZE = getattr(settings, 'KRAKEN_TRAINING_BATCH_SIZE', 12)

    with tempfile.TemporaryDirectory() as tmp_dir:

        train_dir = Path(tmp_dir)

        logger.info(f'Compiling training dataset to {train_dir}/train.arrow')
        train_segs = make_recognition_segmentation(ground_truth[partition:])
        build_binary_dataset(train_segs,
                             output_file=str(train_dir / 'train.arrow'),
                             num_workers=LOAD_THREADS,
                             format_type=None)

        logger.info(f'Compiling validation dataset to {train_dir}/val.arrow')
        val_segs = make_recognition_segmentation(ground_truth[:partition])
        build_binary_dataset(val_segs,
                             output_file=str(train_dir / 'val.arrow'),
                             num_workers=LOAD_THREADS,
                             format_type=None)

        load = None
        try:
            load = model.file.path
        except ValueError:  # model is empty
            filename = slugify(model.name) + '.safetensors'
            model.file = model.file.field.upload_to(model, filename)
            model.save()

        model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])

        if not os.path.exists(model_dir):
            os.makedirs(model_dir)

        accelerator, device = _to_ptl_device(getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu'))

        main_script = None
        if document:
            main_script = document.main_script
        else:
            # if training from collection, get script from first document
            first_line = qs.select_related('line__document_part__document__main_script').first()
            if first_line:
                main_script = getattr(first_line.line.document_part.document, 'main_script', None)

        if (main_script
            and (main_script.text_direction == 'horizontal-rl'
                 or main_script.text_direction == 'vertical-rl')):
            reorder = 'R'
        else:
            reorder = 'L'

        logger.info(f'Starting recognition training on {accelerator}/{device} '
                    f'(precision: {AMP_MODE}, batch_size {BATCH_SIZE} '
                    f', workers: {LOAD_THREADS}) with {len(ground_truth[partition:])} lines')

        rec_data_config = VGSLRecognitionTrainingDataConfig(
            training_data=[str(train_dir / 'train.arrow')],
            evaluation_data=[str(train_dir / 'val.arrow')],
            format_type='binary',
            num_workers=LOAD_THREADS,
        )
        rec_train_config = VGSLRecognitionTrainingConfig(
            batch_size=BATCH_SIZE,
            load_hyper_parameters=True,
            resize='union',
            reorder=reorder,
        )
        rec_dm = VGSLRecognitionDataModule(rec_data_config)
        if load:
            kraken_model = VGSLRecognitionModel.load_from_weights(load, rec_train_config)
        else:
            kraken_model = VGSLRecognitionModel(rec_train_config)

        # allow frontend feedback for per-collection training
        room_name = 'collection' if collection_pk else 'document'
        room_pk = collection_pk if collection_pk else document.pk
        trainer = KrakenTrainer(accelerator=accelerator,
                                devices=device,
                                precision=AMP_MODE,
                                enable_summary=False,
                                enable_progress_bar=False,
                                val_check_interval=1.0,
                                callbacks=[FrontendFeedback(model, model_dir, room_pk, room_name=room_name)])

        trainer.fit(kraken_model, rec_dm)

    # best checkpoint path from lightning's ModelCheckpoint callback
    best_path = getattr(getattr(trainer, 'checkpoint_callback', None), 'best_model_path', None)
    best_score = getattr(getattr(trainer, 'checkpoint_callback', None), 'best_model_score', None)

    if not best_path:
        logger.info(f'Model {os.path.split(model.file.path)[0]} did not improve.')
        raise DidNotConverge
    else:
        best_score_val = float(best_score) if best_score is not None else 0.0
        logger.info(f'Converting best model {best_path} (accuracy: {best_score_val}) to {model.file.path}.')
        convert_models([best_path], model.file.path)
        model.training_accuracy = best_score_val


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def train(transcription_pk=None, model_pk=None, task_group_pk=None,
          part_pks=None, user_pk=None, **kwargs):
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
    except DidNotConverge:
        send_event('document', document.pk, "training:error", {
            "id": model.pk,
        })
        user.notify(_("The model did not converge, probably because of lack of data."),
                    id="training-warning", level='warning')
        model.delete()

    except Exception as e:
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
def forced_align(instance_pk=None, model_pk=None, transcription_pk=None,
                 part_pk=None, user_pk=None, **kwargs):

    from PIL import Image as PILImage

    OcrModel = apps.get_model('core', 'OcrModel')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    Transcription = apps.get_model('core', 'Transcription')
    LineTranscription = apps.get_model('core', 'LineTranscription')

    ocrmodel = OcrModel.objects.get(pk=model_pk)
    aligner = ForcedAlignmentTaskModel.load_model(ocrmodel.file.path)
    transcription = Transcription.objects.get(pk=transcription_pk)

    part = DocumentPart.objects.get(pk=instance_pk)
    document = part.document

    text_direction = (
        (document.main_script and document.main_script.text_direction)
        or "horizontal-lr"
    )

    linetrans = LineTranscription.objects.filter(
        line__document_part=part,
        transcription=transcription
    ).select_related('line')

    with PILImage.open(part.image.path) as im:
        align_config = RecognitionInferenceConfig(accelerator='cpu', num_line_workers=0)
        for lt in linetrans:
            tag_name = lt.line.typology.name if lt.line.typology else 'default'
            bll = BaselineLine(
                id=str(lt.line.pk),
                baseline=lt.line.baseline,
                boundary=lt.line.mask,
                text=lt.content,
                tags={'type': [{'type': tag_name}]},
                language=None,
            )
            seg = Segmentation(
                lines=[bll],
                imagename='/dummy.png',
                type='baselines',
                text_direction=text_direction,
                script_detection=False,
                language=None,
            )
            aligned_segmentation = aligner.predict(im, seg, align_config)
            for pred in aligned_segmentation.lines:
                # lt.content = pred.prediction
                if text_direction == 'horizontal-rl' or text_direction == 'vertical-rl':
                    reorder = 'R'
                else:
                    reorder = 'L'
                pred = pred.logical_order(reorder)
                lt.graphs = [{
                    'c': letter,
                    'poly': poly,
                    'confidence': float(confidence)
                } for letter, poly, confidence in zip(
                    pred.prediction, pred.cuts, pred.confidences)]
                lt.save()


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def align(
    task,
    document_pk=None,
    part_pks=[],
    user_pk=None,
    task_group_pk=None,
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
    gap=600,
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
            gap,
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
            reports = part.reports.filter(method="core.tasks.align")
            if reports.exists():
                reports.last().cancel(None)

        DocumentPart.objects.bulk_update(parts, ["workflow_state"])
        logger.exception(e)
        raise e
    else:
        if user:
            user.notify(_("Alignment done!"),
                        id="alignment-success",
                        level='success')


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def replace_line_transcriptions_text(
    task, mode, find_terms, replace_term, project_pk=None, document_pk=None, transcription_pk=None, part_pk=None, user_pk=None, **kwargs
):
    LineTranscription = apps.get_model('core', 'LineTranscription')

    # Get the associated TaskReport
    TaskReport = apps.get_model('reporting', 'TaskReport')
    try:
        report = TaskReport.objects.get(task_id=task.request.id)
    except TaskReport.MultipleObjectsReturned:
        report = TaskReport.objects.filter(task_id=task.request.id).order_by('-started_at').first()
    except TaskReport.DoesNotExist:
        report = None

    user = User.objects.get(pk=user_pk)
    user.notify(_('Your replacements are being applied...'), links=[{'text': 'Report', 'src': report.uri}], id='find-replace-running', level='info')

    # Find line transcriptions to update
    search_method = search_content_psql_word
    if mode == REGEX_SEARCH_MODE:
        search_method = search_content_psql_regex

    search_results = search_method(
        find_terms,
        user,
        'text-danger',
        project_id=project_pk,
        document_id=document_pk,
        transcription_id=transcription_pk,
        part_id=part_pk,
    )

    if mode == WORD_BY_WORD_SEARCH_MODE:
        find_terms = '|'.join(find_terms.split(' '))

    # Apply the replacement on the found line transcriptions
    total = search_results.count()
    errors = 0
    updated = []
    for result in search_results.iterator(chunk_size=5000):
        try:
            report.append(f'Applying the replacement on the transcription from the line {result.line}', logger_fct=logger.info)
            # Replace on the highlighted content and then remove the highlighting tags
            result.content = strip_tags(build_highlighted_replacement_psql(mode, find_terms, replace_term, result.highlighted_content))
        except Exception as e:
            errors += 1
            report.append(f'Failed to apply the replacement on the transcription from the line {result.line}: {e}', logger_fct=logger.error)
            continue

        updated.append(result)

        # Once we have 1000 line transcriptions to update, we do it and clear the list
        if len(updated) >= 1000:
            LineTranscription.objects.bulk_update(updated, fields=['content'])
            updated = []

    # We don't forget to update the remaining line transcriptions
    if updated:
        LineTranscription.objects.bulk_update(updated, fields=['content'])

    # Alert the user
    if total and errors == total:
        user.notify(_('All replacements failed'), links=[{'text': 'Report', 'src': report.uri}], id='find-replace-error', level='danger')
    elif errors:
        user.notify(_('Replacements applied with some errors'), links=[{'text': 'Report', 'src': report.uri}], id='find-replace-warning', level='warning')
    else:
        user.notify(_('Replacements applied!'), links=[{'text': 'Report', 'src': report.uri}], id='find-replace-success', level='success')


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def train_from_collection(collection_pk=None, model_pk=None, task_group_pk=None, user_pk=None, **kwargs):
    # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    # get models for celery
    VirtualCollectionItem = apps.get_model("core", "VirtualCollectionItem")
    LineTranscription = apps.get_model("core", "LineTranscription")
    OcrModel = apps.get_model("core", "OcrModel")
    from django.contrib.auth import get_user_model
    User = get_user_model()

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

    try:
        model = OcrModel.objects.get(pk=model_pk)
        model.training = True
        model.save()

        # start training on collection
        send_event(
            "collection",
            collection_pk,
            "training:start",
            {
                "id": model.pk,
            },
        )
        collection_items = VirtualCollectionItem.objects.filter(
            collection_id=collection_pk
        ).select_related("document_part", "transcription_layer")
        if not collection_items.exists():
            raise ValueError("Cannot train on an empty collection.")

        # ground truth: only lines from each part + transcription_layer pair in
        # the collection
        q_objects = Q()
        for item in collection_items:
            if item.transcription_layer_id:
                q_objects |= Q(
                    transcription_id=item.transcription_layer_id,
                    line__document_part_id=item.document_part_id,
                )
        qs = LineTranscription.objects.filter(q_objects).exclude(
            Q(content="") | Q(content=None)
        )

        # pass the queryset to kraken for training
        train_(
            qs=qs,
            document=None,
            transcription=None,
            model=model,
            user=user,
            collection_pk=collection_pk
        )
    except DidNotConverge:
        send_event(
            "collection", collection_pk, "training:error", {"id": model.pk}
        )
        if user:
            user.notify(
                _("The model did not converge, probably because of lack of data."),
                id="training-warning",
                level="warning",
            )
        model.delete()
    except Exception as e:
        send_event(
            "collection",
            collection_pk,
            "training:error",
            {
                "id": model_pk,
            },
        )
        if user:
            user.notify(
                _("Something went wrong during the training process!"),
                id="training-error",
                level="danger",
            )
        raise e
    else:
        model.file_size = model.file.size
        if user:
            user.notify(_("Training finished!"), id="training-success", level="success")
    finally:
        model.training = False
        model.save()
        send_event(
            "collection",
            collection_pk,
            "training:done",
            {
                "id": model.pk,
            },
        )


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def segtrain_from_collection(collection_pk=None, model_pk=None, task_group_pk=None, user_pk=None, **kwargs):
    # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    from django.contrib.auth import get_user_model
    User = get_user_model()

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

    VirtualCollectionItem = apps.get_model("core", "VirtualCollectionItem")
    Document = apps.get_model("core", "Document")
    DocumentPart = apps.get_model("core", "DocumentPart")
    OcrModel = apps.get_model("core", "OcrModel")

    model = OcrModel.objects.get(pk=model_pk)

    try:
        load = model.file.path
    except ValueError:  # model is empty
        load = getattr(settings, "SEGMENTATION_DEFAULT_MODEL", "")
        model.file = model.file.field.upload_to(model, slugify(model.name) + ".mlmodel")

    model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    try:
        model.training = True
        model.save()

        send_event(
            "collection",
            collection_pk,
            "training:start",
            {
                "id": model.pk,
            },
        )

        # get ground truth parts for training
        part_pks = VirtualCollectionItem.objects.filter(
            collection_id=collection_pk
        ).values_list("document_part_id", flat=True)
        qs = DocumentPart.objects.filter(pk__in=part_pks).prefetch_related("lines")
        ground_truth = list(qs)

        if not ground_truth:
            raise ValueError("No document parts found in the collection.")

        # determine line_offset setting based on the first document in the collection
        first_doc = ground_truth[0].document
        offset = getattr(first_doc, "line_offset", Document.LINE_OFFSET_BASELINE)
        if offset == Document.LINE_OFFSET_TOPLINE:
            topline = True
        elif offset == Document.LINE_OFFSET_CENTERLINE:
            topline = None
        else:
            topline = False

        # shuffle ground truth lines
        np.random.default_rng(241960353267317949653744176059648850006).shuffle(
            ground_truth
        )
        partition = max(1, int(len(ground_truth) / 10))

        training_data = make_segmentation_training_data(qs[partition:])
        evaluation_data = make_segmentation_training_data(qs[:partition])

        accelerator, device = _to_ptl_device(
            getattr(settings, "KRAKEN_TRAINING_DEVICE", "cpu")
        )
        LOAD_THREADS = getattr(settings, "KRAKEN_TRAINING_LOAD_THREADS", 0)
        AMP_MODE = getattr(settings, "KRAKEN_TRAINING_PRECISION", "32")

        kraken_model = SegmentationModel(
            getattr(settings, "SEGMENTATION_HYPER_PARAMS", {}),
            output=os.path.join(model_dir, "version"),
            model=load,
            format_type=None,
            training_data=training_data,
            evaluation_data=evaluation_data,
            partition=partition,
            num_workers=LOAD_THREADS,
            load_hyper_parameters=True,
            resize="both",
            topline=topline,
        )

        trainer = KrakenTrainer(
            accelerator=accelerator,
            devices=device,
            precision=AMP_MODE,
            enable_summary=False,
            enable_progress_bar=False,
            val_check_interval=1.0,
            callbacks=[FrontendFeedback(model, model_dir, collection_pk, "collection")],
        )

        trainer.fit(kraken_model)

        if kraken_model.best_epoch == -1:
            logger.info(f"Model {os.path.split(model.file.path)[0]} did not improve.")
            raise DidNotConverge

        best_version = os.path.join(model_dir, kraken_model.best_model)

        try:
            logger.info(f"Moving best model {best_version} (accuracy: {kraken_model.best_metric}) to {model.file.path}.")
            shutil.copy(best_version, model.file.path)
            model.training_accuracy = kraken_model.best_metric
        except FileNotFoundError:
            user.notify(
                _("Training didn't get better results than base model!"),
                id="seg-no-gain-error",
                level="warning",
            )
            shutil.copy(load, model.file.path)
    except DidNotConverge:
        send_event(
            "collection", collection_pk, "training:error", {"id": model.pk}
        )
        if user:
            user.notify(
                _("The model did not converge, probably because of lack of data."),
                id="training-warning",
                level="warning",
            )
        model.delete()
    except Exception as e:
        send_event(
            "collection",
            collection_pk,
            "training:error",
            {
                "id": model.pk,
            },
        )
        if user:
            user.notify(
                _("Something went wrong during the segmenter training process!"),
                id="training-error",
                level="danger",
            )
        raise e
    else:
        model.file_size = model.file.size
        if user:
            user.notify(_("Training finished!"), id="training-success", level="success")
    finally:
        model.training = False
        model.save()
        send_event(
            "collection",
            collection_pk,
            "training:done",
            {
                "id": model.pk,
            },
        )
