# scratch/test_webhook_task.py
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'apps'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from employee_onboarding.tasks import process_bitrix_webhook_task
from employee_onboarding.models import SyncedEmployee

# Let's delete any existing synced employees with John Doe email for test clean-start
SyncedEmployee.objects.filter(email='john.doe@example.com').delete()

payload = {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "1234567890",
    "designation": "Software Engineer"
}

print("Running process_bitrix_webhook_task with payload:", payload)
result = process_bitrix_webhook_task(payload)
print("Result of task:", result)

# Now inspect database state
synced = SyncedEmployee.objects.filter(email='john.doe@example.com').first()
if synced:
    print("Found SyncedEmployee in database!")
    print("ID:", synced.bitrix_user_id)
    print("First Name:", synced.first_name)
    print("Last Name:", synced.last_name)
    print("Email:", synced.email)
    print("Designation:", synced.designation)
    print("Phone:", synced.phone)
else:
    print("NO SyncedEmployee found in database for email 'john.doe@example.com'!")
