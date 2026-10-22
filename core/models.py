from django.db import models

class SystemSetting(models.Model):
    key = models.CharField(max_length=50, unique=True, help_text="e.g., MIN_APPROVALS")
    value = models.CharField(max_length=255, help_text="e.g., 2")
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.key}: {self.value}"