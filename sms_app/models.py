from django.db import models


class SMSMessage(models.Model):
    """Model for tracking all SMS messages."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    message_sid = models.CharField(max_length=255, unique=True, blank=True, null=True)
    from_number = models.CharField(max_length=20)
    to_number = models.CharField(max_length=20)
    body = models.TextField()
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_automated = models.BooleanField(default=False, help_text="Was this message handled automatically by the chatbot?")
    auto_reply = models.TextField(blank=True, null=True, help_text="The auto-reply sent by the chatbot")
    intent_detected = models.CharField(max_length=50, blank=True, null=True, help_text="Detected intent from chatbot engine")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SMS Message'
        verbose_name_plural = 'SMS Messages'
    
    def __str__(self):
        return f"{self.direction.title()} SMS: {self.from_number} -> {self.to_number} [{self.status}]"


class SMSAutoReply(models.Model):
    """Model for keyword-based SMS auto-replies."""
    keyword = models.CharField(max_length=50, unique=True, help_text="Keyword to trigger this auto-reply")
    reply_text = models.TextField(help_text="The auto-reply text to send")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['keyword']
        verbose_name = 'SMS Auto Reply'
        verbose_name_plural = 'SMS Auto Replies'
    
    def __str__(self):
        return f"Keyword '{self.keyword}' -> {self.reply_text[:50]}..."
