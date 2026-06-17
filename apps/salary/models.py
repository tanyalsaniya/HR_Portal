from django.db import models
from django.conf import settings
from decimal import Decimal

class SalaryImportBatch(models.Model):
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
        ('processing', 'Processing'),
    )
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='salary_batches'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    total_records = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_report_path = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Batch {self.id} ({self.month}/{self.year}) - {self.status}"


class SalaryStructure(models.Model):
    bitrix_user_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pf_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    esi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    labour_welfare_fund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    professional_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    effective_from = models.DateField()

    @property
    def basic(self):
        # Fallback helper for any legacy views referencing basic
        return self.gross_salary

    @property
    def total_deductions(self):
        return (
            self.pf_contribution +
            self.esi +
            self.labour_welfare_fund +
            self.professional_tax +
            self.other_deductions
        )

    @property
    def net_salary(self):
        return self.gross_salary - self.total_deductions

    def __str__(self):
        return f"Salary Structure for User {self.bitrix_user_id} (Net: {self.net_salary})"

    @property
    def employee(self):
        from common.bitrix_client import BitrixClient, BitrixEmployeeMock
        user = BitrixClient.get_user_detail(self.bitrix_user_id)
        if user:
            return BitrixEmployeeMock(user)
        return None


class SalarySlip(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    bitrix_user_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    location = models.CharField(max_length=100, default='Mohali')

    # Attendance
    leaves_available = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    working_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    extra_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Earnings
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Deductions
    pf_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    esi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    labour_welfare_fund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    professional_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Net Pay
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_credited_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Metadata & Status
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    uploaded_batch = models.ForeignKey(
        SalaryImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='slips'
    )
    payslip_no = models.CharField(max_length=50, blank=True, null=True, unique=True)
    pdf_file = models.FileField(upload_to='salary_slips/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ('bitrix_user_id', 'month', 'year')

    def save(self, *args, **kwargs):
        # Auto calculate gross, deductions, net salary
        self.total_deductions = (
            Decimal(self.pf_contribution or 0) +
            Decimal(self.esi or 0) +
            Decimal(self.labour_welfare_fund or 0) +
            Decimal(self.professional_tax or 0) +
            Decimal(self.other_deductions or 0)
        )
        self.net_salary = Decimal(self.gross_salary or 0) - self.total_deductions
        self.net_credited_amount = self.net_salary

        if not self.payslip_no:
            # Generate temporary unique payslip number if none set
            from common.utils import generate_payslip_number
            self.payslip_no = generate_payslip_number(self.year, self.month)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payslip {self.payslip_no} for User {self.bitrix_user_id}"

    @property
    def employee(self):
        from common.bitrix_client import BitrixClient, BitrixEmployeeMock
        user = BitrixClient.get_user_detail(self.bitrix_user_id)
        if user:
            return BitrixEmployeeMock(user)
        return None


class SalaryIncrementReminder(models.Model):
    bitrix_user_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    anniversary_date = models.DateField()
    reminder_15_sent = models.BooleanField(default=False)
    reminder_7_sent = models.BooleanField(default=False)
    reminder_0_sent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=(('Pending', 'Pending'), ('Actioned', 'Actioned')), default='Pending')
    actioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='actioned_reminders'
    )
    actioned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Reminder for User {self.bitrix_user_id} ({self.status})"

    @property
    def employee(self):
        from common.bitrix_client import BitrixClient, BitrixEmployeeMock
        user = BitrixClient.get_user_detail(self.bitrix_user_id)
        if user:
            return BitrixEmployeeMock(user)
        return None


class SalaryIncrementApproval(models.Model):
    bitrix_user_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    reminder = models.ForeignKey(
        SalaryIncrementReminder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approvals'
    )
    old_net = models.DecimalField(max_digits=10, decimal_places=2)
    new_basic = models.DecimalField(max_digits=10, decimal_places=2)
    new_hra = models.DecimalField(max_digits=10, decimal_places=2)
    new_allowances = models.DecimalField(max_digits=10, decimal_places=2)
    new_net = models.DecimalField(max_digits=10, decimal_places=2)
    increment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    increment_pct = models.DecimalField(max_digits=5, decimal_places=2)
    effective_date = models.DateField()
    reason = models.TextField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_increments'
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='salary_increments/')

    def __str__(self):
        return f"Increment for User {self.bitrix_user_id} (Pct: {self.increment_pct}%)"

    @property
    def employee(self):
        from common.bitrix_client import BitrixClient, BitrixEmployeeMock
        user = BitrixClient.get_user_detail(self.bitrix_user_id)
        if user:
            return BitrixEmployeeMock(user)
        return None
