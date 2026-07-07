# scratch/test_save.py
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'apps'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from salary.serializers import SalaryStructureSerializer

data = {
    'employee': '116',
    'effective_from': '2026-06-10',
    'gross_salary': '20000',
    'pf_contribution': '1000',
    'esi': '200',
    'labour_welfare_fund': '400',
    'professional_tax': '200',
    'other_deductions': '200'
}

serializer = SalaryStructureSerializer(data=data)
print('Is Valid:', serializer.is_valid())
if not serializer.is_valid():
    print('Errors:', serializer.errors)
else:
    try:
        with transaction.atomic():
            obj = serializer.save()
            print('Saved object ID:', obj.id)
            print('gross_salary:', obj.gross_salary, type(obj.gross_salary))
            print('pf_contribution:', obj.pf_contribution, type(obj.pf_contribution))
            print('esi:', obj.esi, type(obj.esi))
            print('labour_welfare_fund:', obj.labour_welfare_fund, type(obj.labour_welfare_fund))
            print('professional_tax:', obj.professional_tax, type(obj.professional_tax))
            print('other_deductions:', obj.other_deductions, type(obj.other_deductions))
            
            # Now let's print properties
            print('total_deductions:', obj.total_deductions, type(obj.total_deductions))
            print('net_salary:', obj.net_salary, type(obj.net_salary))
            
            # Let's inspect serializer fields and their values
            for field_name, field in serializer.fields.items():
                try:
                    attribute = field.get_attribute(obj)
                    print(f'Field: {field_name}, attribute value: {attribute}, type: {type(attribute)}')
                    if attribute is not None:
                        val = field.to_representation(attribute)
                        print(f'  Represented: {val}')
                except Exception as fe:
                    print(f'  Field {field_name} failed: {fe}')
                    import traceback
                    traceback.print_exc()
            
            transaction.set_rollback(True)
    except Exception as e:
        import traceback
        traceback.print_exc()
