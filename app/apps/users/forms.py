from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext as _
from captcha.fields import CaptchaField
from django.contrib.auth.models import Group, Permission

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


class TeamForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name','permissions',)

    def __init__(self,*args, **kwargs):
        # give permissions to adding add invite change delete view users
        super().__init__(*args, **kwargs)
        self.fields['permissions'].queryset = Permission.objects.filter(content_type__app_label="users")

class InvitationTeamForm(BootstrapFormMixin,forms.ModelForm):

    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        )

    class Meta:
        model = Group
        fields = ('user',)


class ContactUsForm(BootstrapFormMixin, forms.ModelForm):

    message = forms.CharField(label="Message : Please precise your institution or research center if applicable", widget=forms.Textarea(attrs={'placeholder':'Message : Please precise your institution or research center if applicable' }))
    captcha = CaptchaField()

    class Meta:
        model = ContactUs
        fields = ('name','email','message','captcha')

