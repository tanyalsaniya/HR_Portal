import requests
import json

url = 'https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/crm.item.fields.json'
params = {'entityTypeId': 1044}
r = requests.post(url, json=params)
fields = r.json().get('result', {}).get('fields', {})

# Print keys and their descriptions
for name, field in fields.items():
    if name.startswith('ufCrm6_'):
        print(f"{name}: {field.get('title')} ({field.get('type')})")
        items = field.get('items')
        if items:
            print("  Items:")
            for item in items:
                print(f"    - {item.get('id')}: {item.get('value')}")
