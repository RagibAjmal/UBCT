from django.db import models
from django.conf import settings
import datetime
from .validators import validate_request_upload

class Beneficiary(models.Model):
    full_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    address = models.TextField()
    identity_document = models.FileField(
        upload_to='kyc_docs/',
        null=True,
        blank=True,
        validators=[validate_request_upload],
    )
    bank_account_details = models.TextField(help_text="Bank, Branch, Account No, IFSC")

    def __str__(self):
        return self.full_name

class Request(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        DOCUMENTS_REQUIRED = 'DOCUMENTS_REQUIRED', 'Documents Required'
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'

    TAX_STATUS_CHOICES = [
        ('80G', '80G Eligible'),
        ('NON_EXEMPT', 'Non-Exempt'),
    ]
    request_id = models.CharField(max_length=50, unique=True, blank=True)
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    requested_for = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the person receiving the actual benefit")
    classification = models.ForeignKey('finance.Classification', on_delete=models.SET_NULL, null=True)
    reason_for_assistance = models.TextField()
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    tax_exemption_status = models.CharField(max_length=20, choices=TAX_STATUS_CHOICES, default='80G')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request_id} - {self.beneficiary.full_name}"

    def save(self, *args, **kwargs):
        if not self.request_id:
            # Fallback to "UBCT" if no prefix is set on the classification
            prefix = self.classification.prefix.upper() if self.classification and self.classification.prefix else "UBCT"
            
            # Get current date as DDMMYYYY (e.g., 21012026)
            date_str = datetime.date.today().strftime("%d%m%Y")
            base_id = f"{prefix}-{date_str}"
            
            # Find the latest request for this specific prefix and date
            last_request = Request.objects.filter(
                request_id__startswith=base_id
            ).order_by('-request_id').first()
            
            if last_request:
                # Extract the 001 part and increment it
                last_number = int(last_request.request_id.split('-')[-1])
                next_number = last_number + 1
            else:
                next_number = 1
                
            # Format the new ID, padding with zeros to 3 digits
            self.request_id = f"{base_id}-{next_number:03d}"
            
        super().save(*args, **kwargs)

class ApprovalSignOff(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    cryptographic_hash = models.CharField(max_length=64, help_text="SHA-256 hash of the request at approval time")

    def __str__(self):
        return f"Approved by {self.approver} on {self.timestamp.strftime('%Y-%m-%d')}"

class RequestDocument(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(
        upload_to='request_documents/%Y/%m/',
        validators=[validate_request_upload],
    )
    tag = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., Medical Bill, ID Proof, Quotation")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tag or 'Document'} for {self.request.id}"
