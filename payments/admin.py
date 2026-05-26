from django.contrib import admin
from .models import PaymentRequest


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'status', 'amount', 'currency',
        'sender_name', 'from_account', 'to_account',
        'parse_confidence', 'reviewed_by', 'authorized_by', 'created_at',
    ]
    list_filter = ['status', 'currency', 'from_account_type', 'to_account_type', 'created_at']
    search_fields = [
        'raw_sms', 'sender_name', 'from_account', 'to_account',
        'reference', 'memo',
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at',
        'reviewed_at', 'authorized_at',
    ]
    fieldsets = [
        ('Status', {
            'fields': ['status', 'parse_confidence', 'parse_notes'],
        }),
        ('Raw SMS', {
            'fields': ['raw_sms'],
        }),
        ('Parsed - Amount', {
            'fields': ['amount', 'currency'],
        }),
        ('Parsed - Sender', {
            'fields': ['sender_name', 'from_account', 'from_account_type', 'from_bank'],
        }),
        ('Parsed - Receiver', {
            'fields': ['receiver_name', 'to_account', 'to_account_type', 'to_bank'],
        }),
        ('Parsed - Reference', {
            'fields': ['reference', 'memo', 'transaction_date'],
        }),
        ('Stage 2: Review', {
            'fields': ['reviewed_by', 'reviewed_at', 'review_notes'],
        }),
        ('Stage 3: Authorization', {
            'fields': ['authorized_by', 'authorized_at', 'authorization_notes'],
        }),
        ('Audit', {
            'fields': ['ip_address', 'created_at', 'updated_at'],
        }),
    ]
