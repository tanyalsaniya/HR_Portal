import os
import sys
import django

sys.path.append(r"c:\Users\Pc\Documents\Python\HR_Portal")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
hr_user = User.objects.filter(email="hr@company.com").first()
if hr_user:
    print(f"User: {hr_user.email}")
    print(f"Role: {hr_user.role}")
    if hr_user.role:
        print("Permissions:")
        for perm in hr_user.role.permissions.all():
            print(f"  - {perm.codename}")
else:
    print("HR User not found.")
