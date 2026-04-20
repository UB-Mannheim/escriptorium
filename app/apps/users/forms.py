from email.utils import parseaddr

from bootstrap.forms import BootstrapFormMixin
from captcha.fields import CaptchaField
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from email.utils import parseaddr

from escriptorium.utils import send_email
from users.models import ContactUs, GroupOwner, Invitation, User


class InvitationForm(BootstrapFormMixin, forms.ModelForm):
    expiry_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text=_("Optional: set an expiry date for this user's account")
    )

    class Meta:
        model = Invitation
        fields = ['recipient_first_name',
                  'recipient_last_name',
                  'recipient_email',
                  'group', 'expiry_date']

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


class BulkInvitationForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(
        label=_("CSV file with emails"),
        help_text=_("Upload a CSV file with one email per line."),
        required=False,
    )
    emails = forms.CharField(
        label=_("Emails"),
        widget=forms.Textarea(attrs={'rows': 5}),
        help_text=_("Enter one email per line."),
        required=False,
    )
    group = forms.ModelChoiceField(
        label=_("Team"),
        queryset=Group.objects.none(),
        required=False,
    )
    expiry_date = forms.DateTimeField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date'}),
        help_text=_("Optional: set an expiry date for these accounts"),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.sender = self.request.user if self.request else None
        super().__init__(*args, **kwargs)
        if self.sender:
            self.fields['group'].queryset = self.sender.groups.all()

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        emails = cleaned_data.get('emails')

        if not file and not emails:
            raise forms.ValidationError(_("Please provide either a CSV file or enter emails directly."))

        return cleaned_data

    def process_invitations(self):
        emails = set()
        invalid_emails = []

        # emails from the file
        if self.cleaned_data.get('file'):
            uploaded_file = self.cleaned_data.get('file')
            for line in uploaded_file:
                email = line.decode('utf-8').strip()
                if email:
                    emails.add(email)

        # emails from the textarea input
        if self.cleaned_data.get('emails'):
            text_emails = self.cleaned_data.get('emails')
            for line in text_emails.splitlines():
                email = line.strip()
                if email:
                    emails.add(email)

        # process unique emails
        count = 0
        for email in emails:
            if self._create_invitation(email, self.cleaned_data.get('group'), self.cleaned_data.get('expiry_date')):
                count += 1
            else:
                invalid_emails.append(email)

        return count, invalid_emails

    def _create_invitation(self, name_addr, group, expiry_date):
        try:
            name, email = parseaddr(name_addr)
            validate_email(email)
            args = {}
            if name:
                parts = name.strip().split(' ', 1)
                if len(parts) < 2:
                    args['recipient_last_name'] = parts[0]
                else:
                    args['recipient_first_name'] = parts[0]
                    args['recipient_last_name'] = parts[1]
            args['recipient_email'] = email
            args['sender'] = self.sender
            args['group'] = group
            args['expiry_date'] = expiry_date
            invitation = Invitation(**args)
            invitation.save()
            invitation.send(self.request)
            return True
        except ValidationError:
            return False


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
        fields = ('email', 'first_name', 'last_name', 'legacy_mode',
                  'preferred_transcription_font', 'download_retention_days')


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
