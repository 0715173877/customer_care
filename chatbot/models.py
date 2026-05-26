from django.db import models


class Conversation(models.Model):
    """Model for tracking chatbot conversations."""
    session_id = models.CharField(max_length=255, unique=True)
    user_identifier = models.CharField(max_length=100, blank=True, null=True, help_text="Phone number, email, or user ID")
    intent_history = models.JSONField(default=list, blank=True, help_text="List of intents detected in this conversation")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Conversation {self.session_id[:30]}... - {self.user_identifier or 'Anonymous'}"


class Message(models.Model):
    """Model for individual messages within a conversation."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role.title()}: {self.content[:50]}..."


class KnowledgeBase(models.Model):
    """Model for knowledge base entries that the chatbot can reference."""
    CATEGORY_CHOICES = [
        ('send_money', 'Sending Money'),
        ('receive_money', 'Receiving Money'),
        ('transfer_fees', 'Transfer Fees'),
        ('exchange_rates', 'Exchange Rates'),
        ('transfer_limits', 'Transfer Limits'),
        ('account_verification', 'Account Verification'),
        ('recipient_info', 'Recipient Information'),
        ('delivery_times', 'Delivery Times'),
        ('cancellations', 'Cancellations & Refunds'),
        ('security', 'Security & Fraud'),
        ('promotions', 'Promotions & Offers'),
        ('faq', 'General FAQ'),
    ]
    
    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='faq')
    keywords = models.CharField(max_length=500, blank=True, null=True, help_text="Comma-separated keywords for matching")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'question']
        verbose_name = 'Knowledge Base Entry'
        verbose_name_plural = 'Knowledge Base Entries'
    
    def __str__(self):
        return f"[{self.get_category_display()}] {self.question[:60]}..."
