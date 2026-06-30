# apps/salary/services.py
import datetime
import io
import zipfile
from decimal import Decimal
from django.core.files.base import ContentFile
from django.conf import settings
from django.db.models import Q
from .models import SalaryStructure, SalarySlip, SalaryIncrementApproval


def get_latest_prior_slip(bitrix_user_id, month, year):
    """
    Returns the most recently imported SalarySlip for the given employee
    that is strictly BEFORE the specified month/year, in reverse chrono order.

    Returns None if no prior slip exists (new employee / no imports yet).

    Examples
    --------
    Selected = April 2026, imported = Jan 2026 + Feb 2026  → returns Feb 2026
    Selected = April 2026, imported = Jan 2026 only         → returns Jan 2026
    Selected = April 2026, no prior imports                 → returns None
    """
    return (
        SalarySlip.objects
        .filter(bitrix_user_id=str(bitrix_user_id))
        .filter(Q(year__lt=year) | Q(year=year, month__lt=month))
        .order_by('-year', '-month')
        .first()
    )


def generate_payslip_pdf_bytes(salary_slip, override_month=None, override_year=None):
    """
    Renders a payslip to PDF bytes WITHOUT saving anything to DB.

    Useful for carry-forward months where no actual SalarySlip record exists:
    we temporarily set month/year on the slip object only in memory.

    Args:
        salary_slip:    A real or temporary SalarySlip-like object with salary data.
        override_month: If provided, use this month on the rendered PDF instead of
                        salary_slip.month (carry-forward use case).
        override_year:  If provided, use this year on the rendered PDF.

    Returns:
        (pdf_bytes, filename) tuple — nothing written to DB or disk.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML
    from common.bitrix_client import BitrixClient, BitrixEmployeeMock

    user_data = BitrixClient.get_user_detail(salary_slip.bitrix_user_id)
    employee = BitrixEmployeeMock(user_data) if user_data else None

    from salary.models import EmployeeBankDetail
    bank_detail = EmployeeBankDetail.objects.filter(bitrix_user_id=salary_slip.bitrix_user_id).first()
    bank_acc = ""
    if bank_detail and bank_detail.bank_account_no:
        bank_acc = bank_detail.bank_account_no
    elif salary_slip.bank_account_no:
        bank_acc = salary_slip.bank_account_no
    elif employee:
        bank_acc = getattr(employee, 'bank_account', '') or ''

    bank_account_masked = f"XXXXXX{bank_acc[-4:]}" if len(bank_acc) >= 4 else "XXXXXX"
    net_pay_words = num_to_words(salary_slip.net_salary)

    # For carry-forward: display the requested month/year on the slip, not the source month
    display_month = override_month if override_month is not None else salary_slip.month
    display_year = override_year if override_year is not None else salary_slip.year

    context = {
        'slip': salary_slip,
        'display_month': display_month,
        'display_year': display_year,
        'employee': employee,
        'bank_account_masked': bank_account_masked,
        'net_pay_words': net_pay_words,
        'company_name': getattr(settings, 'COMPANY_NAME', 'Devex Hub Pvt Ltd.'),
        'today': datetime.date.today(),
    }

    html_string = render_to_string('salary/pdf_payslip.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()

    emp_id = employee.emp_id if employee else salary_slip.bitrix_user_id
    filename = f"payslip_{emp_id}_{display_month}_{display_year}.pdf"
    return pdf_bytes, filename

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
    from common.bitrix_client import BitrixClient, BitrixEmployeeMock
    
    user_data = BitrixClient.get_user_detail(salary_slip.bitrix_user_id)
    employee = BitrixEmployeeMock(user_data) if user_data else None
    
    from salary.models import EmployeeBankDetail
    bank_detail = EmployeeBankDetail.objects.filter(bitrix_user_id=salary_slip.bitrix_user_id).first()
    if bank_detail:
        if bank_detail.bank_account_no:
            salary_slip.bank_account_no = bank_detail.bank_account_no
        if bank_detail.bank_name:
            salary_slip.bank_name = bank_detail.bank_name
        salary_slip.save(update_fields=['bank_account_no', 'bank_name'])
    
    bank_acc = salary_slip.bank_account_no or (employee.bank_account if employee else "")
    bank_account_masked = f"XXXXXX{bank_acc[-4:]}" if len(bank_acc) >= 4 else "XXXXXX"
    
    net_pay_words = num_to_words(salary_slip.net_salary)
    
    context = {
        'slip': salary_slip,
        'employee': employee,
        'bank_account_masked': bank_account_masked,
        'net_pay_words': net_pay_words,
        'company_name': getattr(settings, 'COMPANY_NAME', 'Devex Hub Pvt Ltd.'),
        'today': datetime.date.today()
    }
    
    html_string = render_to_string('salary/pdf_payslip.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    emp_id = employee.emp_id if employee else salary_slip.bitrix_user_id
    filename = f"payslip_{emp_id}_{salary_slip.month}_{salary_slip.year}.pdf"
    salary_slip.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    return salary_slip


def generate_increment_letter_pdf(approval, user=None):
    """
    Renders increment approval letter and saves it to the SalaryIncrementApproval record.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML
    from common.bitrix_client import BitrixClient, BitrixEmployeeMock
    
    user_data = BitrixClient.get_user_detail(approval.bitrix_user_id)
    employee = BitrixEmployeeMock(user_data) if user_data else None
    
    context = {
        'approval': approval,
        'employee': employee,
        'company_name': 'Devex Hub Pvt Ltd.',
        'today': datetime.date.today()
    }
    
    html_string = render_to_string('salary/pdf_increment_letter.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    emp_id = employee.emp_id if employee else approval.bitrix_user_id
    filename = f"increment_letter_{emp_id}_{int(datetime.datetime.now().timestamp())}.pdf"
    approval.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    return approval


def generate_payslips_zip(slips, zip_type='employee'):
    """
    Generates a ZIP archive containing PDFs of the provided salary slips.
    zip_type options: 'employee' (multi-month single employee), 'bulk' (bulk month all employees)
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML
    from common.bitrix_client import BitrixClient, BitrixEmployeeMock
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for slip in slips:
            user_data = BitrixClient.get_user_detail(slip.bitrix_user_id)
            employee = BitrixEmployeeMock(user_data) if user_data else None
            
            from salary.models import EmployeeBankDetail
            bank_detail = EmployeeBankDetail.objects.filter(bitrix_user_id=slip.bitrix_user_id).first()
            if bank_detail:
                if bank_detail.bank_account_no:
                    slip.bank_account_no = bank_detail.bank_account_no
                if bank_detail.bank_name:
                    slip.bank_name = bank_detail.bank_name
            
            bank_acc = slip.bank_account_no or (employee.bank_account if employee else "")
            bank_account_masked = f"XXXXXX{bank_acc[-4:]}" if len(bank_acc) >= 4 else "XXXXXX"
            
            net_pay_words = num_to_words(slip.net_salary)
            
            context = {
                'slip': slip,
                'employee': employee,
                'bank_account_masked': bank_account_masked,
                'net_pay_words': net_pay_words,
                'company_name': getattr(settings, 'COMPANY_NAME', 'Devex Hub Pvt Ltd.'),
                'today': datetime.date.today()
            }
            
            html_string = render_to_string('salary/pdf_payslip.html', context)
            pdf_bytes = HTML(string=html_string).write_pdf()
            
            months_abbr = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            month_name = months_abbr[slip.month]
            
            first_name = employee.first_name if employee else "Employee"
            last_name = employee.last_name if employee else slip.bitrix_user_id
            emp_id = employee.emp_id if employee else slip.bitrix_user_id
            
            if zip_type == 'employee':
                # Structure: "EmpName_EmpID/Apr_2026.pdf"
                folder_name = f"{first_name}_{last_name}_{emp_id}".replace(" ", "_")
                file_path = f"{folder_name}/{month_name}_{slip.year}.pdf"
            else:
                # Structure: "Apr_2026/EmpID_EmpName.pdf"
                folder_name = f"{month_name}_{slip.year}"
                emp_name = f"{first_name}_{last_name}".replace(" ", "_")
                file_path = f"{folder_name}/{emp_id}_{emp_name}.pdf"
                
            zip_file.writestr(file_path, pdf_bytes)
            
    zip_buffer.seek(0)
    return zip_buffer.getvalue()