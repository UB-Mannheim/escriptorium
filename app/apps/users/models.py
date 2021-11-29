import logging
import os
import uuid
from datetime import datetime, date, timedelta

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext as _
from django.urls import reverse

from escriptorium.utils import send_email
from users.consumers import send_notification

logger = logging.getLogger(__name__)
MEGABYTES_TO_BYTES = 1048576


class User(AbstractUser):
    email = models.EmailField(
        verbose_name=_('email address'),
        max_length=255,
        unique=True,
    )
    fields = models.ManyToManyField('ResearchField', blank=True)

    onboarding = models.BooleanField(
        _('Show onboarding'),
        default=True
    )

    # If not set, quotas will be calculated from instance quota settings, if set to 0, user is blocked
    # quota_disk_storage is to be defined in Mb
    quota_disk_storage = models.PositiveIntegerField(null=True, blank=True)
    # quota_cpu is to be defined in CPU-min (spread over a week)
    quota_cpu = models.PositiveIntegerField(null=True, blank=True)
    # quota_gpu is to be defined in GPU-min (spread over a week)
    quota_gpu = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        permissions = (('can_invite', 'Can invite users'),)

    def get_full_name(self):
        if self.first_name and self.last_name:
            return super().get_full_name()
        else:
            return self.username

    def notify(self, message, id=None, level='info', links=None):
        if id is None:
            id = hash(message)
        return send_notification(self.pk, message, id=id, level=level, links=links)

    def get_document_store_path(self):
        store_path = os.path.join(settings.MEDIA_ROOT, 'users', str(self.pk))
        if not os.path.isdir(store_path):
            os.makedirs(store_path)
        return store_path

    def calc_disk_usage(self):
        models_size = self.ocrmodel_set.aggregate(Sum('file_size'))['file_size__sum'] or 0
        images_size = self.document_set.aggregate(Sum('parts__image_file_size'))['parts__image_file_size__sum'] or 0
        return models_size + images_size

    def disk_storage_limit(self):
        if self.quota_disk_storage != None:
            return self.quota_disk_storage*MEGABYTES_TO_BYTES
        if settings.QUOTA_DISK_STORAGE != None:
            return settings.QUOTA_DISK_STORAGE*MEGABYTES_TO_BYTES
        return None

    def has_free_disk_storage(self):
        quota = self.disk_storage_limit()
        if quota != None:
            return quota > self.calc_disk_usage()
        return True   # Unlimited disk storage

    def calc_cpu_usage(self):
        return self.taskreport_set.filter(started_at__gte=date.today() - timedelta(days=7)).aggregate(Sum('cpu_cost'))['cpu_cost__sum'] or 0

    def cpu_minutes_limit(self):
        if self.quota_cpu != None:
            return self.quota_cpu
        if settings.QUOTA_CPU_MINUTES != None:
            return settings.QUOTA_CPU_MINUTES
        return None

    def has_free_cpu_minutes(self):
        quota = self.cpu_minutes_limit()
        if quota != None:
            return quota > self.calc_cpu_usage()
        return True   # Unlimited CPU usage

    def calc_gpu_usage(self):
        return self.taskreport_set.filter(started_at__gte=date.today() - timedelta(days=7)).aggregate(Sum('gpu_cost'))['gpu_cost__sum'] or 0

    def gpu_minutes_limit(self):
        if self.quota_gpu != None:
            return self.quota_gpu
        if settings.QUOTA_GPU_MINUTES != None:
            return settings.QUOTA_GPU_MINUTES
        return None

    def has_free_gpu_minutes(self):
        quota = self.gpu_minutes_limit()
        if quota != None:
            return quota > self.calc_gpu_usage()
        return True   # Unlimited GPU usage


class ResearchField(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Invitation(models.Model):
    """
    Represents an invitation to join the service, possibly in a given 'team' (Group)
    """
    STATE_ERROR = 0
    STATE_CREATED = 1
    STATE_SENT = 2
    STATE_RECEIVED = 4
    STATE_ACCEPTED = 8
    STATE_CHOICES = (
        (STATE_ERROR, _("Error")),
        (STATE_CREATED, _("Created")),
        (STATE_SENT, _("Sent")),
        (STATE_RECEIVED, _("Received")),
        (STATE_ACCEPTED, _("Accepted")),
    )

    sender = models.ForeignKey(User, on_delete=models.PROTECT,
                               related_name='invitations_sent', editable=False)
    recipient_first_name = models.CharField(max_length=256, null=True, blank=True)
    recipient_last_name = models.CharField(max_length=256, null=True, blank=True)
    recipient_email = models.EmailField()
    # once accepted we link the invitation to the created User
    recipient = models.ForeignKey(User, null=True, blank=True, editable=False,
                                  on_delete=models.SET_NULL,
                                  related_name='invitations_received')
    created_at = models.DateTimeField(auto_now_add=True, editable=False)  # instance creation date
    sent_at = models.DateTimeField(editable=False, null=True)  # email send date
    group = models.ForeignKey(Group, blank=True, null=True,
                              verbose_name=_("Team"),
                              on_delete=models.SET_NULL)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    workflow_state = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_CREATED,
                                              editable=False)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return '%s -> %s' % (self.sender, self.recipient_email)

    def send(self, request):
        if self.recipient and self.group:  # already exists in the system
            self.send_invitation_to_group(request)
        elif self.recipient_email:
            self.send_invitation_to_service(request)
        else:
            # shouldn't happen(?)
            pass

    def send_invitation_to_group(self, request):
        accept_url = request.build_absolute_uri(
            reverse("accept-group-invitation", kwargs={"slug": self.token.hex}))

        context = {
            "sender": self.sender.get_full_name() or self.sender.username,
            "recipient_first_name": self.recipient.first_name,
            "recipient_last_name": self.recipient.last_name,
            "recipient_email": self.recipient.email,
            "team": self.group.name,
            "accept_link": accept_url,
        }
        self.send_email((self.recipient.email,), context)

    def send_invitation_to_service(self, request):
        accept_url = request.build_absolute_uri(
            reverse("accept-invitation", kwargs={"token": self.token.hex}))
        context = {
            "sender": self.sender.get_full_name() or self.sender.username,
            "recipient_first_name": self.recipient_first_name,
            "recipient_last_name": self.recipient_last_name,
            "recipient_email": self.recipient_email,
            "team": self.group and self.group.name,
            "accept_link": accept_url,
        }
        self.send_email((self.recipient_email,), context)

    def send_email(self, to, context):
        send_email(
            'users/email/invitation_subject.txt',
            'users/email/invitation_message.txt',
            'users/email/invitation_html.html',
            to,
            context=context,
            result_interface=('users', 'Invitation', self.id))

    def email_sent(self):
        if self.workflow_state < self.STATE_SENT:
            self.workflow_state = self.STATE_SENT
            self.sent_at = datetime.now()
            self.save()

    def email_error(self):
        self.workflow_state = self.STATE_ERROR
        self.save()

    def accept(self, user):
        if self.recipient and self.recipient != user:
            return False
        self.recipient = user
        self.workflow_state = self.STATE_ACCEPTED
        self.save()
        if self.group:
            user.groups.add(self.group)
        send_notification(self.sender.pk,
                          _('{username} accepted your invitation!').format(
                              username=self.recipient.username),
                          level='success')
        return True


class ContactUs(models.Model):
    """
    Represents Contact Us form
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(
        verbose_name=_('email address'),
        max_length=255,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        verbose_name = "Contact message"
        verbose_name_plural = "Contact messages"

    def __str__(self):
        return "from {}({})".format(self.name, self.email)

    def save(self, *args, **kwargs):
        context = {
            "sender_name": self.name,
            "sender_email": self.email,
            "message": self.message,
        }

        send_email(
            'users/email/contactus_subject.txt',
            'users/email/contactus_message.txt',
            'users/email/contactus_html.html',
            settings.ADMINS,
            context=context,
            result_interface=None
        )
        super().save(*args, **kwargs)


class GroupOwner(models.Model):
    """
    Model for the team to share documents with
    the group owner is the first user
    """
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                              related_name='owned_groups')

    def __str__(self):
        return str(self.group)


class QuotaEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quota_events')
    # reached_disk_storage is to be defined in Mb
    reached_disk_storage = models.PositiveIntegerField(null=True, blank=True)
    reached_cpu = models.PositiveIntegerField(null=True, blank=True)
    reached_gpu = models.PositiveIntegerField(null=True, blank=True)
    sent = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def email_sent(self):
        self.sent = True
        self.save()

    def email_error(self):
        logger.info(f'Failed to send email to user {self.user.pk} to inform him that he reached one or more of his quotas')
