from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
from .models import UBCTUser
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin

admin.site.unregister(EmailAddress) 
admin.site.unregister(SocialAccount)
admin.site.unregister(SocialToken)
admin.site.unregister(SocialApp)
admin.site.unregister(Group)

@admin.register(UBCTUser)
class UBCTUserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Permissions', {
            'fields': (
                'role',
                'can_approve_requests',
                'can_manage_fund_transfers',
            ),
        }),
    )

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass