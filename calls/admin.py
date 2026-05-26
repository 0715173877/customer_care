from django.contrib import admin
from .models import CallLog, CallMenuOption


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ['caller_number', 'direction', 'status', 'duration', 'intent_detected', 'created_at']
    list_filter = ['direction', 'status', 'intent_detected', 'created_at']
    search_fields = ['caller_number', 'recipient_number', 'call_sid', 'intent_detected']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(CallMenuOption)
class CallMenuOptionAdmin(admin.ModelAdmin):
    list_display = ['digit', 'title', 'is_active', 'order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'order']
    ordering = ['order']
