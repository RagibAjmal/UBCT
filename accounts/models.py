from django.db import models
from django.contrib.auth.models import AbstractUser

class UBCTUser(AbstractUser):
    ROLE_CHOICES = [
        ('REQUESTER', 'Requester'),
        ('APPROVER', 'Approver / Trustee'),
        ('ADMIN', 'Administrator'),
        ('VIEWER', 'Report Viewer (Auditor)'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='REQUESTER')
    can_approve_requests = models.BooleanField(default=False, help_text="Can this user vote to approve grants?")
    can_manage_fund_transfers = models.BooleanField(
        default=False,
        help_text="Can this user record fund transfers and complete approved requests?",
    )
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"