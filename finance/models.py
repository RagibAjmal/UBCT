from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from grants.models import Request
from simple_history.models import HistoricalRecords

class Classification(models.Model):
    name = models.CharField(max_length=100, help_text="e.g., Education, Medical, General Corpus")
    prefix = models.CharField(max_length=10, blank=True, null=True, help_text="e.g., MED for Medical")

    def __str__(self):
        return self.name

class Donation(models.Model):
    donor_name = models.CharField(max_length=255)
    donor_pan = models.CharField(max_length=10, null=True, blank=True, help_text="Required for 10BD filing")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_date = models.DateField()
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True)
    transaction_reference = models.CharField(max_length=100, help_text="Bank reference / UTR")
    is_tax_exempt = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.donor_name} - ₹{self.amount} ({self.receipt_date})"

    history = HistoricalRecords()

class FundTransfer(models.Model):
    request = models.ForeignKey(Request, on_delete=models.PROTECT, help_text="Links to the approved voucher")
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    transfer_date = models.DateField()
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True)
    transaction_reference = models.CharField(max_length=100, help_text="e.g., IndusInd UTR number")

    def __str__(self):
        return f"Transfer for {self.request.request_id} - ₹{self.amount}"
    
class FundTransferDocument(models.Model):
    TAG_CHOICES = [
        ("RECEIPT", "Receipt"),
        ("BANK_CONFIRMATION", "Bank Confirmation"),
        ("TRANSACTION_PROOF", "Transaction Proof"),
        ("OTHER", "Other"),
    ]

    transfer = models.ForeignKey(
        FundTransfer,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    file = models.FileField(upload_to="fund_transfer_documents/%Y/%m/")
    tag = models.CharField(
        max_length=30,
        choices=TAG_CHOICES,
        blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for transfer {self.transfer_id}"
