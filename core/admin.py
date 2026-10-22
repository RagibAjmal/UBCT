from django.contrib import admin
from .models import SystemSetting
from unfold.admin import ModelAdmin

@admin.register(SystemSetting)
class SystemSettingAdmin(ModelAdmin):
    list_display = ('key', 'value') 
