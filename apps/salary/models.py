from django.db import models
from django.conf import settings
from decimal import Decimal
from common.fields import EncryptedDecimalField

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
    gross_salary = EncryptedDecimalField(default=Decimal('0.00'))
    pf_contribution = EncryptedDecimalField(default=Decimal('0.00'))
    esi = EncryptedDecimalField(default=Decimal('0.00'))
    labour_welfare_fund = EncryptedDecimalField(default=Decimal('0.00'))
    professional_tax = EncryptedDecimalField(default=Decimal('0.00'))
    other_deductions = EncryptedDecimalField(default=Decimal('0.00'))
    effective_from = models.DateField()

    # New detailed breakup fields
    ctc = EncryptedDecimalField(default=Decimal('0.00'))
    basic_salary = EncryptedDecimalField(default=Decimal('0.00'))
    hra = EncryptedDecimalField(default=Decimal('0.00'))
    conveyance = EncryptedDecimalField(default=Decimal('0.00'))
    medical_allowance = EncryptedDecimalField(default=Decimal('0.00'))
    special_allowance = EncryptedDecimalField(default=Decimal('0.00'))
    monthly_bonus = EncryptedDecimalField(default=Decimal('0.00'))
    esi_employer = EncryptedDecimalField(default=Decimal('0.00'))
    pf_employer = EncryptedDecimalField(default=Decimal('0.00'))
    pf_employee = EncryptedDecimalField(default=Decimal('0.00'))
    esi_employee = EncryptedDecimalField(default=Decimal('0.00'))
    lwf = EncryptedDecimalField(default=Decimal('0.00'))
    in_hand_salary = EncryptedDecimalField(default=Decimal('0.00'))

    @property
    def basic(self):
        if self.basic_salary != Decimal('0.00'):
            return self.basic_salary
        return self.gross_salary

    @property
    def effective_pf_employee(self):
        if self.pf_employee != Decimal('0.00'):
            return self.pf_employee
        return self.pf_contribution

    @property
    def effective_esi_employee(self):
        if self.esi_employee != Decimal('0.00'):
            return self.esi_employee
        return self.esi

    @property
    def effective_lwf(self):
        if self.lwf != Decimal('0.00'):
            return self.lwf
        return self.labour_welfare_fund

    @property
    def total_deductions(self):
        return (
            self.effective_pf_employee +
            self.effective_esi_employee +
            self.effective_lwf +
            self.professional_tax +
            self.other_deductions
        )

    @property
    def net_salary(self):
        if self.in_hand_salary != Decimal('0.00'):
            return self.in_hand_salary
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
    month_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    worked_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    weekend = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    cl = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    extra = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    payable_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Earnings
    month_salary = EncryptedDecimalField(default=Decimal('0.00'))
    payable_salary = EncryptedDecimalField(default=Decimal('0.00'))
    extra_days_working = EncryptedDecimalField(default=Decimal('0.00'))

    # Deductions
    fine_advance = EncryptedDecimalField(default=Decimal('0.00'))

    # Net Pay
    net_payable = EncryptedDecimalField(default=Decimal('0.00'))

    # Bank Details
    bank_account_no = models.CharField(max_length=50, blank=True, null=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, null=True, default='')

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
        if not getattr(self, '_skip_recalculation', False):
            # Calculate payable_days = worked_days + weekend + cl + extra
            self.payable_days = (
                Decimal(self.worked_days or 0) +
                Decimal(self.weekend or 0) +
                Decimal(self.cl or 0) +
                Decimal(self.extra or 0)
            ).quantize(Decimal('0.01'))
            
            # Calculate payable_salary = (month_salary / month_days) * payable_days
            if self.month_days and Decimal(self.month_days) > 0:
                self.payable_salary = ((Decimal(self.month_salary or 0) / Decimal(self.month_days)) * Decimal(self.payable_days)).quantize(Decimal('0.01'))
            else:
                self.payable_salary = Decimal(self.month_salary or 0).quantize(Decimal('0.01'))

            # Calculate net_payable = payable_salary + extra_days_working - fine_advance
            self.net_payable = (Decimal(self.payable_salary or 0) + Decimal(self.extra_days_working or 0) - Decimal(self.fine_advance or 0)).quantize(Decimal('0.01'))
        else:
            # Even when skipping, if payable_days is 0 or None, calculate it based on attendance
            if not self.payable_days or self.payable_days == 0:
                self.payable_days = (
                    Decimal(self.worked_days or 0) +
                    Decimal(self.weekend or 0) +
                    Decimal(self.cl or 0) +
                    Decimal(self.extra or 0)
                ).quantize(Decimal('0.01'))

        if not self.payslip_no:
            from common.utils import generate_payslip_number
            self.payslip_no = generate_payslip_number(self.year, self.month)

        super().save(*args, **kwargs)

    @property
    def gross_salary(self):
        return self.month_salary
    
    @gross_salary.setter
    def gross_salary(self, value):
        self.month_salary = value

    @property
    def net_salary(self):
        return self.net_payable
    
    @net_salary.setter
    def net_salary(self, value):
        self.net_payable = value

    @property
    def net_credited_amount(self):
        return self.net_payable
    
    @net_credited_amount.setter
    def net_credited_amount(self, value):
        self.net_payable = value

    @property
    def total_deductions(self):
        return self.fine_advance
    
    @total_deductions.setter
    def total_deductions(self, value):
        self.fine_advance = value

    @property
    def pf_contribution(self):
        return Decimal('0.00')

    @pf_contribution.setter
    def pf_contribution(self, value):
        pass

    @property
    def esi(self):
        return Decimal('0.00')

    @esi.setter
    def esi(self, value):
        pass

    @property
    def labour_welfare_fund(self):
        return Decimal('0.00')

    @labour_welfare_fund.setter
    def labour_welfare_fund(self, value):
        pass

    @property
    def professional_tax(self):
        return Decimal('0.00')

    @professional_tax.setter
    def professional_tax(self, value):
        pass

    @property
    def other_deductions(self):
        return Decimal('0.00')

    @other_deductions.setter
    def other_deductions(self, value):
        pass

    @property
    def leaves_available(self):
        return self.cl

    @leaves_available.setter
    def leaves_available(self, value):
        self.cl = value

    @property
    def working_days(self):
        return self.payable_days

    @working_days.setter
    def working_days(self, value):
        self.payable_days = value

    @property
    def extra_days(self):
        return self.extra

    @extra_days.setter
    def extra_days(self, value):
        self.extra = value

    @property
    def masked_bank_account_no(self):
        if not self.bank_account_no:
            return ""
        val = str(self.bank_account_no).strip()
        if len(val) <= 4:
            return "X" * len(val)
        return "X" * (len(val) - 4) + val[-4:]

    @property
    def total_earnings(self):
        return Decimal(self.payable_salary or 0) + Decimal(self.extra_days_working or 0)

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
    old_net = EncryptedDecimalField()
    new_basic = EncryptedDecimalField()
    new_hra = EncryptedDecimalField()
    new_allowances = EncryptedDecimalField()
    new_net = EncryptedDecimalField()
    increment_amount = EncryptedDecimalField()
    increment_pct = EncryptedDecimalField()
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


class EmployeeBankDetail(models.Model):
    bitrix_user_id = models.CharField(max_length=50, unique=True, db_index=True)
    bank_account_no = models.CharField(max_length=50, blank=True, null=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, null=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Bank Detail for User {self.bitrix_user_id}: {self.bank_name} - {self.bank_account_no}"


# =====================================================================
# DISMISSED EMPLOYEE MODELS (PARALLEL PAYROLL)
# =====================================================================

class DismissedSalaryImportBatch(models.Model):
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
        related_name='dismissed_salary_batches'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    total_records = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_report_path = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Dismissed Batch {self.id} ({self.month}/{self.year}) - {self.status}"


class DismissedSalaryStructure(models.Model):
    bitrix_user_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    gross_salary = EncryptedDecimalField(default=Decimal('0.00'))
    pf_contribution = EncryptedDecimalField(default=Decimal('0.00'))
    esi = EncryptedDecimalField(default=Decimal('0.00'))
    labour_welfare_fund = EncryptedDecimalField(default=Decimal('0.00'))
    professional_tax = EncryptedDecimalField(default=Decimal('0.00'))
    other_deductions = EncryptedDecimalField(default=Decimal('0.00'))
    effective_from = models.DateField()

    # New detailed breakup fields
    ctc = EncryptedDecimalField(default=Decimal('0.00'))
    basic_salary = EncryptedDecimalField(default=Decimal('0.00'))
    hra = EncryptedDecimalField(default=Decimal('0.00'))
    conveyance = EncryptedDecimalField(default=Decimal('0.00'))
    medical_allowance = EncryptedDecimalField(default=Decimal('0.00'))
    special_allowance = EncryptedDecimalField(default=Decimal('0.00'))
    monthly_bonus = EncryptedDecimalField(default=Decimal('0.00'))
    esi_employer = EncryptedDecimalField(default=Decimal('0.00'))
    pf_employer = EncryptedDecimalField(default=Decimal('0.00'))
    pf_employee = EncryptedDecimalField(default=Decimal('0.00'))
    esi_employee = EncryptedDecimalField(default=Decimal('0.00'))
    lwf = EncryptedDecimalField(default=Decimal('0.00'))
    in_hand_salary = EncryptedDecimalField(default=Decimal('0.00'))

    @property
    def basic(self):
        if self.basic_salary != Decimal('0.00'):
            return self.basic_salary
        return self.gross_salary

    @property
    def effective_pf_employee(self):
        if self.pf_employee != Decimal('0.00'):
            return self.pf_employee
        return self.pf_contribution

    @property
    def effective_esi_employee(self):
        if self.esi_employee != Decimal('0.00'):
            return self.esi_employee
        return self.esi

    @property
    def effective_lwf(self):
        if self.lwf != Decimal('0.00'):
            return self.lwf
        return self.labour_welfare_fund

    @property
    def total_deductions(self):
        return (
            self.effective_pf_employee +
            self.effective_esi_employee +
            self.effective_lwf +
            self.professional_tax +
            self.other_deductions
        )

    @property
    def net_salary(self):
        if self.in_hand_salary != Decimal('0.00'):
            return self.in_hand_salary
        return self.gross_salary - self.total_deductions

    def __str__(self):
        return f"Dismissed Salary Structure for User {self.bitrix_user_id} (Net: {self.net_salary})"

    @property
    def employee(self):
        from common.bitrix_client import BitrixClient, BitrixEmployeeMock
        user = BitrixClient.get_user_detail(self.bitrix_user_id)
        if user:
            return BitrixEmployeeMock(user)
        return None


class DismissedSalarySlip(models.Model):
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
    month_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    worked_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    weekend = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    cl = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    extra = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    payable_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Earnings
    month_salary = EncryptedDecimalField(default=Decimal('0.00'))
    payable_salary = EncryptedDecimalField(default=Decimal('0.00'))
    extra_days_working = EncryptedDecimalField(default=Decimal('0.00'))

    # Deductions
    fine_advance = EncryptedDecimalField(default=Decimal('0.00'))

    # Net Pay
    net_payable = EncryptedDecimalField(default=Decimal('0.00'))

    # Bank Details
    bank_account_no = models.CharField(max_length=50, blank=True, null=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, null=True, default='')

    # Metadata & Status
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    uploaded_batch = models.ForeignKey(
        DismissedSalaryImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='slips'
    )
    payslip_no = models.CharField(max_length=50, blank=True, null=True, unique=True)
    pdf_file = models.FileField(upload_to='dismissed_salary_slips/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ('bitrix_user_id', 'month', 'year')

    def save(self, *args, **kwargs):
        if not getattr(self, '_skip_recalculation', False):
            # Calculate payable_days = worked_days + weekend + cl + extra
            self.payable_days = (
                Decimal(self.worked_days or 0) +
                Decimal(self.weekend or 0) +
                Decimal(self.cl or 0) +
                Decimal(self.extra or 0)
            ).quantize(Decimal('0.01'))
            
            # Calculate payable_salary = (month_salary / month_days) * payable_days
            if self.month_days and Decimal(self.month_days) > 0:
                self.payable_salary = ((Decimal(self.month_salary or 0) / Decimal(self.month_days)) * Decimal(self.payable_days)).quantize(Decimal('0.01'))
            else:
                self.payable_salary = Decimal(self.month_salary or 0).quantize(Decimal('0.01'))

            # Calculate net_payable = payable_salary + extra_days_working - fine_advance
            self.net_payable = (Decimal(self.payable_salary or 0) + Decimal(self.extra_days_working or 0) - Decimal(self.fine_advance or 0)).quantize(Decimal('0.01'))
        else:
            # Even when skipping, if payable_days is 0 or None, calculate it based on attendance
            if not self.payable_days or self.payable_days == 0:
                self.payable_days = (
                    Decimal(self.worked_days or 0) +
                    Decimal(self.weekend or 0) +
                    Decimal(self.cl or 0) +
                    Decimal(self.extra or 0)
                ).quantize(Decimal('0.01'))

        if not self.payslip_no:
            from common.utils import generate_payslip_number
            self.payslip_no = generate_payslip_number(self.year, self.month, is_dismissed=True) + "-D"

        super().save(*args, **kwargs)

    @property
    def gross_salary(self):
        return self.month_salary
    
    @gross_salary.setter
    def gross_salary(self, value):
        self.month_salary = value

    @property
    def net_salary(self):
        return self.net_payable
    
    @net_salary.setter
    def net_salary(self, value):
        self.net_payable = value

    @property
    def net_credited_amount(self):
        return self.net_payable
    
    @net_credited_amount.setter
    def net_credited_amount(self, value):
        self.net_payable = value

    @property
    def total_deductions(self):
        return self.fine_advance
    
    @total_deductions.setter
    def total_deductions(self, value):
        self.fine_advance = value

    @property
    def pf_contribution(self):
        return Decimal('0.00')

    @pf_contribution.setter
    def pf_contribution(self, value):
        pass

    @property
    def esi(self):
        return Decimal('0.00')

    @esi.setter
    def esi(self, value):
        pass

    @property
    def labour_welfare_fund(self):
        return Decimal('0.00')

    @labour_welfare_fund.setter
    def labour_welfare_fund(self, value):
        pass

    @property
    def professional_tax(self):
        return Decimal('0.00')

    @professional_tax.setter
    def professional_tax(self, value):
        pass

    @property
    def other_deductions(self):
        return Decimal('0.00')

    @other_deductions.setter
    def other_deductions(self, value):
        pass

    @property
    def leaves_available(self):
        return self.cl

    @leaves_available.setter
    def leaves_available(self, value):
        self.cl = value

    @property
    def working_days(self):
        return self.payable_days

    @working_days.setter
    def working_days(self, value):
        self.payable_days = value

    @property
    def extra_days(self):
        return self.extra

    @extra_days.setter
    def extra_days(self, value):
        self.extra = value

    @property
    def masked_bank_account_no(self):
        if not self.bank_account_no:
            return ""
        val = str(self.bank_account_no).strip()
        if len(val) <= 4:
            return "X" * len(val)
        return "X" * (len(val) - 4) + val[-4:]

    @property
    def total_earnings(self):
        return Decimal(self.payable_salary or 0) + Decimal(self.extra_days_working or 0)

    def __str__(self):
        return f"Dismissed Payslip {self.payslip_no} for User {self.bitrix_user_id}"

    @property
    def employee(self):
        from common.bitrix_client import BitrixClient, BitrixEmployeeMock
        user = BitrixClient.get_user_detail(self.bitrix_user_id)
        if user:
            return BitrixEmployeeMock(user)
        return None


class DismissedEmployeeBankDetail(models.Model):
    bitrix_user_id = models.CharField(max_length=50, unique=True, db_index=True)
    bank_account_no = models.CharField(max_length=50, blank=True, null=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, null=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Dismissed Bank Detail for User {self.bitrix_user_id}: {self.bank_name} - {self.bank_account_no}"
