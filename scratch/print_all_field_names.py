import requests
import json

url = 'https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/crm.item.fields.json'
params = {'entityTypeId': 1044}
r = requests.post(url, json=params)
fields = r.json().get('result', {}).get('fields', {})

for name, field in fields.items():
    print(f"{name}: {field.get('title')} ({field.get('type')})")
