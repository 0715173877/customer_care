from django.contrib import admin
from .models import SMSMessage, SMSAutoReply


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ['from_number', 'to_number', 'direction', 'status', 'is_automated', 'intent_detected', 'created_at']
    list_filter = ['direction', 'status', 'is_automated', 'intent_detected', 'created_at']
    search_fields = ['from_number', 'to_number', 'body', 'intent_detected']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(SMSAutoReply)
class SMSAutoReplyAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'reply_text', 'is_active', 'created_at']
    list_filter = ['is_active']
    list_editable = ['is_active']
    search_fields = ['keyword', 'reply_text']
