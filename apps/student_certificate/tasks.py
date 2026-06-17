# apps/student_certificate/tasks.py
import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from .models import Student

logger = logging.getLogger(__name__)

@shared_task
def send_student_welcome_email(student_id):
    """
    Trigger 22: Sends welcome email to student upon record creation
    """
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return "Student not found."

    recipient_email = student.email
    if not recipient_email:
        return "No email for student."

    subject = f"Welcome to MTLV Training Program – {student.program_name}"
    body = f"""Dear {student.name},

Welcome to the MTLV Training Program! We are excited to have you join us.

Please find your training details below:
- Program Name: {student.program_name}
- Student Type: {student.get_student_type_display()}
- Joining Date: {student.joining_date}
- Completion Date: {student.completion_date}
- Mentor: {student.mentor or 'To be assigned'}
- Institute: {student.institute}

What to expect:
Over the course of your program, you will undergo structured training, work on practical hands-on tasks, and collaborate with experienced mentors to hone your skills.

If you have any questions, feel free to contact the training department.

Best Regards,
HR Team
MTLV
"""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL or 'hr@mtlv.com',
            recipient_list=[recipient_email],
            fail_silently=False
        )
        return "Student welcome email sent successfully."
    except Exception as e:
        logger.error(f"Failed to send student welcome email to {recipient_email}: {e}")
        return f"Failed: {e}"
