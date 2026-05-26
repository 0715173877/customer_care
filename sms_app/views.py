import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import SMSMessage, SMSAutoReply
from chatbot.engine import engine

logger = logging.getLogger(__name__)


@login_required
def sms_dashboard(request):
    """Dashboard view for SMS management."""
    recent_messages = SMSMessage.objects.all()[:20]
    context = {
        'recent_messages': recent_messages,
        'total_messages': SMSMessage.objects.count(),
        'inbound_count': SMSMessage.objects.filter(direction='inbound').count(),
        'outbound_count': SMSMessage.objects.filter(direction='outbound').count(),
        'automated_count': SMSMessage.objects.filter(is_automated=True).count(),
    }
    return render(request, 'sms_app/dashboard.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def inbound_sms_webhook(request):
    """
    Twilio webhook for incoming SMS messages.
    Processes the message using the chatbot engine and sends an auto-reply.
    Customized for Kalton Investment Money Transfer Services.
    """
    from_number = request.POST.get('From', '')
    to_number = request.POST.get('To', '')
    body = request.POST.get('Body', '')
    message_sid = request.POST.get('MessageSid', '')
    
    # Log the incoming message
    sms = SMSMessage.objects.create(
        message_sid=message_sid,
        from_number=from_number,
        to_number=to_number,
        body=body,
        direction='inbound',
        status='received',
    )
    
    # Check for keyword-based auto-replies first
    for keyword_reply in SMSAutoReply.objects.filter(is_active=True):
        if body.lower().startswith(keyword_reply.keyword.lower()):
            reply_text = keyword_reply.reply_text
            sms.auto_reply = reply_text
            sms.is_automated = True
            sms.save()
            
            # Send the auto-reply via Twilio (in production)
            # from twilio.rest import Client
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # client.messages.create(
            #     body=reply_text,
            #     from_=to_number,
            #     to=from_number
            # )
            
            # Log the outbound reply
            SMSMessage.objects.create(
                from_number=to_number,
                to_number=from_number,
                body=reply_text,
                direction='outbound',
                status='sent',
                is_automated=True,
            )
            
            twiml_response = '<?xml version="1.0" encoding="UTF-8"?>'
            twiml_response += '<Response>'
            twiml_response += f'<Message>{reply_text}</Message>'
            twiml_response += '</Response>'
            
            return HttpResponse(twiml_response, content_type='text/xml')
    
    # Use chatbot engine for intelligent response
    bot_response = engine.generate_response(body, session_id=from_number)
    reply_text = bot_response['response']
    intent = bot_response['intent']
    
    # Update the SMS record
    sms.intent_detected = intent
    sms.auto_reply = reply_text
    sms.is_automated = True
    sms.save()
    
    # Log the outbound reply
    SMSMessage.objects.create(
        from_number=to_number,
        to_number=from_number,
        body=reply_text,
        direction='outbound',
        status='sent',
        is_automated=True,
        intent_detected=intent,
    )
    
    # Generate TwiML response
    twiml_response = '<?xml version="1.0" encoding="UTF-8"?>'
    twiml_response += '<Response>'
    twiml_response += f'<Message>{reply_text}</Message>'
    twiml_response += '</Response>'
    
    return HttpResponse(twiml_response, content_type='text/xml')


@csrf_exempt
@require_http_methods(["POST"])
def send_sms(request):
    """API endpoint to send an SMS message."""
    try:
        data = json.loads(request.body)
        to_number = data.get('to_number')
        message_body = data.get('body', '')
        
        if not to_number or not message_body:
            return JsonResponse({'status': 'error', 'message': 'to_number and body are required'}, status=400)
        
        # In production, send via Twilio:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=message_body,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=to_number
        # )
        
        sms = SMSMessage.objects.create(
            from_number=settings.TWILIO_PHONE_NUMBER,
            to_number=to_number,
            body=message_body,
            direction='outbound',
            status='sent',
            is_automated=True,
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'SMS sent',
            'sms_id': sms.pk,
        })
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def sms_status_callback(request):
    """Handle SMS status updates from Twilio."""
    message_sid = request.POST.get('MessageSid', '')
    message_status = request.POST.get('MessageStatus', '')
    
    status_map = {
        'queued': 'pending',
        'sent': 'sent',
        'delivered': 'delivered',
        'failed': 'failed',
        'undelivered': 'failed',
    }
    
    new_status = status_map.get(message_status, 'pending')
    
    SMSMessage.objects.filter(message_sid=message_sid).update(status=new_status)
    
    return HttpResponse(status=200)


def sms_logs_api(request):
    """API endpoint to get SMS logs."""
    messages = SMSMessage.objects.all()[:50]
    data = []
    for msg in messages:
        data.append({
            'id': msg.pk,
            'from': msg.from_number,
            'to': msg.to_number,
            'body': msg.body[:100],
            'direction': msg.direction,
            'status': msg.status,
            'intent': msg.intent_detected,
            'is_automated': msg.is_automated,
            'created_at': msg.created_at.isoformat(),
        })
    return JsonResponse({'messages': data})
