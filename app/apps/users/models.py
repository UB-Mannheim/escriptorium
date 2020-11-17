import os
import uuid
from datetime import datetime

from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext as _
from django.urls import reverse

from escriptorium.utils import send_email
from users.consumers import send_notification


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
        send_email(
            'users/email/invitation_subject.txt',
            'users/email/invitation_message.txt',
            'users/email/invitation_html.html',
            self.recipient_email,
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
        self.recipient = user
        self.workflow_state = self.STATE_ACCEPTED
        self.save()
        if self.group:
            user.groups.add(self.group)
        send_notification(self.sender.pk,
                          _('{username} accepted your invitation!').format(
                              username=self.recipient.username),
                          level='success')


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

    class Meta:
        verbose_name = "message"
        verbose_name_plural = "messages"

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
