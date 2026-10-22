from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from import_export.fields import Field
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from simple_history.admin import SimpleHistoryAdmin
from .models import Classification, Donation, FundTransfer

# 1. Define the Resource Class First
class DonationResource(resources.ModelResource):
    # Mapped attribute to 'receipt_date' to match your model's actual field name
    receipt_date = Field(attribute='receipt_date', column_name='Date')
    transaction_reference = Field(attribute='transaction_reference', column_name='Ref No')
    amount = Field(attribute='amount', column_name='Deposit')

    class Meta:
        model = Donation
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('transaction_reference',) 

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not row.get('Deposit'):
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

# 2. Register Donation using a single, combined class
@admin.register(Donation)
class DonationAdmin(SimpleHistoryAdmin, ImportExportModelAdmin, ModelAdmin):
    resource_classes = [DonationResource]
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = ('id', 'amount', 'receipt_date', 'transaction_reference') 

# 3. Register remaining models
@admin.register(FundTransfer)
class FundTransferAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ('id', 'amount', 'transfer_date', 'transaction_reference')

@admin.register(Classification)
class ClassificationAdmin(ModelAdmin):
    list_display = ('name', 'prefix')