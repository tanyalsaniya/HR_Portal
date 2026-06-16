# apps/salary/services.py
import datetime
from decimal import Decimal
from django.core.files.base import ContentFile
from employee_onboarding.services import generate_document_pdf
from .models import SalaryStructure, SalarySlip, SalaryIncrementApproval

def calculate_payslip_details(employee, year, month, working_days, days_worked, one_time_bonus=0, one_time_deduction=0):
    """
    Calculates LOP and scales the salary earnings components proportionally.
    Returns a dictionary of calculated earnings, deductions, and net pay.
    """
    structure = SalaryStructure.objects.filter(
        employee=employee,
        effective_from__lte=datetime.date(year, month, 28) # Approximate end of month
    ).order_by('-effective_from').first()
    
    if not structure:
        raise ValueError("No active salary structure found for this employee.")
        
    working_days = Decimal(working_days)
    days_worked = Decimal(days_worked)
    lop_days = int(working_days - days_worked)
    ratio = days_worked / working_days if working_days > 0 else Decimal('1.0')
    
    # Scale earnings
    basic_earned = Decimal(structure.basic or 0) * ratio
    hra_earned = Decimal(structure.hra or 0) * ratio
    conveyance_earned = Decimal(structure.conveyance or 0) * ratio
    medical_earned = Decimal(structure.medical or 0) * ratio
    special_earned = Decimal(structure.special or 0) * ratio
    bonus_earned = Decimal(structure.monthly_bonus or 0) * ratio
    
    other_allowances_earned = []
    allowances_total = Decimal('0.00')
    for allowance in structure.other_allowances:
        amt = Decimal(str(allowance.get('amount', 0))) * ratio
        allowances_total += amt
        other_allowances_earned.append({
            'label': allowance.get('label'),
            'base_amount': allowance.get('amount'),
            'earned_amount': f"{amt:.2f}"
        })
        
    gross = basic_earned + hra_earned + conveyance_earned + medical_earned + special_earned + bonus_earned + allowances_total
    gross += Decimal(one_time_bonus)
    
    # Deductions (Deductions are usually kept fixed unless configured otherwise)
    pf = Decimal(structure.pf or 0)
    pt = Decimal(structure.professional_tax or 0)
    tds = Decimal(structure.tds or 0)
    
    deductions_total = pf + pt + tds
    other_deductions_earned = []
    for deduction in structure.other_deductions:
        amt = Decimal(str(deduction.get('amount', 0)))
        deductions_total += amt
        other_deductions_earned.append({
            'label': deduction.get('label'),
            'amount': f"{amt:.2f}"
        })
        
    deductions_total += Decimal(one_time_deduction)
    net_pay = gross - deductions_total
    
    return {
        'structure': structure,
        'lop_days': lop_days,
        'ratio': ratio,
        'basic_earned': basic_earned,
        'hra_earned': hra_earned,
        'conveyance_earned': conveyance_earned,
        'medical_earned': medical_earned,
        'special_earned': special_earned,
        'bonus_earned': bonus_earned,
        'other_allowances_earned': other_allowances_earned,
        'gross': gross,
        'pf': pf,
        'pt': pt,
        'tds': tds,
        'other_deductions_earned': other_deductions_earned,
        'total_deductions': deductions_total,
        'net_pay': net_pay
    }

def generate_payslip_pdf(salary_slip, details, user=None):
    """
    Renders monthly payslip to PDF and saves it to the SalarySlip record.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML
    
    context = {
        'slip': salary_slip,
        'details': details,
        'employee': salary_slip.employee,
        'company_name': 'DevexHub Pvt. Ltd.',
        'today': datetime.date.today()
    }
    
    html_string = render_to_string('salary/pdf_payslip.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    filename = f"payslip_{salary_slip.payslip_no}.pdf"
    salary_slip.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    return salary_slip

def generate_increment_letter_pdf(approval, user=None):
    """
    Renders increment approval letter and saves it to the SalaryIncrementApproval record.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML
    
    context = {
        'approval': approval,
        'employee': approval.employee,
        'company_name': 'MTLV Solutions Private Limited',
        'today': datetime.date.today()
    }
    
    html_string = render_to_string('salary/pdf_increment_letter.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    filename = f"increment_letter_{approval.employee.emp_id}_{int(datetime.datetime.now().timestamp())}.pdf"
    approval.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    return approval
