# apps/employee_onboarding/services.py
import os
import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.template import Template, Context
from weasyprint import HTML
from .models import EmployeeDocument, LetterTemplate

def render_letter_to_html(employee, doc_type, custom_context=None):
    """
    Renders the letter template (from DB or fallback HTML file) to a string using custom context.
    """
    context = get_letter_context(employee, custom_context)
    
    template_name_map = {
        'OFFER_LETTER': 'onboarding/pdf_offer_letter.html',
        'APPOINTMENT_LETTER': 'onboarding/pdf_appointment_letter.html',
        'BOND_LETTER': 'onboarding/pdf_bond_letter.html',
    }
    template_name = template_name_map.get(doc_type, 'onboarding/pdf_offer_letter.html')
    
    # Check if a database template exists
    template_obj = LetterTemplate.objects.filter(name=doc_type).first()
    if template_obj:
        html_string = Template(template_obj.html_content).render(Context(context))
    else:
        # Render HTML template to string
        html_string = render_to_string(template_name, context)
        
    return html_string

def generate_document_pdf(employee, doc_type, template_name, context, user=None):
    """
    Renders an HTML template with context, generates a PDF using WeasyPrint,
    saves the PDF to the media folder, and logs it as an EmployeeDocument.
    """
    # Check if a database template exists
    template_obj = LetterTemplate.objects.filter(name=doc_type).first()
    if template_obj:
        html_string = Template(template_obj.html_content).render(Context(context))
    else:
        # Render HTML template to string
        html_string = render_to_string(template_name, context)
    
    # Generate PDF bytes via WeasyPrint
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    # Prepare File content
    filename = f"{doc_type.lower()}_{employee.emp_id}_{int(datetime.datetime.now().timestamp())}.pdf"
    content_file = ContentFile(pdf_bytes, name=filename)
    
    # Create EmployeeDocument record
    doc = EmployeeDocument.objects.create(
        bitrix_user_id=employee.id,
        doc_type=doc_type,
        file=content_file,
        uploaded_by=user
    )
    return doc


def get_letter_context(employee, custom_context=None):
    salary_struct = employee.salary_structures.order_by('-effective_from').first()
    
    custom_context = custom_context or {}
    
    # Format today's date
    date_str = custom_context.get('date', datetime.date.today().strftime('%d %B %Y'))
    
    # Create customizable employee dict
    custom_emp = {
        'first_name': custom_context.get('first_name', employee.first_name),
        'last_name': custom_context.get('last_name', employee.last_name),
        'emp_id': custom_context.get('emp_id', employee.emp_id),
        'designation': custom_context.get('designation', employee.designation),
        'joining_date': custom_context.get('joining_date', employee.joining_date.strftime('%Y-%m-%d') if employee.joining_date else ''),
        'notice_period_days': custom_context.get('notice_period_days', employee.notice_period_days),
        'bond_period_months': custom_context.get('bond_period_months', employee.bond_period_months),
        'address_line1': custom_context.get('address_line1', employee.address_line1),
        'city': custom_context.get('city', employee.city),
        'state': custom_context.get('state', employee.state),
        'get_state_display': employee.get_state_display(),
    }
    
    # Support direct variable fallback in template like name, address, designation, date
    context = {
        'employee': custom_emp,
        'today': datetime.date.today(),
        'date': date_str,
        'bond_date': date_str,
        'employee_name': f"{custom_emp['first_name']} {custom_emp['last_name']}",
        'name': f"{custom_emp['first_name']} {custom_emp['last_name']}",
        'address': f"{custom_emp['address_line1']}, {custom_emp['city']}",
        'employee_address': f"{custom_emp['address_line1']}, {custom_emp['city']}",
        'designation': custom_emp['designation'],
        'joining_date': custom_emp['joining_date'],
        'company_name': custom_context.get('company_name', getattr(settings, 'COMPANY_NAME', 'Devex Hub Pvt Ltd.')),
        'company_address': custom_context.get('company_address', getattr(settings, 'COMPANY_ADDRESS', 'Plot No D-254, Fourth Floor, Phase 8A, Industrial Area, Mohali')),
        'signatory_name': custom_context.get('signatory_name', getattr(settings, 'LETTER_SIGNATORY_NAME', 'Head of HR Operations')),
        'signatory_designation': custom_context.get('signatory_designation', getattr(settings, 'LETTER_SIGNATORY_DESIGNATION', 'Authorized Signatory')),
    }
    
    # Populate salary details safely
    basic = custom_context.get('basic', str(getattr(salary_struct, 'basic', '0.00')) if salary_struct else '0.00')
    hra = custom_context.get('hra', str(getattr(salary_struct, 'hra', '0.00')) if salary_struct else '0.00')
    conveyance = custom_context.get('conveyance', str(getattr(salary_struct, 'conveyance', '0.00')) if salary_struct else '0.00')
    medical = custom_context.get('medical', str(getattr(salary_struct, 'medical', '0.00')) if salary_struct else '0.00')
    special = custom_context.get('special', str(getattr(salary_struct, 'special', '0.00')) if salary_struct else '0.00')
    monthly_bonus = custom_context.get('monthly_bonus', str(getattr(salary_struct, 'monthly_bonus', '0.00')) if salary_struct else '0.00')
    
    pf = custom_context.get('pf', str(getattr(salary_struct, 'pf_contribution', getattr(salary_struct, 'pf', '0.00'))) if salary_struct else '0.00')
    pt = custom_context.get('professional_tax', str(getattr(salary_struct, 'professional_tax', '200.00')) if salary_struct else '200.00')
    tds = custom_context.get('tds', str(getattr(salary_struct, 'tds', '0.00')) if salary_struct else '0.00')
    
    gross_salary = custom_context.get('gross_salary', str(getattr(salary_struct, 'gross_salary', '0.00')) if salary_struct else '0.00')
    total_deductions = custom_context.get('total_deductions', str(getattr(salary_struct, 'total_deductions', '0.00')) if salary_struct else '0.00')
    net_salary = custom_context.get('net_salary', str(getattr(salary_struct, 'net_salary', '0.00')) if salary_struct else '0.00')
    
    # Extra breakup fields requested
    ctc = custom_context.get('ctc', str(getattr(salary_struct, 'gross_salary', '0.00')) if salary_struct else '0.00')
    esi_employer = custom_context.get('esi_employer', '0.00')
    pf_employer = custom_context.get('pf_employer', '0.00')
    pf_employee = custom_context.get('pf_employee', pf)
    esi_employee = custom_context.get('esi_employee', str(getattr(salary_struct, 'esi', '0.00')) if salary_struct else '0.00')
    lwf = custom_context.get('lwf', str(getattr(salary_struct, 'labour_welfare_fund', '0.00')) if salary_struct else '0.00')
    in_hand = custom_context.get('in_hand', net_salary)
    
    context.update({
        'salary': salary_struct if salary_struct else True,
        'basic': basic,
        'hra': hra,
        'conveyance': conveyance,
        'medical': medical,
        'special': special,
        'monthly_bonus': monthly_bonus,
        'pf': pf,
        'professional_tax': pt,
        'tds': tds,
        'gross_salary': gross_salary,
        'total_deductions': total_deductions,
        'net_salary': net_salary,
        
        'ctc': ctc,
        'esi_employer': esi_employer,
        'pf_employer': pf_employer,
        'pf_employee': pf_employee,
        'esi_employee': esi_employee,
        'lwf': lwf,
        'in_hand': in_hand,
        
        'bond_period': custom_emp['bond_period_months'],
        'probation_period': '3',
        'notice_period': custom_emp['notice_period_days'],
        'penalty_salary': 'two months’ salary',
        
        'other_allowances': getattr(salary_struct, 'other_allowances', []),
        'other_deductions': [
            {'label': 'ESI', 'amount': getattr(salary_struct, 'esi', 0)},
            {'label': 'Labour Welfare Fund', 'amount': getattr(salary_struct, 'labour_welfare_fund', 0)},
            {'label': 'Other Deductions', 'amount': getattr(salary_struct, 'other_deductions', 0)},
        ] if salary_struct else [],
    })
    
    return context

def generate_offer_letter(employee, user=None, custom_context=None):
    context = get_letter_context(employee, custom_context)
    return generate_document_pdf(
        employee=employee,
        doc_type='OFFER_LETTER',
        template_name='onboarding/pdf_offer_letter.html',
        context=context,
        user=user
    )

def generate_appointment_letter(employee, user=None, custom_context=None):
    context = get_letter_context(employee, custom_context)
    return generate_document_pdf(
        employee=employee,
        doc_type='APPOINTMENT_LETTER',
        template_name='onboarding/pdf_appointment_letter.html',
        context=context,
        user=user
    )

def generate_bond_letter(employee, user=None, custom_context=None):
    bond_period = employee.bond_period_months
    if custom_context and 'bond_period_months' in custom_context:
        bond_period = int(custom_context['bond_period_months'] or 0)
        
    if not bond_period:
        raise ValueError("Employee does not have a bond period defined.")
        
    context = get_letter_context(employee, custom_context)
    context['bond_period'] = bond_period
    return generate_document_pdf(
        employee=employee,
        doc_type='BOND_LETTER',
        template_name='onboarding/pdf_bond_letter.html',
        context=context,
        user=user
    )
