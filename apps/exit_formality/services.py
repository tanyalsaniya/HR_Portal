# apps/exit_formality/services.py
import datetime
from decimal import Decimal
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.template import Template, Context
from weasyprint import HTML
from employee_onboarding.models import EmployeeDocument, LetterTemplate

class MockObj:
    def __init__(self, original_obj=None, **kwargs):
        self._original = original_obj
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        if self._original is not None:
            return getattr(self._original, name)
        raise AttributeError(f"'MockObj' object has no attribute '{name}'")

def get_exit_letter_context(exit_request, custom_context=None):
    employee = exit_request.employee
    ff = getattr(exit_request, 'ff_settlement', None)
    
    custom_context = custom_context or {}
    
    # Overrides for employee
    emp_overrides = {}
    for field in ['first_name', 'last_name', 'designation']:
        if field in custom_context:
            emp_overrides[field] = custom_context[field]
    if 'joining_date' in custom_context:
        try:
            emp_overrides['joining_date'] = datetime.datetime.strptime(custom_context['joining_date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    mock_employee = MockObj(employee, **emp_overrides)
    
    # Overrides for exit_request
    exit_overrides = {}
    if 'last_working_day' in custom_context:
        try:
            exit_overrides['last_working_day'] = datetime.datetime.strptime(custom_context['last_working_day'], '%Y-%m-%d').date()
        except ValueError:
            pass
    if 'resignation_date' in custom_context:
        try:
            exit_overrides['resignation_date'] = datetime.datetime.strptime(custom_context['resignation_date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    mock_exit_request = MockObj(exit_request, employee=mock_employee, **exit_overrides)
    
    # Overrides for F&F settlement
    mock_ff = None
    reimbursements = []
    other_deductions = []
    if ff or any(k in custom_context for k in ['salary_month_days', 'salary_worked_days', 'salary_proportional', 'leave_encashment_days', 'leave_encashment_amount', 'bonus_arrears', 'gratuity_amount', 'notice_shortfall_days', 'notice_shortfall_amount', 'salary_advance_outstanding', 'bond_penalty', 'tds_deduction', 'total_earnings', 'total_deductions', 'net_payable', 'reimbursements_json', 'other_deductions_json']):
        ff_overrides = {}
        # Simple numeric fields
        for field in ['salary_month_days', 'salary_worked_days', 'leave_encash_days']:
            if field in custom_context:
                ff_overrides[field] = Decimal(str(custom_context[field]))
        
        # Decimal fields
        decimal_fields = [
            'salary_proportional', 'leave_encashment_days', 'leave_encashment_amount',
            'bonus_arrears', 'gratuity_amount', 'notice_shortfall_days', 'notice_shortfall_amount',
            'salary_advance_outstanding', 'bond_penalty', 'tds_deduction',
            'total_earnings', 'total_deductions', 'net_payable'
        ]
        for field in decimal_fields:
            if field in custom_context:
                ff_overrides[field] = Decimal(str(custom_context[field]))
        
        mock_ff = MockObj(ff, **ff_overrides)
        reimbursements = custom_context.get('reimbursements_json', ff.reimbursements_json if ff else [])
        other_deductions = custom_context.get('other_deductions_json', ff.other_deductions_json if ff else [])

    # Special handling for experience letter tenure
    start_date = mock_employee.joining_date
    end_date = mock_exit_request.last_working_day
    
    years = end_date.year - start_date.year
    months = end_date.month - start_date.month
    if end_date.day < start_date.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
        
    tenure_parts = []
    if years > 0:
        tenure_parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        tenure_parts.append(f"{months} month{'s' if months > 1 else ''}")
    if not tenure_parts:
        tenure_parts.append("0 months")
    tenure_str = " and ".join(tenure_parts)
    
    # Prorated salary components calculation for Final Month Payslip
    salary_struct = employee.salary_structures.order_by('-effective_from').first()
    
    if mock_ff:
        m_days = mock_ff.salary_month_days if hasattr(mock_ff, 'salary_month_days') else Decimal(30)
        w_days = mock_ff.salary_worked_days if hasattr(mock_ff, 'salary_worked_days') else Decimal(0)
        ratio = w_days / Decimal(m_days) if m_days else Decimal(1)
    else:
        ratio = Decimal(1)
        
    prorated = {
        'basic': (Decimal(salary_struct.basic) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'hra': (Decimal(salary_struct.hra) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'conveyance': (Decimal(salary_struct.conveyance) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'medical': (Decimal(salary_struct.medical) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'special': (Decimal(salary_struct.special) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'monthly_bonus': (Decimal(salary_struct.monthly_bonus) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'pf': (Decimal(salary_struct.pf) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'professional_tax': (Decimal(salary_struct.professional_tax) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
        'tds': (Decimal(salary_struct.tds) * ratio).quantize(Decimal('0.01')) if salary_struct else Decimal(0),
    }
    
    # Allow custom_context overrides for prorated components
    for comp in prorated.keys():
        if comp in custom_context:
            prorated[comp] = Decimal(str(custom_context[comp]))
            
    gross_prorated = sum([
        prorated['basic'], prorated['hra'], prorated['conveyance'],
        prorated['medical'], prorated['special'], prorated['monthly_bonus']
    ])
    deductions_prorated = sum([
        prorated['pf'], prorated['professional_tax'], prorated['tds']
    ])
    net_prorated = gross_prorated - deductions_prorated
    
    # Standard signatory & company info
    company_name = custom_context.get('company_name', getattr(settings, 'COMPANY_NAME', 'MTLV Solutions Private Limited'))
    company_address = custom_context.get('company_address', getattr(settings, 'COMPANY_ADDRESS', 'HR Division, Secure Enterprise Operations, India'))
    signatory_name = custom_context.get('signatory_name', getattr(settings, 'LETTER_SIGNATORY_NAME', 'Head of HR Operations'))
    signatory_designation = custom_context.get('signatory_designation', getattr(settings, 'LETTER_SIGNATORY_DESIGNATION', 'Authorized Signatory'))
    
    date_str = custom_context.get('date', datetime.date.today().strftime('%d %B %Y'))

    context = {
        'employee': mock_employee,
        'exit_request': mock_exit_request,
        'ff': mock_ff,
        'reimbursements': reimbursements,
        'other_deductions': other_deductions,
        'today': datetime.date.today(),
        'date': date_str,
        'tenure_str': tenure_str,
        'salary_struct': salary_struct,
        'prorated': prorated,
        'gross_prorated': gross_prorated,
        'deductions_prorated': deductions_prorated,
        'net_prorated': net_prorated,
        'company_name': company_name,
        'company_address': company_address,
        'signatory_name': signatory_name,
        'signatory_designation': signatory_designation,
    }
    return context

def render_exit_letter_to_html(exit_request, doc_type, custom_context=None):
    context = get_exit_letter_context(exit_request, custom_context)
    
    template_name_map = {
        'RELIEVING_LETTER': 'exit/pdf_relieving_letter.html',
        'EXPERIENCE_LETTER': 'exit/pdf_experience_letter.html',
        'NOTICE_LETTER': 'exit/pdf_notice_letter.html',
        'NOC_LETTER': 'exit/pdf_noc_letter.html',
        'FF_SETTLEMENT_LETTER': 'exit/pdf_ff_settlement_letter.html',
        'FF_SALARY_SLIP': 'exit/pdf_ff_salary_slip.html',
    }
    template_name = template_name_map.get(doc_type)
    if not template_name:
        raise ValueError(f"Unknown exit document type: {doc_type}")
        
    template_obj = LetterTemplate.objects.filter(name=doc_type).first()
    if template_obj:
        html_string = Template(template_obj.html_content).render(Context(context))
    else:
        html_string = render_to_string(template_name, context)
        
    return html_string

def generate_exit_document_pdf(exit_request, doc_type, custom_context=None, user=None):
    html_string = render_exit_letter_to_html(exit_request, doc_type, custom_context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    filename = f"{doc_type.lower()}_{exit_request.employee.emp_id}_{int(datetime.datetime.now().timestamp())}.pdf"
    content_file = ContentFile(pdf_bytes, name=filename)
    
    doc = EmployeeDocument.objects.create(
        employee=exit_request.employee,
        doc_type=doc_type,
        file=content_file,
        uploaded_by=user
    )
    return doc

def generate_relieving_letter(exit_request, user=None, custom_context=None):
    return generate_exit_document_pdf(exit_request, 'RELIEVING_LETTER', custom_context, user)

def generate_experience_letter(exit_request, user=None, custom_context=None):
    return generate_exit_document_pdf(exit_request, 'EXPERIENCE_LETTER', custom_context, user)

def generate_notice_letter(exit_request, user=None, custom_context=None):
    return generate_exit_document_pdf(exit_request, 'NOTICE_LETTER', custom_context, user)

def generate_noc_letter(exit_request, user=None, custom_context=None):
    return generate_exit_document_pdf(exit_request, 'NOC_LETTER', custom_context, user)

def generate_ff_settlement_letter(exit_request, user=None, custom_context=None):
    return generate_exit_document_pdf(exit_request, 'FF_SETTLEMENT_LETTER', custom_context, user)

def generate_ff_salary_slip(exit_request, user=None, custom_context=None):
    return generate_exit_document_pdf(exit_request, 'FF_SALARY_SLIP', custom_context, user)
