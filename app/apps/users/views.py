from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic.edit import CreateView


from users.models import User, Invitation
from users.forms import InvitationForm, InvitationAcceptForm


class SendInvitation(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Note: Email is sent on instance save()
    """
    model = Invitation
    template_name = 'users/invitation_form.html'
    form_class = InvitationForm
    success_url = '/'
    success_message = _("Invitation sent successfully!")

    def get_form(self):
        form_class = self.get_form_class()
        return form_class(request=self.request, **self.get_form_kwargs())


class AcceptInvitation(CreateView):
    model = User
    template_name = 'users/invitation_accept_register.html'
    form_class = InvitationAcceptForm
    success_url = '/login/'
    success_message = _("Successfully registered, you can now log in!")

    @cached_property
    def invitation(self):
        try:
            return (Invitation.objects
                    .filter(workflow_state__lte=Invitation.STATE_RECEIVED)
                    .get(token=self.kwargs['token']))
        except Invitation.DoesNotExist:
            raise Http404("No Invitation matches the given query.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['invitation'] = self.invitation
        return context

    def get_form(self):
        form = super().get_form()
        form.initial = {
            'email': self.invitation.recipient_email,
            'first_name': self.invitation.recipient_first_name,
            'last_name': self.invitation.recipient_last_name,
        }
        return form

    def get(self, *args, **kwargs):
        if self.invitation.workflow_state < Invitation.STATE_RECEIVED:
            self.invitation.workflow_state = Invitation.STATE_RECEIVED
            self.invitation.save()
        return super().get(*args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        self.invitation.accept(form.instance)
        # TODO: send a welcome message ?!
        return response

# request invitation
