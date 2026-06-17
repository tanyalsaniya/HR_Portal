# apps/exit_formality/models.py
import uuid
import datetime
from decimal import Decimal
from django.db import models
from django.conf import settings
from common.fields import EncryptedDecimalField
from rules import (
    EXIT_TYPE_CHOICES, EXIT_STATUS_CHOICES, KT_STATUS_CHOICES, EXIT_LINK_EXPIRY_DAYS, CLEARANCE_STATUS
)

class ExitRequest(models.Model):
    bitrix_user_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    resignation_date = models.DateField()
    last_working_day = models.DateField()
    exit_type = models.CharField(max_length=20, choices=EXIT_TYPE_CHOICES)
    exit_reason = models.TextField()
    mode_of_resignation = models.CharField(max_length=20)
    notice_period_waiver = models.BooleanField(default=False)
    notice_letter_required = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=EXIT_STATUS_CHOICES, default='PENDING')
    send_email_on_exit = models.BooleanField(default=True)
    email_documents = models.JSONField(default=list, blank=True)

    # Clearances
    clearance_it = models.CharField(max_length=10, choices=CLEARANCE_STATUS, default='PENDING')
    clearance_finance = models.CharField(max_length=10, choices=CLEARANCE_STATUS, default='PENDING')
    clearance_admin = models.CharField(max_length=10, choices=CLEARANCE_STATUS, default='PENDING')
    clearance_manager = models.CharField(max_length=10, choices=CLEARANCE_STATUS, default='PENDING')
    clearance_library = models.CharField(max_length=10, choices=CLEARANCE_STATUS, default='NA')

    # IT Revocation
    it_email_deactivated = models.BooleanField(default=False)
    it_system_access_revoked = models.BooleanField(default=False)
    it_vpn_removed = models.BooleanField(default=False)
    it_biometric_deactivated = models.BooleanField(default=False)
    it_data_backup_completed = models.BooleanField(default=False)

    # Leave balance
    leave_balance_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    leave_policy_option = models.CharField(
        max_length=20,
        choices=[('ENCASHMENT', 'Encashment'), ('ADJUST', 'Adjust'), ('LAPSE', 'Lapse')],
        default='LAPSE'
    )

    # Override / cancellation tracking
    override_reason = models.TextField(blank=True, null=True)
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='overridden_exits'
    )
    overridden_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True, null=True)

    # Secure link tracking
    secure_link_sent_at = models.DateTimeField(null=True, blank=True)
    secure_link_expires_at = models.DateTimeField(null=True, blank=True)

    # Meta
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_exits'
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Exit for User {self.bitrix_user_id} ({self.status})"

    @property
    def employee(self):
        from common.bitrix_client import BitrixClient, BitrixEmployeeMock
        user = BitrixClient.get_user_detail(self.bitrix_user_id)
        if user:
            return BitrixEmployeeMock(user)
        return None

class ExitSecureLink(models.Model):
    exit_request = models.OneToOneField(
        ExitRequest,
        on_delete=models.CASCADE,
        related_name='secure_link'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def is_valid(self):
        from django.utils import timezone
        now_dt = timezone.now() if timezone.is_aware(self.expires_at) else datetime.datetime.now()
        return not self.used and now_dt < self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + datetime.timedelta(days=EXIT_LINK_EXPIRY_DAYS)
        super().save(*args, **kwargs)

    def get_link(self):
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
        return f"{frontend_url}/exit/form/{self.token}/"

    def __str__(self):
        return f"Link for User {self.exit_request.bitrix_user_id} (Expired: {not self.is_valid()})"

class ExitFormResponse(models.Model):
    exit_request = models.OneToOneField(
        ExitRequest,
        on_delete=models.CASCADE,
        related_name='form_response'
    )
    
    # Asset Return Checkboxes + text
    asset_laptop_returned = models.BooleanField(default=False)
    asset_laptop_serial = models.CharField(max_length=100, blank=True, null=True)
    asset_laptop_remarks = models.TextField(blank=True, null=True)
    
    asset_id_returned = models.BooleanField(default=False)
    asset_id_remarks = models.TextField(blank=True, null=True)
    
    asset_access_card_returned = models.BooleanField(default=False)
    asset_access_card_remarks = models.TextField(blank=True, null=True)

    asset_mobile_returned = models.BooleanField(default=False)
    asset_mobile_number = models.CharField(max_length=20, blank=True, null=True)
    asset_mobile_remarks = models.TextField(blank=True, null=True)

    asset_locker_returned = models.BooleanField(default=False)
    asset_locker_remarks = models.TextField(blank=True, null=True)
    
    asset_others_details = models.TextField(blank=True, null=True)
    assets_confirmation = models.BooleanField(default=False)

    # Knowledge Transfer details
    kt_status = models.CharField(max_length=20, choices=KT_STATUS_CHOICES)
    kt_handover_to = models.CharField(max_length=100, blank=True, null=True)
    kt_completion_date = models.DateField(blank=True, null=True)
    kt_remarks = models.TextField(blank=True, null=True)
    kt_manager_confirmed = models.BooleanField(default=False)

    # Feedback questionnaire
    reason_dropdown = models.CharField(max_length=100)
    reason_details = models.TextField(blank=True, null=True)
    
    rating_env = models.PositiveIntegerField() # 1 to 5
    rating_mgmt = models.PositiveIntegerField() # 1 to 5
    rating_balance = models.PositiveIntegerField(default=5) # 1 to 5
    recommend = models.CharField(max_length=10) # Yes / No / Maybe
    liked_most = models.TextField(blank=True, null=True)
    improved_most = models.TextField(blank=True, null=True)
    other_feedback = models.TextField(blank=True, null=True)
    
    personal_email = models.EmailField()
    personal_phone = models.CharField(max_length=15, blank=True, null=True)
    personal_address = models.TextField(blank=True, null=True)
    declaration_confirmed = models.BooleanField(default=False)
    
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response for User {self.exit_request.bitrix_user_id}"

class ExitFFSettlement(models.Model):
    exit_request = models.OneToOneField(
        ExitRequest,
        on_delete=models.CASCADE,
        related_name='ff_settlement'
    )
    
    # Salary for Last Month
    salary_month_days = models.IntegerField(default=30)
    salary_worked_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    salary_proportional = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Leave Encashment
    leave_encashment_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    leave_encashment_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    leave_encashment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Pending Reimbursements (JSONField)
    reimbursements_json = models.JSONField(default=list, blank=True)
    
    bonus_arrears = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gratuity_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Deductions
    notice_shortfall_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notice_shortfall_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notice_shortfall_amount = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    
    salary_advance_outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bond_penalty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Other Deductions (JSONField)
    other_deductions_json = models.JSONField(default=list, blank=True)
    
    tds_deduction = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    per_day_salary = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    payment_mode = models.CharField(
        max_length=20,
        choices=[('BANK_TRANSFER', 'Bank Transfer'), ('CHEQUE', 'Cheque')],
        default='BANK_TRANSFER'
    )
    expected_payment_date = models.DateField(blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Tracking
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_ff_settlements'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    payment_processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_ff_settlements'
    )
    employee_acknowledgement = models.BooleanField(default=False)
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_ff_settlements'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"F&F Settlement for User {self.exit_request.bitrix_user_id}"
