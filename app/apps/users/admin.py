from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm


from users.models import User, ResearchField, Invitation



class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
    
    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])


class MyUserAdmin(UserAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('fields',)}),  # second fields refers to research fields
    )


class InvitationAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ('workflow_state', 'group')
    list_display = ('recipient_email', 'recipient_last_name', 'recipient_first_name', 'sender', 'workflow_state')
    readonly_fields = ('sender', 'recipient', 'token', 'created_at', 'sent_at', 'workflow_state')
    
    def save_model(self, request, obj, form, change):
        obj.sender = request.user
        super().save_model(request, obj, form, change)
        obj.send(request)  # send the email


admin.site.register(User, MyUserAdmin)
admin.site.register(ResearchField)
admin.site.register(Invitation, InvitationAdmin)
