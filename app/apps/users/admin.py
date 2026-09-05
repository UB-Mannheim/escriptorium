from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from users.forms import BulkInvitationForm
from users.models import (
    ContactUs,
    GroupOwner,
    Invitation,
    QuotaEvent,
    ResearchField,
    User,
)


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(UserCreationForm):
    email = forms.EmailField()
    expiry_date = forms.DateTimeField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date'}),
        help_text=_("Optional: Set the user's account expiry date")
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError('Duplicate username.')


class MyUserAdmin(UserAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm
    list_display = UserAdmin.list_display + ('is_active', 'last_login', 'date_joined', 'expiry_date', 'quota_disk_storage', 'quota_cpu', 'quota_gpu')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('fields', 'expiry_date')}),  # second fields refers to research fields
        ('Quotas management (if not defined, fallback to instance quotas)', {'fields': ('quota_disk_storage', 'quota_cpu', 'quota_gpu')}),
    )
    add_fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password1', 'password2', 'expiry_date')}
         ),
        ('Quotas management (if not defined, fallback to instance quotas)', {'fields': ('quota_disk_storage', 'quota_cpu', 'quota_gpu')}),
    )

    actions = ['disable']

    def disable(self, request, queryset):
        queryset.update(is_active=False)
        count = queryset.count()
        self.message_user(request, ngettext(
            '%d user disabled.',
            '%d users disabled.',
            count,
        ) % count, messages.SUCCESS)


class InvitationAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ('workflow_state', 'group')
    list_display = ('recipient_email_', 'recipient_last_name_', 'recipient_first_name_',
                    'group', 'sender', 'workflow_state', 'expiry_date')
    readonly_fields = ('sender', 'recipient', 'token', 'created_at', 'sent_at', 'workflow_state')
    search_fields = ('recipient_email', 'recipient__username',
                     'recipient_last_name', 'recipient_first_name',
                     'recipient__last_name', 'recipient__first_name')
    actions = ['resend']

    @admin.display(description='Recipient Email')
    def recipient_email_(self, obj):
        return obj.recipient.email if obj.recipient else obj.recipient_email

    @admin.display(description='Recipient last name')
    def recipient_last_name_(self, obj):
        return obj.recipient.last_name if obj.recipient else obj.recipient_last_name

    @admin.display(description='Recipient first name')
    def recipient_first_name_(self, obj):
        return obj.recipient.first_name if obj.recipient else obj.recipient_first_name

    def save_model(self, request, obj, form, change):
        obj.sender = request.user
        super().save_model(request, obj, form, change)
        obj.send(request)  # send the email

    def resend(self, request, queryset):
        for invit in queryset:
            invit.send(request)
        count = queryset.count()
        self.message_user(request, ngettext(
            '%d invitation was resent.',
            '%d invitations were resent.',
            count,
        ) % count, messages.SUCCESS)

    change_list_template = 'admin/users/invitation/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk_invite/',
                self.admin_site.admin_view(self.bulk_invite),
                name='users_invitation_bulk_invite',
            ),
        ]
        return custom_urls + urls

    def bulk_invite(self, request):
        if not request.user.has_perm('users.can_invite'):
            self.message_user(
                request,
                _("You do not have permission to send invitations."),
                level=messages.ERROR,
            )
            return redirect('..')

        if request.method == 'POST':
            form = BulkInvitationForm(request.POST, request.FILES, request=request)
            if form.is_valid():
                count, invalid_emails = form.process_invitations()
                message = _("Successfully sent {count} invitations.").format(count=count)
                if invalid_emails:
                    message += _(" The following emails were invalid and were skipped: {emails}").format(emails=", ".join(invalid_emails))
                    level = messages.WARNING
                else:
                    level = messages.SUCCESS
                self.message_user(
                    request,
                    message,
                    level=level,
                )
                return redirect('..')
        else:
            form = BulkInvitationForm(request=request)

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            opts=self.model._meta,
            title=_('Bulk Invite'),
            has_permission=True,
        )
        return TemplateResponse(
            request,
            'admin/users/invitation/bulk_invite.html',
            context,
        )

    # override changelist_view to pass bulk_invite_url to the template
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        # add the url for the bulk invite view to the context
        bulk_invite_url = 'bulk_invite/'
        extra_context['bulk_invite_url'] = bulk_invite_url
        return super().changelist_view(request, extra_context=extra_context)


class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'created_at')
    readonly_fields = ('created_at',)


class QuotaEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'reached_disk_storage', 'reached_cpu', 'reached_gpu', 'sent', 'created')
    ordering = ('-created',)

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(User, MyUserAdmin)
admin.site.register(ResearchField)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(ContactUs, ContactUsAdmin)
admin.site.register(QuotaEvent, QuotaEventAdmin)
admin.site.register(GroupOwner)
