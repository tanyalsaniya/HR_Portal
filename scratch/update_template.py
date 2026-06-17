import os
import django

import sys
# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from employee_onboarding.models import LetterTemplate

def update_ff_settlement_template():
    file_path = os.path.join('templates', 'exit', 'pdf_ff_settlement_letter.html')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        template_obj = LetterTemplate.objects.filter(name='FF_SETTLEMENT_LETTER').first()
        if template_obj:
            template_obj.html_content = html_content
            template_obj.save()
            print("Successfully updated the FF_SETTLEMENT_LETTER template in the database.")
        else:
            LetterTemplate.objects.create(
                name='FF_SETTLEMENT_LETTER',
                title='F&F Settlement Letter Template',
                html_content=html_content,
                allow_hr_edit=False
            )
            print("Successfully created the FF_SETTLEMENT_LETTER template in the database.")
    else:
        print("Template file not found.")

if __name__ == "__main__":
    update_ff_settlement_template()
