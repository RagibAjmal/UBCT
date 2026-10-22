import os
from pathlib import Path

PROJECT_FILES = {
    "requirements.txt": """Django>=5.0
django-import-export>=3.3.6
django-unfold>=0.22.0
django-allauth>=0.61.1
pillow>=10.0.0
""",
    "accounts/models.py": """from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('REQUESTER', 'Requester'),
        ('APPROVER', 'Approver / Trustee'),
        ('ADMIN', 'Administrator'),
        ('VIEWER', 'Report Viewer (Auditor)'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='REQUESTER')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
""",
    "grants/models.py": """from django.db import models
from django.conf import settings

class Beneficiary(models.fields.Model):
    full_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    address = models.TextField()
    identity_document = models.FileField(upload_to='kyc_docs/', null=True, blank=True)
    bank_account_details = models.TextField(help_text="Bank, Branch, Account No, IFSC")

    def __str__(self):
        return self.full_name

class Request(models.fields.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('TRANSFERRED', 'Funds Transferred'),
    ]
    TAX_STATUS_CHOICES = [
        ('80G', '80G Eligible'),
        ('NON_EXEMPT', 'Non-Exempt'),
    ]
    request_id = models.CharField(max_length=50, unique=True, help_text="e.g., UBCT-2026-0001")
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    classification = models.ForeignKey('finance.Classification', on_delete=models.SET_NULL, null=True)
    reason_for_assistance = models.TextField()
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    tax_exemption_status = models.CharField(max_length=20, choices=TAX_STATUS_CHOICES, default='80G')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request_id} - {self.beneficiary.full_name}"

class ApprovalSignOff(models.fields.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    cryptographic_hash = models.CharField(max_length=64, help_text="SHA-256 hash of the request at approval time")

    def __str__(self):
        return f"Approved by {self.approver} on {self.timestamp.strftime('%Y-%m-%d')}"
""",
    "grants/admin.py": """from django.contrib import admin
from .models import Beneficiary, Request

@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'contact_number')
    search_fields = ('full_name', 'contact_number')

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'beneficiary', 'classification', 'requested_amount', 'status', 'tax_exemption_status')
    list_filter = ('status', 'tax_exemption_status', 'classification')
    search_fields = ('request_id', 'beneficiary__full_name')
""",
    "finance/models.py": """from django.db import models
from grants.models import Request

class Classification(models.fields.Model):
    name = models.CharField(max_length=100, help_text="e.g., Education, Medical, General Corpus")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Donation(models.fields.Model):
    donor_name = models.CharField(max_length=255)
    donor_pan = models.CharField(max_length=10, null=True, blank=True, help_text="Required for 10BD filing")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_date = models.DateField()
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True)
    transaction_reference = models.CharField(max_length=100, help_text="Bank reference / UTR")
    is_tax_exempt = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.donor_name} - ₹{self.amount} ({self.receipt_date})"

class FundTransfer(models.fields.Model):
    request = models.ForeignKey(Request, on_delete=models.PROTECT, help_text="Links to the approved voucher")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transfer_date = models.DateField()
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True)
    transaction_reference = models.CharField(max_length=100, help_text="e.g., IndusInd UTR number")

    def __str__(self):
        return f"Transfer for {self.request.request_id} - ₹{self.amount}"
""",
    "finance/admin.py": """from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Classification, Donation, FundTransfer

@admin.register(Donation)
class DonationAdmin(ImportExportModelAdmin):
    list_display = ('donor_name', 'amount', 'receipt_date', 'transaction_reference', 'donor_pan', 'is_tax_exempt')
    list_filter = ('receipt_date', 'classification', 'is_tax_exempt')
    search_fields = ('donor_name', 'donor_pan', 'transaction_reference')

@admin.register(FundTransfer)
class FundTransferAdmin(ImportExportModelAdmin):
    list_display = ('request', 'amount', 'transfer_date', 'transaction_reference')
    list_filter = ('transfer_date', 'classification')
    search_fields = ('transaction_reference', 'request__request_id')

@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
"""
}

def create_project_structure():
    print("🚀 Initializing UBCT Django Project Structure...")
    for filepath, content in PROJECT_FILES.items():
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.name != "":
            (path.parent / "__init__.py").touch()
            
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Created {filepath}")
    print("\n🎉 Done! You can now start the Django project.")

if __name__ == "__main__":
    create_project_structure()