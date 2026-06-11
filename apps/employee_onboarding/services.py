# apps/employee_onboarding/services.py
import os
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import EmployeeDocument

def generate_document_pdf(employee, doc_type, template_name, context, user=None):
    """
    Renders an HTML template with context, generates a PDF using WeasyPrint,
    saves the PDF to the media folder, and logs it as an EmployeeDocument.
    """
    # Render HTML template to string
    html_string = render_to_string(template_name, context)
    
    # Generate PDF bytes via WeasyPrint
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    # Prepare File content
    filename = f"{doc_type.lower()}_{employee.emp_id}_{int(datetime.datetime.now().timestamp())}.pdf" if 'datetime' in globals() else f"{doc_type.lower()}_{employee.emp_id}.pdf"
    
    # Fallback to avoid import errors inside strings
    import datetime
    filename = f"{doc_type.lower()}_{employee.emp_id}_{int(datetime.datetime.now().timestamp())}.pdf"
    
    content_file = ContentFile(pdf_bytes, name=filename)
    
    # Create EmployeeDocument record
    doc = EmployeeDocument.objects.create(
        employee=employee,
        doc_type=doc_type,
        file=content_file,
        uploaded_by=user
    )
    return doc

def generate_offer_letter(employee, user=None):
    context = {
        'employee': employee,
        'today': datetime.date.today(),
        'company_name': 'MTLV Solutions Private Limited'
    }
    return generate_document_pdf(
        employee=employee,
        doc_type='OFFER_LETTER',
        template_name='onboarding/pdf_offer_letter.html',
        context=context,
        user=user
    )

def generate_appointment_letter(employee, user=None):
    context = {
        'employee': employee,
        'today': datetime.date.today(),
        'company_name': 'MTLV Solutions Private Limited'
    }
    return generate_document_pdf(
        employee=employee,
        doc_type='APPOINTMENT_LETTER',
        template_name='onboarding/pdf_appointment_letter.html',
        context=context,
        user=user
    )

def generate_bond_letter(employee, user=None):
    if not employee.bond_period_months:
        raise ValueError("Employee does not have a bond period defined.")
    context = {
        'employee': employee,
        'today': datetime.date.today(),
        'company_name': 'MTLV Solutions Private Limited',
        'bond_period': employee.bond_period_months
    }
    return generate_document_pdf(
        employee=employee,
        doc_type='BOND_LETTER',
        template_name='onboarding/pdf_bond_letter.html',
        context=context,
        user=user
    )
