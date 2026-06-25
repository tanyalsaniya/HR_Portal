import os
import django

import sys
# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from employee_onboarding.models import LetterTemplate

def update_templates():
    templates_to_update = [
        ('FF_SETTLEMENT_LETTER', 'F&F Settlement Letter Template', 'pdf_ff_settlement_letter.html', 'exit'),
        ('RELIEVING_LETTER', 'Relieving Letter Template', 'pdf_relieving_letter.html', 'exit'),
        ('EXPERIENCE_LETTER', 'Experience Letter Template', 'pdf_experience_letter.html', 'exit'),
        ('FF_SALARY_SLIP', 'Final Month Payslip Template', 'pdf_ff_salary_slip.html', 'exit'),
        ('OFFER_LETTER', 'Offer Letter Template', 'pdf_offer_letter.html', 'onboarding'),
        ('APPOINTMENT_LETTER', 'Appointment Letter Template', 'pdf_appointment_letter.html', 'onboarding'),
        ('BOND_LETTER', 'Employment Bond Template', 'pdf_bond_letter.html', 'onboarding'),
    ]
    for name, title, filename, folder in templates_to_update:
        file_path = os.path.join('templates', folder, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            template_obj = LetterTemplate.objects.filter(name=name).first()
            if template_obj:
                template_obj.html_content = html_content
                template_obj.save()
                print(f"Successfully updated the {name} template in the database.")
            else:
                LetterTemplate.objects.create(
                    name=name,
                    title=title,
                    html_content=html_content,
                    allow_hr_edit=False
                )
                print(f"Successfully created the {name} template in the database.")
        else:
            print(f"Template file {filename} not found.")

if __name__ == "__main__":
    update_templates()
