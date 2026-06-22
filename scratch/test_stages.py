import requests

url = 'https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/crm.item.list.json'
start = 0
stages = {}

while True:
    r = requests.post(url, json={'entityTypeId': 1044, 'start': start})
    data = r.json()
    items = data.get('result', {}).get('items', [])
    for item in items:
        s = item.get('stageId', '')
        if s.startswith('DT1044_20:'):
            stages[s] = stages.get(s, 0) + 1
    next_offset = data.get('next')
    if not next_offset:
        break
    start = next_offset

print("All DT1044_20 stages:", stages)
