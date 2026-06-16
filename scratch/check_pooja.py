import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from employee_onboarding.models import Employee

for emp in Employee.objects.all():
    print(f"ID: {emp.id}, Name: {emp.name!r}, First: {emp.first_name!r}, Last: {emp.last_name!r}")
