import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PaymentRequest(models.Model):
    """
    A payment request that flows through the 3-stage workflow:
    1. INTAKE (parsed from SMS)
    2. REVIEW (verified by reviewer)
    3. AUTHORIZE (approved by authorizer)
    """
    class Status(models.TextChoices):
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        FAILED = 'failed', 'Failed Review'
        PENDING_AUTHORIZATION = 'pending_authorization', 'Pending Authorization'
        AUTHORIZED = 'authorized', 'Authorized'
        REJECTED = 'rejected', 'Rejected'

    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING_REVIEW,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Raw SMS ---
    raw_sms = models.TextField(help_text="Original SMS text received")

    # --- Parsed data (extracted by the system) ---
    # Amount & Currency
    amount = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True,
        help_text="Extracted amount",
    )
    currency = models.CharField(
        max_length=10, null=True, blank=True,
        help_text="Extracted currency (TZS, USD, etc.)",
    )

    # Sender / From
    sender_name = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Name of the person/entity sending the money",
    )
    from_account = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Source account number",
    )
    from_account_type = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Source type: BANK, MOMO, or INTL",
    )
    from_bank = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Source bank name (e.g. Mkombozi, NBC, NMB, CRDB, etc.)",
    )

    # Receiver / To
    receiver_name = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Name of recipient",
    )
    to_account = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Destination account number",
    )
    to_account_type = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Destination type: BANK, MOMO, or INTL",
    )
    to_bank = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Destination bank name",
    )

    # Reference / Memo
    reference = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Transaction reference number from SMS",
    )
    memo = models.TextField(
        null=True, blank=True,
        help_text="Extra description / purpose",
    )
    transaction_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Date of the original transaction",
    )

    # --- Parsing confidence ---
    parse_confidence = models.FloatField(
        null=True, blank=True,
        help_text="Confidence score (0.0 to 1.0) of the parse",
    )
    parse_notes = models.TextField(
        null=True, blank=True,
        help_text="Notes about parsing warnings/issues",
    )

    # --- Stage 2: Review ---
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payment_reviews',
        help_text="Reviewer who verified this request",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(
        null=True, blank=True,
        help_text="Notes from the reviewer (if failed/discarded)",
    )

    # --- Stage 3: Authorization ---
    authorized_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payment_authorizations',
        help_text="Authorizer who approved/rejected this request",
    )
    authorized_at = models.DateTimeField(null=True, blank=True)
    authorization_notes = models.TextField(
        null=True, blank=True,
        help_text="Notes from the authorizer",
    )

    # --- Audit ---
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="IP address of the intake source",
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Request'
        verbose_name_plural = 'Payment Requests'
        permissions = [
            ('can_review_payment', 'Can review and verify payment requests'),
            ('can_authorize_payment', 'Can authorize and execute payment requests'),
        ]

    def __str__(self):
        amt = f"{self.amount or '?'} {self.currency or ''}"
        return f"Payment {self.id} [{self.status}] {amt}"

    def approve_review(self, reviewer, notes=""):
        """Move from PENDING_REVIEW to PENDING_AUTHORIZATION"""
        if self.status != self.Status.PENDING_REVIEW:
            raise ValueError(f"Cannot approve review: current status is {self.status}")
        self.status = self.Status.PENDING_AUTHORIZATION
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

    def fail_review(self, reviewer, notes=""):
        """Move from PENDING_REVIEW to FAILED (discarded)"""
        if self.status != self.Status.PENDING_REVIEW:
            raise ValueError(f"Cannot fail review: current status is {self.status}")
        self.status = self.Status.FAILED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

    def authorize(self, authorizer, notes=""):
        """Move from PENDING_AUTHORIZATION to AUTHORIZED"""
        if self.status != self.Status.PENDING_AUTHORIZATION:
            raise ValueError(f"Cannot authorize: current status is {self.status}")
        self.status = self.Status.AUTHORIZED
        self.authorized_by = authorizer
        self.authorized_at = timezone.now()
        self.authorization_notes = notes
        self.save()

    def reject(self, authorizer, notes=""):
        """Move from PENDING_AUTHORIZATION to REJECTED"""
        if self.status != self.Status.PENDING_AUTHORIZATION:
            raise ValueError(f"Cannot reject: current status is {self.status}")
        self.status = self.Status.REJECTED
        self.authorized_by = authorizer
        self.authorized_at = timezone.now()
        self.authorization_notes = notes
        self.save()
