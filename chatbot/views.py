import json
import uuid
import logging
from django.db import models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from .engine import engine
from .models import Conversation, Message, KnowledgeBase

logger = logging.getLogger(__name__)


def dashboard(request):
    """Chatbot dashboard view."""
    recent_conversations = Conversation.objects.filter(is_active=True)[:10]
    context = {
        'recent_conversations': recent_conversations,
        'total_conversations': Conversation.objects.count(),
        'active_conversations': Conversation.objects.filter(is_active=True).count(),
        'knowledge_base_entries': KnowledgeBase.objects.filter(is_active=True).count(),
    }
    return render(request, 'chatbot/dashboard.html', context)


def widget(request):
    """Embeddable chatbot widget view."""
    return render(request, 'chatbot/widget.html')


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """
    Main chat API endpoint.
    Accepts a message and returns a bot response using the engine.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not message.strip():
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            session_id=session_id,
            defaults={'user_identifier': data.get('user_identifier', '')}
        )
        
        if not created and not conversation.is_active:
            conversation.is_active = True
            conversation.save()
        
        # Save user message
        Message.objects.create(
            conversation=conversation,
            role='user',
            content=message,
        )
        
        # Get bot response from engine
        bot_response = engine.get_response(message, session_id=session_id)
        
        # Save bot message
        Message.objects.create(
            conversation=conversation,
            role='bot',
            content=bot_response['response'],
            intent=bot_response['intent'],
        )
        
        # Update conversation with intent
        intents = conversation.intent_history or []
        intents.append(bot_response['intent'])
        conversation.intent_history = intents
        conversation.save()
        
        # Check knowledge base for additional info
        kb_entries = KnowledgeBase.objects.filter(
            is_active=True,
            category=bot_response['intent']
        )[:3]
        
        kb_data = []
        if kb_entries:
            for entry in kb_entries:
                kb_data.append({
                    'question': entry.question,
                    'answer': entry.answer,
                })
        
        return JsonResponse({
            'response': bot_response['response'],
            'intent': bot_response['intent'],
            'language': bot_response['language'],
            'action': bot_response.get('action'),
            'requires_info': bot_response.get('requires_info', False),
            'session_id': session_id,
            'knowledge_base': kb_data,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Chat API error: {e}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def reset_conversation(request):
    """Reset a conversation session."""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id', '')
        
        if not session_id:
            return JsonResponse({'error': 'session_id is required'}, status=400)
        
        # Reset engine context
        engine.reset_session(session_id)
        
        # Update database
        Conversation.objects.filter(session_id=session_id).update(is_active=False)
        
        return JsonResponse({'status': 'success', 'message': 'Conversation reset'})
    except Exception as e:
        logger.error(f"Reset conversation error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def conversation_history(request, session_id):
    """Get the full conversation history for a session."""
    try:
        conv = Conversation.objects.filter(session_id=session_id).first()
        if not conv:
            return JsonResponse({'error': 'Conversation not found'}, status=404)
        
        messages = conv.messages.all().values('role', 'content', 'intent', 'created_at')
        
        return JsonResponse({
            'session_id': session_id,
            'messages': list(messages),
            'created_at': conv.created_at,
            'is_active': conv.is_active,
        })
    except Exception as e:
        logger.error(f"Conversation history error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def knowledge_base_api(request):
    """API endpoint to search the knowledge base."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    entries = KnowledgeBase.objects.filter(is_active=True)
    
    if query:
        entries = entries.filter(
            models.Q(question__icontains=query) |
            models.Q(answer__icontains=query) |
            models.Q(keywords__icontains=query)
        )
    
    if category:
        entries = entries.filter(category=category)
    
    data = []
    for entry in entries[:20]:
        data.append({
            'id': entry.pk,
            'question': entry.question,
            'answer': entry.answer,
            'category': entry.category,
            'category_display': entry.get_category_display(),
        })
    
    return JsonResponse({'entries': data})


@csrf_exempt
@require_http_methods(["GET"])
def conversations_api(request):
    """API endpoint to get all conversations."""
    convs = Conversation.objects.all()[:20]
    data = []
    for conv in convs:
        data.append({
            'id': conv.pk,
            'session_id': conv.session_id[:30] + '...',
            'user_identifier': conv.user_identifier or 'Anonymous',
            'message_count': conv.messages.count(),
            'intents': conv.intent_history,
            'is_active': conv.is_active,
            'created_at': conv.created_at.isoformat(),
        })
    return JsonResponse({'conversations': data})
