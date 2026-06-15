import os
import django
import sys

# Setup django environment
sys.path.append('c:\\Users\\Pc\\Documents\\Python\\HR_Portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import resolve, Resolver404

try:
    match = resolve('/api/auth/login/')
    print("MATCH VIEW:", match.func)
    print("MATCH VIEW NAME:", match.view_name)
    print("MATCH ARGS:", match.args)
    print("MATCH KWARGS:", match.kwargs)
    print("MATCH URL_NAME:", match.url_name)
except Resolver404:
    print("No match found (404)")
except Exception as e:
    print("Error:", e)
