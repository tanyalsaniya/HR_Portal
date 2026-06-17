# apps/student_certificate/services.py
import datetime
import os
import re
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from weasyprint import HTML
from django.template.loader import render_to_string
from rules import STUDENT_FEES_WARNING_SUBJECT, STUDENT_FEES_WARNING_BODY
from .models import Student, StudentCertificate

def generate_student_certificate_pdf(certificate):
    """
    Generates a student certificate PDF depending on the cert_type.
    Saves PDF file in StudentCertificate model and updates Student status.
    """
    student = certificate.student
    gender = student.gender
    
    # Pronoun resolution
    if gender == 'MALE':
        he_she = "he"
        his_her = "his"
    elif gender == 'FEMALE':
        he_she = "she"
        his_her = "her"
    else:
        he_she = "he/she"
        his_her = "his/her"
        
    bg_image_path = os.path.join(settings.BASE_DIR, 'apps', 'student_certificate', 'media', 'certificate (1).png')
    
    # Convert windows path for URI standard in WeasyPrint
    bg_path = bg_image_path.replace('\\', '/')
    if not bg_path.startswith('/'):
        bg_path = '/' + bg_path
        
    cert_content_text = certificate.cert_content or ""
    # Convert double asterisks to bold tag
    html_content = cert_content_text.replace('\n', '<br>')
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
    
    performance_heading = f"{his_her.capitalize()} Performance Given as Below"
    
    context = {
        'certificate': certificate,
        'bg_image_path': bg_path,
        'cert_content_html': html_content,
        'performance_heading': performance_heading,
        'he_she': he_she,
        'his_her': his_her,
        'skill_ratings': certificate.skill_ratings,
    }
    
    html_string = render_to_string('certificate/pdf_certificate_template.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    filename = f"cert_{certificate.serial_no.replace('|', '_')}.pdf"
    certificate.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
    certificate.save()
    
    # Backward compatibility with student's legacy cert_pdf field
    student.cert_pdf = certificate.pdf_file
    if student.status == 'ACTIVE':
        student.status = 'COMPLETED'
    student.save()
    
    return certificate

def send_fee_warning_email(installment):
    """
    Sends a soft, professional warning email to the student about overdue installment.
    """
    student = installment.student
    subject = STUDENT_FEES_WARNING_SUBJECT
    body = STUDENT_FEES_WARNING_BODY.format(
        student_name=student.name,
        installment_number=installment.installment_number,
        amount=installment.amount,
        due_date=installment.due_date.strftime("%d %B %Y")
    )
    
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        fail_silently=False
    )
    return True

