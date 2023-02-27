from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import ngettext

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
    list_display = UserAdmin.list_display + ('is_active', 'last_login', 'date_joined', 'quota_disk_storage', 'quota_cpu', 'quota_gpu')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('fields',)}),  # second fields refers to research fields
        ('Quotas management (if not defined, fallback to instance quotas)', {'fields': ('quota_disk_storage', 'quota_cpu', 'quota_gpu')}),
    )
    add_fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password1', 'password2')}
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
                    'group', 'sender', 'workflow_state')
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
