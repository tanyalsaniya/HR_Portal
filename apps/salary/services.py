# apps/salary/services.py
import datetime
import io
import zipfile
from decimal import Decimal
from django.core.files.base import ContentFile
from django.conf import settings
from .models import SalaryStructure, SalarySlip, SalaryIncrementApproval

def num_to_words(number):
    """
    Converts a number into Indian Rupees words.
    e.g., 50000.50 -> Fifty Thousand Rupees and Fifty Paise Only
    """
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", 
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def get_word(n):
        if n < 20:
            return units[n]
        elif n < 100:
            return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
        elif n < 1000:
            return units[n // 100] + " Hundred" + (" and " + get_word(n % 100) if n % 100 != 0 else "")
        elif n < 100000: # Lakh
            return get_word(n // 1000) + " Thousand" + (" " + get_word(n % 1000) if n % 1000 != 0 else "")
        elif n < 10000000: # Crore
            return get_word(n // 100000) + " Lakh" + (" " + get_word(n % 100000) if n % 100000 != 0 else "")
        else:
            return get_word(n // 10000000) + " Crore" + (" " + get_word(n % 10000000) if n % 10000000 != 0 else "")

    try:
        # separate rupees and paise
        num_str = f"{float(number):.2f}"
        rupees_part, paise_part = map(int, num_str.split('.'))
        
        rupees_words = ""
        if rupees_part == 0:
            rupees_words = "Zero Rupees"
        else:
            rupees_words = get_word(rupees_part) + " Rupees"
            
        paise_words = ""
        if paise_part > 0:
            paise_words = " and " + get_word(paise_part) + " Paise"
            
        return rupees_words + paise_words + " Only"
    except Exception:
        return "Rupees " + str(number)


def generate_payslip_pdf(salary_slip):
    """
    Renders monthly payslip to PDF and saves it to the SalarySlip record.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML
    
    employee = salary_slip.employee
    bank_acc = employee.bank_account or ""
    bank_account_masked = f"XXXXXX{bank_acc[-4:]}" if len(bank_acc) >= 4 else "XXXXXX"
    
    net_pay_words = num_to_words(salary_slip.net_salary)
    
    context = {
        'slip': salary_slip,
        'employee': employee,
        'bank_account_masked': bank_account_masked,
        'net_pay_words': net_pay_words,
        'company_name': getattr(settings, 'COMPANY_NAME', 'MTLV Solutions Private Limited'),
        'today': datetime.date.today()
    }
    
    html_string = render_to_string('salary/pdf_payslip.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    filename = f"payslip_{salary_slip.employee.emp_id}_{salary_slip.month}_{salary_slip.year}.pdf"
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


def generate_payslips_zip(slips, zip_type='employee'):
    """
    Generates a ZIP archive containing PDFs of the provided salary slips.
    zip_type options: 'employee' (multi-month single employee), 'bulk' (bulk month all employees)
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for slip in slips:
            employee = slip.employee
            bank_acc = employee.bank_account or ""
            bank_account_masked = f"XXXXXX{bank_acc[-4:]}" if len(bank_acc) >= 4 else "XXXXXX"
            
            net_pay_words = num_to_words(slip.net_salary)
            
            context = {
                'slip': slip,
                'employee': employee,
                'bank_account_masked': bank_account_masked,
                'net_pay_words': net_pay_words,
                'company_name': getattr(settings, 'COMPANY_NAME', 'MTLV Solutions Private Limited'),
                'today': datetime.date.today()
            }
            
            html_string = render_to_string('salary/pdf_payslip.html', context)
            pdf_bytes = HTML(string=html_string).write_pdf()
            
            months_abbr = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            month_name = months_abbr[slip.month]
            
            if zip_type == 'employee':
                # Structure: "EmpName_EmpID/Apr_2026.pdf"
                folder_name = f"{employee.first_name}_{employee.last_name}_{employee.emp_id}".replace(" ", "_")
                file_path = f"{folder_name}/{month_name}_{slip.year}.pdf"
            else:
                # Structure: "Apr_2026/EmpID_EmpName.pdf"
                folder_name = f"{month_name}_{slip.year}"
                emp_name = f"{employee.first_name}_{employee.last_name}".replace(" ", "_")
                file_path = f"{folder_name}/{employee.emp_id}_{emp_name}.pdf"
                
            zip_file.writestr(file_path, pdf_bytes)
            
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
