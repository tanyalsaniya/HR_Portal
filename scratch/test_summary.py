import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from employee_onboarding.models import Employee

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

client = Client()
client.force_login(admin_user)

emp = Employee.objects.filter(is_deleted=False).first()
if emp:
    print(f"Testing GET /api/salary/employee/{emp.id}/summary")
    response = client.get(f"/api/salary/employee/{emp.id}/summary")
    print("Status code:", response.status_code)
    print("Response data:", response.json() if response.status_code == 200 else response.content)
else:
    print("No active employees found!")
