from django.db import models


class CallLog(models.Model):
    """Model for tracking all calls (inbound/outbound)."""
    STATUS_CHOICES = [
        ('ringing', 'Ringing'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('failed', 'Failed'),
    ]
    DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    call_sid = models.CharField(max_length=255, unique=True, blank=True, null=True)
    caller_number = models.CharField(max_length=20)
    recipient_number = models.CharField(max_length=20)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ringing')
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    intent_detected = models.CharField(max_length=50, blank=True, null=True, help_text="Detected intent from chatbot engine")
    summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Call Log'
        verbose_name_plural = 'Call Logs'
    
    def __str__(self):
        return f"{self.direction.title()} call from {self.caller_number} [{self.status}]"


class CallMenuOption(models.Model):
    """Model for IVR menu options."""
    digit = models.CharField(max_length=2)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'IVR Menu Option'
        verbose_name_plural = 'IVR Menu Options'
    
    def __str__(self):
        return f"Press {self.digit}: {self.title}"
