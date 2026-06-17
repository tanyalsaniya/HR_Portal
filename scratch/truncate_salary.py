import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    print("Deleting from salary_salarystructure...")
    cursor.execute("DELETE FROM salary_salarystructure CASCADE;")
    print("Deleted successfully!")
