# apps/student_certificate/services.py
import datetime
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from weasyprint import HTML
from django.template.loader import render_to_string
from rules import STUDENT_FEES_WARNING_SUBJECT, STUDENT_FEES_WARNING_BODY
from .models import Student

def generate_student_certificate_pdf(student, user=None):
    """
    Generates a student certificate PDF depending on the cert_type.
    Saves PDF file in Student model and updates status.
    """
    templates = {
        'INTERNSHIP_CERT': 'certificate/pdf_internship_certificate.html',
        'TRAINING_CERT': 'certificate/pdf_training_certificate.html',
        'PROJECT_CERT': 'certificate/pdf_project_certificate.html',
    }
    
    template_name = templates.get(student.cert_type, 'certificate/pdf_internship_certificate.html')
    
    context = {
        'student': student,
        'today': datetime.date.today(),
        'company_name': 'MTLV Solutions Private Limited'
    }
    
    html_string = render_to_string(template_name, context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    filename = f"cert_{student.cert_no}.pdf"
    student.cert_pdf.save(filename, ContentFile(pdf_bytes), save=False)
    
    # Mark student as Completed if Active
    if student.status == 'ACTIVE':
        student.status = 'COMPLETED'
        
    student.save()
    
    # Trigger notification (bell log will pick it up or we can log explicitly)
    return student

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
