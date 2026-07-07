# apps/common/utils.py
import datetime

def generate_employee_id():
    """
    Generates a unique employee ID in the format: EMP-YYYY-XXXX
    where YYYY is the current year and XXXX is a sequential 4-digit number.
    """
    from django.apps import apps
    Employee = apps.get_model('employee_onboarding', 'Employee')
    year = datetime.date.today().year
    prefix = f"EMP-{year}-"
    
    # Query for the last generated ID of the current year
    last_emp = Employee.objects.filter(emp_id__startswith=prefix).order_by('-emp_id').first()
    if last_emp:
        try:
            last_sequence = int(last_emp.emp_id.split('-')[-1])
            new_sequence = last_sequence + 1
        except (ValueError, IndexError):
            new_sequence = 1
    else:
        new_sequence = 1
        
    return f"{prefix}{new_sequence:04d}"

def generate_payslip_number(year, month, is_dismissed=False):
    """
    Generates a unique payslip number in the format: PS-YYYY-MM-XXXX
    where YYYY is the target year, MM is the target month, and XXXX is a sequential 4-digit number.
    """
    from django.apps import apps
    if is_dismissed:
        SalarySlip = apps.get_model('salary', 'DismissedSalarySlip')
    else:
        SalarySlip = apps.get_model('salary', 'SalarySlip')
        
    month_str = f"{int(month):02d}"
    prefix = f"PS-{year}-{month_str}-"
    
    last_slip = SalarySlip.objects.filter(payslip_no__startswith=prefix).order_by('-payslip_no').first()
    if last_slip:
        try:
            payslip_str = last_slip.payslip_no.replace("-D", "")
            last_sequence = int(payslip_str.split('-')[-1])
            new_sequence = last_sequence + 1
        except (ValueError, IndexError):
            new_sequence = 1
    else:
        new_sequence = 1
        
    return f"{prefix}{new_sequence:04d}"

def generate_certificate_number():
    """
    Generates a unique certificate number in the format: CERT-YYYY-XXXXXX
    where YYYY is the current year and XXXXXX is a sequential 6-digit number.
    """
    from django.apps import apps
    Student = apps.get_model('student_certificate', 'Student')
    year = datetime.date.today().year
    prefix = f"CERT-{year}-"
    
    last_student = Student.objects.filter(cert_no__startswith=prefix).order_by('-cert_no').first()
    if last_student:
        try:
            last_sequence = int(last_student.cert_no.split('-')[-1])
            new_sequence = last_sequence + 1
        except (ValueError, IndexError):
            new_sequence = 1
    else:
        new_sequence = 1
        
    return f"{prefix}{new_sequence:06d}"
