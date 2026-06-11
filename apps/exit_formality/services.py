# apps/exit_formality/services.py
import datetime
from employee_onboarding.services import generate_document_pdf

def generate_relieving_letter(exit_request, user=None):
    """
    Generates a Relieving Letter PDF.
    """
    employee = exit_request.employee
    context = {
        'employee': employee,
        'exit_request': exit_request,
        'today': datetime.date.today(),
        'company_name': 'MTLV Solutions Private Limited'
    }
    return generate_document_pdf(
        employee=employee,
        doc_type='RELIEVING_LETTER',
        template_name='exit/pdf_relieving_letter.html',
        context=context,
        user=user
    )

def generate_experience_letter(exit_request, user=None):
    """
    Generates an Experience Letter PDF and calculates service tenure duration.
    """
    employee = exit_request.employee
    tenure_days = (exit_request.last_working_day - employee.joining_date).days
    tenure_years = round(tenure_days / 365.25, 1)
    
    context = {
        'employee': employee,
        'exit_request': exit_request,
        'today': datetime.date.today(),
        'company_name': 'MTLV Solutions Private Limited',
        'tenure_years': tenure_years
    }
    return generate_document_pdf(
        employee=employee,
        doc_type='EXPERIENCE_LETTER',
        template_name='exit/pdf_experience_letter.html',
        context=context,
        user=user
    )

def generate_notice_letter(exit_request, user=None):
    """
    Generates a Notice Period Letter PDF.
    """
    employee = exit_request.employee
    context = {
        'employee': employee,
        'exit_request': exit_request,
        'today': datetime.date.today(),
        'company_name': 'MTLV Solutions Private Limited'
    }
    return generate_document_pdf(
        employee=employee,
        doc_type='NOTICE_LETTER',
        template_name='exit/pdf_notice_letter.html',
        context=context,
        user=user
    )
