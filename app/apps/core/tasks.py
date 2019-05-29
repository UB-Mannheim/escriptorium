import json
import logging
import numpy as np
import os.path
import redis
import subprocess
import torch
from PIL import Image

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.db.models import F
from django.utils.text import slugify
from django.utils.translation import gettext as _

from celery import shared_task
from celery.signals import *
from easy_thumbnails.files import get_thumbnailer
from kraken import binarization, pageseg, rpred
from kraken.lib import vgsl, train as kraken_train, models as kraken_models
from kraken.lib.dataset import GroundTruthDataset, generate_input_transforms, compute_error
from kraken.lib.train import TrainScheduler, EarlyStopping, KrakenTrainer
from kraken.lib.exceptions import KrakenStopTrainingException
from torch.utils.data import DataLoader

from users.consumers import send_event


logger = logging.getLogger(__name__)
User = get_user_model()
redis_ = redis.Redis(host=settings.REDIS_HOST,
                     port=settings.REDIS_PORT,
                     db=getattr(settings, 'REDIS_DB', 0))


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


@shared_task
def generate_part_thumbnails(instance_pk):
    if not getattr(settings, 'THUMBNAIL_ENABLE', True):
        return 
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        raise
    
    aliases = {}
    thbnr = get_thumbnailer(part.image)
    for alias, config in settings.THUMBNAIL_ALIASES[''].items():
        aliases[alias] = thbnr.get_thumbnail(config).url
    return aliases


@shared_task
def convert(instance_pk, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to convert innexistant DocumentPart : %d', instance_pk)
        raise
    part.convert()

    
@shared_task
def lossless_compression(instance_pk, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        raise
    part.compress()


@shared_task
def binarize(instance_pk, user_pk=None, binarizer=None, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to binarize innexistant DocumentPart : %d', instance_pk)
        raise
    
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    try:
        part.binarize()
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the binarization!"),
                        id="binarization-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_CREATED
        part.save()
        raise e
    else:
        if user:
            user.notify(_("Binarization done!"),
                        id="binarization-success", level='success')


@shared_task
def segment(instance_pk, user_pk=None, steps=None, text_direction=None, **kwargs):
    """
    steps can be either 'regions', 'lines' or 'both'
    """
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist as e:
        logger.error('Trying to segment innexistant DocumentPart : %d', instance_pk)
        raise e

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    try:
        part.segment(steps=steps, text_direction=text_direction)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the segmentation!"),
                        id="segmentation-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_BINARIZED
        part.save()
        raise e
    else:
        if user:
            user.notify(_("Segmentation done!"),
                        id="segmentation-success", level='success')


def add_data_to_training_set(data, target_set):
    # reorder the lines inside the set to make sure we only open the image once
    data.sort(key=lambda e: e['image'])
    im = None;
    for lt in data:
        if lt['image'] != im:
            if im:
                logger.debug('Closing', im)
                im.close()  # close previous image
            im = Image.open(os.path.join(settings.MEDIA_ROOT, lt['image']))
            logger.debug('Opened', im)
        if lt['content']:
            target_set.add_loaded(im.crop(lt['box']), lt['content'])
    im.close()



def train_(part_pks, transcription_pk, model_pk=None, model_name=None, user=None):
    DEVICE = getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu')
    LAG = 5
    Line = apps.get_model('core', 'Line')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    Transcription = apps.get_model('core', 'Transcription')
    LineTranscription = apps.get_model('core', 'LineTranscription')
    OcrModel = apps.get_model('core', 'OcrModel')
    
    transcription = Transcription.objects.get(pk=transcription_pk)
    document = transcription.document
    
    send_event('document', document.pk, "training:start", {})
    
    # [1,48,0,1 Cr3,3,32 Do0.1,2 Mp2,2 Cr3,3,64 Do0.1,2 Mp2,2 S1(1x12)1,3 Lbx100 Do]
    # m = re.match(r'(\d+),(\d+),(\d+),(\d+)', blocks[0])
    # if not m:
    #     raise cick.BadOptionUsage('spec', 'Invalid input spec {}'.format(blocks[0]))
    # batch, height, width, channels, pad
    transforms = generate_input_transforms(1, 48, 0, 1, 16)
    qs = (LineTranscription.objects
          .filter(transcription=transcription,
                  line__document_part__pk__in=part_pks)
          .exclude(content__isnull=True))
    
    # try to minimize what is loaded in memory for large datasets
    ground_truth = list(qs.values('content',
                                  box=F('line__box'),
                                  image=F('line__document_part__image')))
    # is it a good idea with a very large number of lines?
    np.random.shuffle(ground_truth)
    
    gt_set = GroundTruthDataset(normalization='NFD',  # ['NFD', 'NFKD', 'NFC', 'NFKC']
                                whitespace_normalization=True,
                                reorder=True,
                                im_transforms=transforms,
                                preload=False)
    val_set = GroundTruthDataset(normalization='NFD',
                                 whitespace_normalization=True,
                                 reorder=True,
                                 im_transforms=transforms,
                                 preload=True)
    partition = int(len(ground_truth) / 10)
    
    add_data_to_training_set(ground_truth[:partition], gt_set)
    gt_set.encode(None)  # codec
    train_loader = DataLoader(gt_set, batch_size=1, shuffle=True,
                              num_workers=0, pin_memory=True)
    
    add_data_to_training_set(ground_truth[partition:], val_set)
    
    logger.debug('Done loading training data')
    
    if model_pk:
        model = OcrModel.objects.get(pk=model_pk)
        nn = vgsl.TorchVGSLModel.load_model(model.file.path)
        upload_to = model.file.name
        fulldir = os.path.join(settings.MEDIA_ROOT, os.path.split(upload_to)[0], '')
    else:
        spec = '[1,48,0,1 Cr3,3,32 Do0.1,2 Mp2,2 Cr3,3,64 Do0.1,2 Mp2,2 S1(1x12)1,3 Lbx100 Do]'
        spec = '[{} O1c{}]'.format(spec[1:-1], gt_set.codec.max_label()+1)
        nn = vgsl.TorchVGSLModel(spec)
        nn.user_metadata['accuracy'] = []
        nn.init_weights()
        nn.add_codec(gt_set.codec)
        filename = slugify(model_name) + '.mlmodel'
        model = OcrModel.objects.create(name=filename,
                                        owner=user,
                                        document=document,
                                        script=document.main_script,
                                        version_author=user and user.username or 'unknown')
        upload_to = model.file.field.upload_to(model, filename)
        fulldir = os.path.join(settings.MEDIA_ROOT, os.path.split(upload_to)[0], '')
        if not os.path.exists(fulldir):
            os.mkdir(fulldir)
        modelpath = os.path.join(fulldir, filename)
        nn.save_model(path=modelpath)
        model.file = upload_to
    
    model.training = True
    model.save()
    
    val_set.training_set = list(zip(val_set._images, val_set._gt))
    # #nn.train()
    # # nn.set_num_threads(threads)
    # rec = models.TorchSeqRecognizer(nn, train=True, device=device)
    #optim = getattr(torch.optim, optimizer)(nn.nn.parameters(), lr=0)
    optim = torch.optim.Adam(nn.nn.parameters(), lr=1e-3)
    # tr_it = TrainScheduler(optim)
    # tr_it.add_phase(1, (2e-3, 2e-3), (0.9, 0.9), 0, train.annealing_const)
    st_it = EarlyStopping(None, int(len(gt_set) * LAG))
    temp_file_prefix = os.path.join(fulldir, 'version')
    trainer = KrakenTrainer(model=nn,
                            optimizer=optim,
                            device=DEVICE,
                            filename_prefix=temp_file_prefix,
                            event_frequency=1.0,
                            train_set=train_loader,
                            val_set=val_set,
                            stopper=st_it)
    
    def _progress(*args, **kwargs):
        logger.debug('progress', args, kwargs)
    
    def _print_eval(epoch=0, accuracy=0, chars=0, error=0):
        model.refresh_from_db()
        model.training_epoch = epoch
        model.training_accuracy = accuracy
        model.training_total = chars
        model.training_errors = error
        new_version_filename = '%s/version_%d.mlmodel' % (os.path.split(upload_to)[0], epoch)
        model.new_version(file=new_version_filename)
        model.save()
        send_event('document', document.pk, "training:eval", {
            "id": model.pk,
            "data": {
                'epoch': epoch,
                'accuracy': accuracy,
                'chars': chars,
                'error': error
            }})
    
    trainer.run(_print_eval, _progress)
    send_event('document', document.pk, "training:done", {
        "id": model.pk,
    })
    return model


@shared_task
def train(part_pks, transcription_pk, model_pk=None, model_name=None, user_pk=None):
    if not (model_pk or model_name):
        raise ValueError("tasks.train() was called without either a model_pk or a model_name.")
    
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    model = None
    try:
        model = train_(part_pks, transcription_pk, model_pk=model_pk, model_name=model_name, user=user)
    except Exception as e:
        raise e
        if user:
            user.notify(_("Something went wrong during the training process!"),
                        id="training-error", level='danger')
    else:
        if user:
            user.notify(_("Training finished!"),
                        id="training-success",
                        level='success')
    finally:
        if model:
            model.training = False
            model.save()


@shared_task
def transcribe(instance_pk, model_pk=None, user_pk=None, text_direction=None, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to transcribe innexistant DocumentPart : %d', instance_pk)
        raise
    
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    if model_pk:
        try:
            OcrModel = apps.get_model('core', 'OcrModel')
            model = OcrModel.objects.get(pk=model_pk)
        except OcrModel.DoesNotExist:
            # Not sure how we should deal with this case
            model = None
    else:
        model = None
    
    try:
        part.transcribe(model=model)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the transcription!"),
                        id="transcription-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_SEGMENTED
        part.save()
        raise
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
    if not sender.startswith('core.tasks') or sender.name.endswith('train'):
        return
    instance_id = body[0][0]
    data = json.loads(redis_.get('process-%d' % instance_id) or '{}')
    
    try:
        # protects against signal race condition
        if (data[sender]['task_id'] == sender.request.id and
            not check_signal_order(data[sender]['status'], signal_name)):
            return
    except KeyError:
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
    instance_id = sender.request.args[0]
    
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
        data = {k:v for k,v in data.items() if v['status'] != 'pending'}
    redis_.set('process-%d' % instance_id, json.dumps(data))

    if status == 'done':
        result = kwargs.get('result', None)
    else:
        result = None
    update_client_state(instance_id, sender.name, status, task_id=sender.request.id, data=result)
