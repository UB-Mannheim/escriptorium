from bootstrap.forms import BootstrapFormMixin
from captcha.fields import CaptchaField
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.db.models import Q
from django.utils.translation import gettext as _

from escriptorium.utils import send_email
from users.models import ContactUs, GroupOwner, Invitation, User


class InvitationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['recipient_first_name',
                  'recipient_last_name',
                  'recipient_email',
                  'group']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.sender = self.request.user
        super().__init__(*args, **kwargs)
        self.fields['group'].queryset = self.sender.groups

    def save(self, commit=True):
        invitation = super().save(commit=False)
        invitation.sender = self.sender
        if commit:
            invitation.save()
            invitation.send(self.request)
        return invitation


class GroupInvitationForm(InvitationForm):
    recipient_id = forms.CharField(label=_("Email or username."))

    class Meta:
        model = Invitation
        fields = ['recipient_id', 'group']

    def clean_recipient_id(self):
        # we don't throw an error on purpose to avoid fishing
        try:
            return User.objects.get(Q(email=self.data.get('recipient_id'))
                                    | Q(username=self.data.get('recipient_id')))
        except User.DoesNotExist:
            return None

    def clean(self):
        data = super().clean()
        return data

    def save(self, commit=True):
        recipient = self.cleaned_data['recipient_id']
        print('recipient', recipient)
        if recipient:
            invitation = super().save(commit=False)
            invitation.recipient = recipient
            if commit:
                invitation.save()
                invitation.send(self.request)
            return invitation


class InvitationAcceptForm(BootstrapFormMixin, UserCreationForm):
    """
    This is a registration form since a user is created.
    """
    username = forms.CharField(min_length=3)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email',
                  'username',
                  'first_name',
                  'last_name',
                  'password1',
                  'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = None
        self.fields['password1'].help_text = None


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'legacy_mode')


class GroupForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('request').user
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        group = super().save(commit=True)
        group.user_set.add(self.user)
        GroupOwner.objects.create(
            group=group,
            owner=self.user)
        return group


class RemoveUserFromGroup(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.all())

    class Meta:
        model = Group
        fields = ('user',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = self.instance.user_set.exclude(
            pk=self.instance.groupowner.owner.pk)

    def save(self, commit=True):
        self.instance.user_set.remove(self.cleaned_data['user'])


class TransferGroupOwnershipForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.all())

    class Meta:
        model = Group
        fields = ('user',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = self.instance.user_set.exclude(
            pk=self.instance.groupowner.owner.pk)

    def save(self, commit=True):
        self.instance.groupowner.owner = self.cleaned_data['user']
        self.instance.groupowner.save()


class ContactUsForm(BootstrapFormMixin, forms.ModelForm):
    message = forms.CharField(
        label=_("Message : Please precise your institution or research center if applicable"),
        widget=forms.Textarea)
    captcha = CaptchaField()

    class Meta:
        model = ContactUs
        fields = ('name', 'email', 'message', 'captcha')

    def save(self, commit=True):
        instance = super().save(commit=commit)

        context = {
            "sender_name": self.instance.name,
            "sender_email": self.instance.email,
            "message": self.instance.message,
        }

        send_email(
            'users/email/contactus_subject.txt',
            'users/email/contactus_message.txt',
            'users/email/contactus_html.html',
            [email for name, email in settings.ADMINS],
            context=context,
            result_interface=None
        )

        return instance


class RegenerateApiTokenForm(forms.Form):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        self.user.regenerate_api_token()
