from os import listdir, stat
from os.path import isfile, join, relpath

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    TemplateView,
    UpdateView,
)
from rest_framework.authtoken.models import Token

from users.forms import (
    BulkInvitationForm,
    ContactUsForm,
    GroupForm,
    GroupInvitationForm,
    InvitationAcceptForm,
    InvitationForm,
    ProfileForm,
    RegenerateApiTokenForm,
    RemoveUserFromGroup,
    TransferGroupOwnershipForm,
)
from users.models import ContactUs, Invitation, User


class SendInvitation(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Note: Email is sent on instance save()
    """
    model = Invitation
    template_name = 'users/invitation_form.html'
    form_class = InvitationForm
    success_message = _("Invitation sent successfully!")

    def get_form(self):
        form_class = self.get_form_class()
        return form_class(request=self.request, **self.get_form_kwargs())

    def get_success_url(self):
        return reverse('home')


class BulkInviteView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = 'users/bulk_invitation_form.html'
    form_class = BulkInvitationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('users.can_invite'):
            raise PermissionDenied(_("You do not have permission to invite users."))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        count, invalid = form.process_invitations()
        msg = _("Successfully sent %(count)d invitations.") % {'count': count}
        if invalid:
            msg += " " + _("Skipped invalid: %(emails)s") % {
                'emails': ", ".join(invalid)
            }
            messages.warning(self.request, msg)
        else:
            messages.success(self.request, msg)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('home')


class AcceptInvitation(CreateView):
    model = User
    template_name = 'users/invitation_accept_register.html'
    form_class = InvitationAcceptForm
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
        context = super().get_context_data(**kwargs)
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

    def get_success_url(self):
        return reverse('login')

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


class InviteView(LoginRequiredMixin, SuccessMessageMixin, TemplateView):
    template_name = 'users/invitation_form.html'

    def _default_mode(self):
        path = self.request.path.rstrip('/')
        return 'bulk' if path.endswith('/bulk') else 'single'

    def get_mode(self):
        return self.request.GET.get('mode') or self._default_mode()

    def get_context_data(self, **kwargs):
        from .forms import BulkInvitationForm, InvitationForm
        ctx = super().get_context_data(**kwargs)
        mode = kwargs.get('active_mode') or self.get_mode()
        ctx['active_mode'] = mode
        if mode == 'bulk':
            form = kwargs.get('form') or BulkInvitationForm(request=self.request)
        else:
            form = kwargs.get('form') or InvitationForm(request=self.request)
        ctx['form'] = form
        return ctx

    def post(self, request, *args, **kwargs):
        from .forms import BulkInvitationForm, InvitationForm
        mode = request.POST.get('mode') or self._default_mode()

        if mode == 'bulk':
            bulk_form = BulkInvitationForm(request.POST, request.FILES, request=request)
            if bulk_form.is_valid():
                count, invalid = bulk_form.process_invitations()
                msg = _("Successfully sent %(count)d invitations.") % {'count': count}
                if invalid:
                    msg += " " + _("Skipped invalid: %(emails)s") % {'emails': ", ".join(invalid)}
                    messages.warning(request, msg)
                else:
                    messages.success(request, msg)
                return HttpResponseRedirect(request.get_full_path())
            return self.render_to_response(self.get_context_data(active_mode='bulk', form=bulk_form))

        # single user invitation
        single_form = InvitationForm(request.POST, request=request)
        if single_form.is_valid():
            invitation = single_form.save()
            messages.success(
                request,
                _("Invitation sent to %(email)s.") % {'email': invitation.recipient_email}
            )
            return HttpResponseRedirect(request.get_full_path())
        return self.render_to_response(self.get_context_data(active_mode='single', form=single_form))


class AcceptGroupInvitation(LoginRequiredMixin, DetailView):
    model = Invitation
    slug_field = 'token'

    def get_success_message(self):
        return _("You are now a member of Team {team_name}!").format(
            team_name=self.object.group.name)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        valid = self.object.accept(self.request.user)
        if not valid:
            raise Http404("Invitation is not valid.")
        messages.success(self.request, self.get_success_message())
        return HttpResponseRedirect(reverse('profile-team-list'))


class GroupOwnerMixin():
    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if obj.groupowner.owner != self.request.user:
            raise PermissionDenied()  # or Http404
        return obj

    def get_success_url(self):
        return reverse('team-detail', kwargs={'pk': self.get_object().pk})


class RemoveFromGroup(GroupOwnerMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Group
    form_class = RemoveUserFromGroup

    def get_success_message(self, data):
        return _('User {user} successfully removed from the team {team_name}.').format(
            user=data.get('user'),
            team_name=self.get_object())

    def form_invalid(self, forms):
        return reverse('team-detail', kwargs={'pk': self.get_object().pk})


class LeaveGroup(LoginRequiredMixin, SuccessMessageMixin, DetailView):
    model = Group

    def get_success_message(self, data):
        return _('You successfully left {team}.').format(team=self.object)

    def get_success_url(self):
        return reverse('profile-team-list')

    def post(self, request, **kwargs):
        self.get_object().user_set.remove(request.user)
        return HttpResponseRedirect(reverse('profile-team-list'))


class TransferGroupOwnership(GroupOwnerMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Group
    form_class = TransferGroupOwnershipForm

    def get_success_url(self):
        return reverse('profile-team-list')

    def get_success_message(self, data):
        return _('Successfully transferred ownership to {user}.').format(
            user=data.get('user'))

    def form_invalid(self, forms):
        return reverse('team-detail', kwargs={'pk': self.get_object().pk})


class ProfileInfos(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = ProfileForm
    success_message = _('Profile successfully saved.')
    template_name = 'users/profile.html'

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse('profile')


class ProfileApiKey(LoginRequiredMixin, FormView):
    template_name = 'users/profile_api_key.html'
    form_class = RegenerateApiTokenForm

    def get_success_url(self):
        return reverse('profile-api-key')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['api_auth_token'], created = Token.objects.get_or_create(user=self.request.user)
        return context


class ProfileFiles(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile_files.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # files directory
        upath = self.request.user.get_document_store_path() + '/'
        files = listdir(upath)
        files.sort(key=lambda x: stat(join(upath, x)).st_mtime)
        files.reverse()
        files = [(relpath(join(upath, f), settings.MEDIA_ROOT), f)
                 for f in files
                 if isfile(join(upath, f))]
        paginator = Paginator(files, 25)  # Show 25 files per page.
        page_number = self.request.GET.get('page')
        context['is_paginated'] = paginator.count != 0
        context['page_obj'] = paginator.get_page(page_number)

        return context


class ProfileInvitations(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile_invitations.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        invites = self.request.user.invitations_sent.all()
        paginator = Paginator(invites, 25)
        context['is_paginated'] = paginator.count != 0
        page_number = self.request.GET.get('page')
        context['page_obj'] = paginator.get_page(page_number)
        return context


class ProfileGroupListCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Create new groups and list them
    """
    model = Group
    success_message = _('Team successfully created.')
    template_name = 'users/profile_group_list.html'
    form_class = GroupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invitations'] = Invitation.objects.filter(
            recipient=self.request.user,
            workflow_state__lt=Invitation.STATE_ACCEPTED)
        return context

    def get_success_url(self):
        return reverse('profile-team-list')


class GroupDetail(GroupOwnerMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Group
    form_class = GroupInvitationForm
    success_message = _('User successfully invited to the team.')
    template_name = 'users/group_detail_invite.html'

    def get_form_kwargs(self):
        # passing instance=None, as the instance would be a group instead of an Invitation
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'instance': None,
            'request': self.request})
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['other_users'] = self.object.user_set.exclude(pk=self.request.user.pk)
        return context


class ContactUsView(SuccessMessageMixin, CreateView):
    model = ContactUs
    form_class = ContactUsForm
    success_message = _('Message successfully sent.')
    template_name = 'users/contactus.html'

    def get_success_url(self):
        return reverse('contactus')
