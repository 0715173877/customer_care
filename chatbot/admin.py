from django.contrib import admin
from .models import Conversation, Message, KnowledgeBase


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user_identifier', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['session_id', 'user_identifier']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'intent', 'created_at', 'content_preview']
    list_filter = ['role', 'intent', 'created_at']
    search_fields = ['content']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    list_editable = ['is_active']
    search_fields = ['question', 'answer', 'keywords']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Question & Answer', {
            'fields': ('question', 'answer', 'category', 'keywords')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
