from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone

from .models import PaymentRequest
from .sms_parser import parse_sms


# ──────────────────────────────────────────────
#  Stage 0: Intake
# ──────────────────────────────────────────────

@login_required
def intake_sms(request):
    """Form to paste SMS text. System parses it and creates a PaymentRequest."""
    parsed_result = None

    if request.method == 'POST':
        sms_text = request.POST.get('sms_text', '').strip()
        if sms_text:
            parsed = parse_sms(sms_text)
            parsed_result = parsed

            if request.POST.get('confirm') == 'yes':
                # Create the PaymentRequest from parsed data
                pay = PaymentRequest(
                    raw_sms=sms_text,
                    amount=parsed.get('amount'),
                    currency=parsed.get('currency'),
                    sender_name=parsed.get('sender_name'),
                    from_account=parsed.get('from_account'),
                    from_account_type=parsed.get('from_account_type'),
                    from_bank=parsed.get('from_bank'),
                    receiver_name=parsed.get('receiver_name'),
                    to_account=parsed.get('to_account'),
                    to_account_type=parsed.get('to_account_type'),
                    to_bank=parsed.get('to_bank'),
                    reference=parsed.get('reference'),
                    memo=parsed.get('memo'),
                    transaction_date=parsed.get('transaction_date'),
                    parse_confidence=parsed.get('parse_confidence'),
                    parse_notes=parsed.get('parse_notes'),
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
                pay.save()
                messages.success(request, f'✅ Payment request created and sent for review!')
                return redirect('payments:dashboard')

    return render(request, 'payments/intake.html', {
        'parsed': parsed_result,
    })


# ──────────────────────────────────────────────
#  Dashboard (Kanban-style)
# ──────────────────────────────────────────────

@login_required
def dashboard(request):
    """Kanban view showing all stages of the workflow."""
    counts = {
        'pending_review': PaymentRequest.objects.filter(
            status=PaymentRequest.Status.PENDING_REVIEW
        ).count(),
        'failed': PaymentRequest.objects.filter(
            status=PaymentRequest.Status.FAILED
        ).count(),
        'pending_authorization': PaymentRequest.objects.filter(
            status=PaymentRequest.Status.PENDING_AUTHORIZATION
        ).count(),
        'authorized': PaymentRequest.objects.filter(
            status=PaymentRequest.Status.AUTHORIZED
        ).count(),
        'rejected': PaymentRequest.objects.filter(
            status=PaymentRequest.Status.REJECTED
        ).count(),
    }

    pending_review = PaymentRequest.objects.filter(
        status=PaymentRequest.Status.PENDING_REVIEW
    )[:20]
    pending_auth = PaymentRequest.objects.filter(
        status=PaymentRequest.Status.PENDING_AUTHORIZATION
    )[:20]

    return render(request, 'payments/dashboard.html', {
        'counts': counts,
        'pending_review': pending_review,
        'pending_auth': pending_auth,
    })


# ──────────────────────────────────────────────
#  Stage 2: Review
# ──────────────────────────────────────────────

@login_required
@permission_required('payments.can_review_payment', raise_exception=True)
def review_detail(request, pk):
    """Review a payment request: approve (pass to authorization) or fail (discard)."""
    payment = get_object_or_404(PaymentRequest, pk=pk)

    if payment.status != PaymentRequest.Status.PENDING_REVIEW:
        messages.warning(request, 'This payment is not pending review.')
        return redirect('payments:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')

        if action == 'approve':
            payment.approve_review(request.user, notes)
            messages.success(request, f'✅ Payment approved and sent for authorization!')
        elif action == 'fail':
            payment.fail_review(request.user, notes)
            messages.warning(request, f'❌ Payment discarded (failed review).')
        else:
            messages.error(request, 'Invalid action.')

        return redirect('payments:dashboard')

    return render(request, 'payments/review.html', {
        'payment': payment,
    })


# ──────────────────────────────────────────────
#  Stage 3: Authorize
# ──────────────────────────────────────────────

@login_required
@permission_required('payments.can_authorize_payment', raise_exception=True)
def authorize_detail(request, pk):
    """Authorize a payment request: approve and execute, or reject."""
    payment = get_object_or_404(PaymentRequest, pk=pk)

    if payment.status != PaymentRequest.Status.PENDING_AUTHORIZATION:
        messages.warning(request, 'This payment is not pending authorization.')
        return redirect('payments:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')

        if action == 'authorize':
            payment.authorize(request.user, notes)
            messages.success(request, f'✅ Payment authorized and executed!')
        elif action == 'reject':
            payment.reject(request.user, notes)
            messages.warning(request, f'🚫 Payment rejected.')
        else:
            messages.error(request, 'Invalid action.')

        return redirect('payments:dashboard')

    return render(request, 'payments/authorize.html', {
        'payment': payment,
    })


# ──────────────────────────────────────────────
#  History
# ──────────────────────────────────────────────

@login_required
def history(request):
    """View all completed payment requests (authorized, rejected, failed)."""
    status_filter = request.GET.get('status', '')
    query = PaymentRequest.objects.exclude(
        status=PaymentRequest.Status.PENDING_REVIEW
    ).exclude(
        status=PaymentRequest.Status.PENDING_AUTHORIZATION
    )

    if status_filter:
        query = query.filter(status=status_filter)

    payments = query[:50]

    return render(request, 'payments/history.html', {
        'payments': payments,
        'current_filter': status_filter,
    })
