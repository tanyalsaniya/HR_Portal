import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from salary.models import SalaryStructure, SalarySlip
print("SalaryStructure count:", SalaryStructure.objects.count())
print("SalarySlip count:", SalarySlip.objects.count())
for s in SalaryStructure.objects.all()[:5]:
    try:
        print("Structure id:", s.id, "basic:", s.basic)
    except Exception as e:
        print("Structure id:", s.id, "Error basic:", e)
