import json
import logging
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import CallLog, CallMenuOption
from chatbot.engine import engine

logger = logging.getLogger(__name__)


@login_required
def call_dashboard(request):
    """Dashboard view for call management."""
    recent_calls = CallLog.objects.all()[:20]
    avg = CallLog.objects.filter(status='completed').aggregate(
        avg=models.Avg('duration')
    ).get('avg__duration', 0) or 0
    context = {
        'recent_calls': recent_calls,
        'total_calls': CallLog.objects.count(),
        'missed_calls': CallLog.objects.filter(status='missed').count(),
        'avg_duration': avg,
    }
    return render(request, 'calls/dashboard.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def inbound_call_webhook(request):
    """
    Twilio webhook for incoming calls.
    Returns TwiML (Twilio Markup Language) to handle the call flow.
    Customized for Kalton Investment Money Transfer Services.
    """
    caller = request.POST.get('From', '')
    called = request.POST.get('To', '')
    call_sid = request.POST.get('CallSid', '')
    
    CallLog.objects.create(
        call_sid=call_sid,
        caller_number=caller,
        recipient_number=called,
        direction='inbound',
        status='ringing',
    )
    
    menu_options = CallMenuOption.objects.filter(is_active=True)
    
    twiml_response = '<?xml version="1.0" encoding="UTF-8"?>'
    twiml_response += '<Response>'
    twiml_response += '<Gather numDigits="1" action="/calls/ivr-handler/" method="POST">'
    twiml_response += '<Say voice="alice">'
    twiml_response += 'Welcome to Kalton Investment Money Transfer Services. '
    twiml_response += 'You have reached our automated support system. '
    twiml_response += 'Please listen to the following options: '
    
    for option in menu_options:
        twiml_response += f'Press {option.digit} for {option.title}. '
    
    twiml_response += '</Say>'
    twiml_response += '</Gather>'
    twiml_response += '<Say voice="alice">We did not receive any input. Goodbye.</Say>'
    twiml_response += '</Response>'
    
    return HttpResponse(twiml_response, content_type='text/xml')


@csrf_exempt
@require_http_methods(["POST"])
def ivr_handler(request):
    """
    Handle IVR menu selections from callers.
    Uses the chatbot engine to process the request.
    Customized for Kalton Investment Money Transfer Services.
    """
    digits = request.POST.get('Digits', '')
    call_sid = request.POST.get('CallSid', '')
    
    digit_actions = {
        '1': 'send_money',
        '2': 'track_transfer',
        '3': 'exchange_rate',
        '4': 'transfer_fees',
        '5': 'transfer_limits',
        '6': 'account_verification',
        '7': 'hours_location',
        '0': 'speak_to_agent',
    }
    
    action = digit_actions.get(digits, 'unknown')
    
    CallLog.objects.filter(call_sid=call_sid).update(
        intent_detected=action,
        status='in_progress'
    )
    
    intent_map = {
        'send_money': 'send',
        'track_transfer': 'track',
        'exchange_rate': 'rate',
        'transfer_fees': 'fee',
        'transfer_limits': 'limit',
        'account_verification': 'verify',
        'hours_location': 'hours',
    }
    
    bot_response = engine.generate_response(
        intent_map.get(action, 'help'),
        session_id=call_sid
    )
    
    twiml_response = '<?xml version="1.0" encoding="UTF-8"?>'
    twiml_response += '<Response>'
    twiml_response += f'<Say voice="alice">{bot_response["response"]}</Say>'
    
    if action == '0' or action == 'speak_to_agent':
        twiml_response += '<Say voice="alice">Please hold while we connect you to a live agent.</Say>'
        twiml_response += '<Dial>' + settings.TWILIO_PHONE_NUMBER + '</Dial>'
    else:
        twiml_response += '<Gather numDigits="1" action="/calls/ivr-handler/" method="POST">'
        twiml_response += '<Say voice="alice">Press 9 to return to the main menu, or press 0 to speak to an agent.</Say>'
        twiml_response += '</Gather>'
    
    twiml_response += '</Response>'
    
    return HttpResponse(twiml_response, content_type='text/xml')


@csrf_exempt
@require_http_methods(["POST"])
def call_status_callback(request):
    """Handle call status updates from Twilio."""
    call_sid = request.POST.get('CallSid', '')
    call_status = request.POST.get('CallStatus', '')
    duration = request.POST.get('CallDuration', '0')
    
    status_map = {
        'completed': 'completed',
        'busy': 'failed',
        'no-answer': 'missed',
        'canceled': 'failed',
        'failed': 'failed',
        'in-progress': 'in_progress',
        'ringing': 'ringing',
    }
    
    new_status = status_map.get(call_status, 'completed')
    
    CallLog.objects.filter(call_sid=call_sid).update(
        status=new_status,
        duration=int(duration) if duration.isdigit() else 0,
    )
    
    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def outbound_call(request):
    """
    Initiate an outbound call via Twilio.
    """
    try:
        data = json.loads(request.body)
        to_number = data.get('to_number')
        message = data.get('message', 'Hello, this is an automated message from Kalton Investment Money Transfer Services.')
        
        call_log = CallLog.objects.create(
            caller_number=settings.TWILIO_PHONE_NUMBER,
            recipient_number=to_number,
            direction='outbound',
            status='ringing',
            summary=message,
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Call initiated',
            'call_id': call_log.pk,
        })
    except Exception as e:
        logger.error(f"Failed to initiate outbound call: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def outbound_twiml(request):
    """Generate TwiML for outbound calls."""
    message = request.GET.get('message', 'Hello, this is an automated message from Kalton Investment.')
    
    twiml_response = '<?xml version="1.0" encoding="UTF-8"?>'
    twiml_response += '<Response>'
    twiml_response += f'<Say voice="alice">{message}</Say>'
    twiml_response += '</Response>'
    
    return HttpResponse(twiml_response, content_type='text/xml')


def call_logs_api(request):
    """API endpoint to get call logs."""
    calls = CallLog.objects.all()[:50]
    data = []
    for call in calls:
        data.append({
            'id': call.pk,
            'caller': call.caller_number,
            'direction': call.direction,
            'status': call.status,
            'duration': call.duration,
            'intent': call.intent_detected,
            'created_at': call.created_at.isoformat(),
        })
    return JsonResponse({'calls': data})
