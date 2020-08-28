from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext as _

from bootstrap.forms import BootstrapFormMixin
from users.models import Invitation, User, ContactUs


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
        invitation.save()
        invitation.send(self.request)
        return invitation


class InvitationAcceptForm(BootstrapFormMixin, UserCreationForm):
    """
    This is a registration form since a user is created.
    """

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
        fields = ('email', 'first_name', 'last_name')


class ContactUsForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = ContactUs
        fields = ('name','email','message')

