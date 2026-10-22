from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Request, Beneficiary

@admin.register(Request)
class RequestAdmin(ModelAdmin):
    list_display = ('request_id', 'requester', 'beneficiary', 'status', 'requested_amount')
    list_filter = ('status', 'classification')

@admin.register(Beneficiary)
class BeneficiaryAdmin(ModelAdmin):
    list_display = ('full_name', 'contact_number')