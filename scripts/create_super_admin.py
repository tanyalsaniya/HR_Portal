# scripts/create_super_admin.py
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_super_admin():
    User = get_user_model()
    username = os.getenv('SUPERADMIN_EMAIL', 'admin@company.com')
    password = os.getenv('SUPERADMIN_PASSWORD', 'admin123')
    
    if not User.objects.filter(email=username).exists():
        print(f"Creating superuser {username}...")
        User.objects.create_superuser(email=username, password=password, username=username)
        print("Superuser created successfully.")
    else:
        print(f"Superuser {username} already exists.")

if __name__ == '__main__':
    create_super_admin()
