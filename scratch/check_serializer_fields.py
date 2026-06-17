import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from employee_onboarding.models import Employee
from employee_onboarding.serializers import EmployeeSerializer

emp = Employee.objects.first()
if emp:
    serializer = EmployeeSerializer(emp)
    print("Keys in serialized Employee:")
    print(serializer.data.keys())
    print("Name field value:", serializer.data.get('name'))
else:
    print("No employees found!")
