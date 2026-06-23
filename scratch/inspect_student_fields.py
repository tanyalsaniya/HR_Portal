import requests
import json

url = 'https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/crm.item.list.json'
stages = ['DT1044_20:CLIENT', 'DT1044_20:UC_8CP2UP', 'DT1044_20:UC_QXBN3E', 'DT1044_20:UC_10M2QN', 'DT1044_20:UC_26OISW']
params = {'entityTypeId': 1044, 'filter': {'stageId': stages}}
r = requests.post(url, json=params)
items = r.json().get('result', {}).get('items', [])

if items:
    print(json.dumps(items[0], indent=2))
else:
    print("No items found.")
