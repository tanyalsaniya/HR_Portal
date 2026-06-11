from django.db import models
from django.conf import settings
from decimal import Decimal
from common.fields import EncryptedDecimalField

class SalaryStructure(models.Model):
    employee = models.ForeignKey(
        'employee_onboarding.Employee',
        on_delete=models.CASCADE,
        related_name='salary_structures'
    )
    effective_from = models.DateField()
    
    # Encrypted salary earnings components
    basic = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    hra = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    conveyance = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    medical = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    special = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    monthly_bonus = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    
    # Repeatable rows stored as JSON
    other_allowances = models.JSONField(default=list, blank=True)
    
    # Encrypted salary deductions components
    pf = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    professional_tax = EncryptedDecimalField(max_length=255, default=Decimal('200.00'))
    tds = EncryptedDecimalField(max_length=255, default=Decimal('0.00'))
    
    # Repeatable deductions stored as JSON
    other_deductions = models.JSONField(default=list, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_salaries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def gross_salary(self):
        basic = Decimal(self.basic or 0)
        hra = Decimal(self.hra or 0)
        conveyance = Decimal(self.conveyance or 0)
        medical = Decimal(self.medical or 0)
        special = Decimal(self.special or 0)
        monthly_bonus = Decimal(self.monthly_bonus or 0)
        total = basic + hra + conveyance + medical + special + monthly_bonus
        for allowance in self.other_allowances:
            try:
                total += Decimal(str(allowance.get('amount', 0)))
            except (ValueError, TypeError):
                pass
        return total

    @property
    def total_deductions(self):
        pf = Decimal(self.pf or 0)
        pt = Decimal(self.professional_tax or 0)
        tds = Decimal(self.tds or 0)
        total = pf + pt + tds
        for deduction in self.other_deductions:
            try:
                total += Decimal(str(deduction.get('amount', 0)))
            except (ValueError, TypeError):
                pass
        return total

    @property
    def net_salary(self):
        return self.gross_salary - self.total_deductions

    def __str__(self):
        return f"Salary Structure for {self.employee.emp_id} (Net: {self.net_salary})"


class SalarySlip(models.Model):
    PAYMENT_MODE_CHOICES = (
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('CASH', 'Cash'),
    )

    employee = models.ForeignKey(
        'employee_onboarding.Employee',
        on_delete=models.CASCADE,
        related_name='salary_slips'
    )
    payslip_no = models.CharField(max_length=30, unique=True)
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    working_days = models.PositiveIntegerField()
    days_worked = models.PositiveIntegerField()
    lop_days = models.PositiveIntegerField(default=0)
    
    one_time_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    one_time_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    gross = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_date = models.DateField()
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='BANK_TRANSFER')
    pdf_file = models.FileField(upload_to='salary_slips/')
    
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_slips'
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payslip {self.payslip_no} for {self.employee.emp_id}"


class SalaryIncrementReminder(models.Model):
    employee = models.ForeignKey(
        'employee_onboarding.Employee',
        on_delete=models.CASCADE,
        related_name='increment_reminders'
    )
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
        return f"Reminder for {self.employee.emp_id} ({self.status})"


class SalaryIncrementApproval(models.Model):
    employee = models.ForeignKey(
        'employee_onboarding.Employee',
        on_delete=models.CASCADE,
        related_name='increment_approvals'
    )
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
    reason = models.TextField()  # min 20 chars validation in serializer
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_increments'
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='salary_increments/')

    def __str__(self):
        return f"Increment for {self.employee.emp_id} (Pct: {self.increment_pct}%)"
