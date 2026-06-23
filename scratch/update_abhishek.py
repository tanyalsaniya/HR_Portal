import django
import os
import sys
import requests

# Add both root and apps folder to Python path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from common.bitrix_client import BitrixClient

def main():
    webhook = BitrixClient.get_webhook_url()
    pk = '296'
    
    # 1. Update CRM Contact
    update_contact_url = f"{webhook}/crm.contact.update"
    contact_payload = {
        'id': pk,
        'fields': {
            'NAME': 'Abhishek',
            'LAST_NAME': 'Sharma',
            'EMAIL': [{'VALUE': 'abhisheksharma@devexhub.in', 'VALUE_TYPE': 'WORK'}],
            'PHONE': [{'VALUE': '9876543210', 'VALUE_TYPE': 'WORK'}],
            'POST': 'Jr. Python Developer',
            'BIRTHDATE': '1995-01-01',
            'ADDRESS': 'Mohali',
            'ADDRESS_CITY': 'Mohali',
            'ADDRESS_PROVINCE': 'Punjab',
            'ADDRESS_POSTAL_CODE': '160055'
        }
    }
    
    print("Updating CRM Contact...")
    res1 = requests.post(update_contact_url, json=contact_payload, timeout=10)
    print("CRM Contact Update Status:", res1.status_code)
    print("Response:", res1.text)
    
    # 2. Update User Profile
    update_user_url = f"{webhook}/user.update.json"
    user_payload = {
        'ID': pk,
        'NAME': 'Abhishek',
        'LAST_NAME': 'Sharma',
        'EMAIL': 'abhisheksharma@devexhub.in',
        'PERSONAL_MOBILE': '9876543210',
        'WORK_POSITION': 'Jr. Python Developer',
        'PERSONAL_BIRTHDAY': '1995-01-01',
        'PERSONAL_CITY': 'Mohali',
        'PERSONAL_STATE': 'Punjab',
        'PERSONAL_ZIP': '160055',
        'PERSONAL_GENDER': 'M'
    }
    
    print("\nUpdating User Profile...")
    res2 = requests.post(update_user_url, json=user_payload, timeout=10)
    print("User Update Status:", res2.status_code)
    print("Response:", res2.text)
    
    # Clear cache
    print("\nClearing Bitrix cache...")
    BitrixClient.get_all_users(force_refresh=True)
    print("Done!")

if __name__ == '__main__':
    main()
