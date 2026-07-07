import requests
import json

webhook_url = "https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/crm.item.list.json"
entity_type_id = 1044

# Ongoing stages
included_stages = {
    'DT1044_20:CLIENT',      # Inquiry/Lead stage
    'DT1044_20:UC_8CP2UP',   # Application Submitted
    'DT1044_20:UC_QXBN3E',   # Under Review
    'DT1044_20:UC_10M2QN',   # Enrollment Started
    'DT1044_20:UC_26OISW',   # Course Starting Soon
}

active_students = []
start = 0

print("Connecting to Bitrix24 CRM with permission-granted webhook...")

while True:
    params = {
        'entityTypeId': entity_type_id,
        'start': start,
    }
    
    response = requests.post(webhook_url, json=params, timeout=15)
    if response.status_code != 200:
        print(f"Error calling Bitrix API: {response.status_code} - {response.text}")
        break
        
    data = response.json()
    items = data.get('result', {}).get('items', [])
    if not items:
        break
        
    for item in items:
        stage = item.get('stageId', '')
        # Exclude completed/failed or those containing FAIL
        if 'FAIL' in stage.upper() or 'UC_69T3IT' in stage:
            continue
            
        if stage in included_stages:
            active_students.append({
                'id': item.get('id'),
                'name': (item.get('title') or '').strip(),
                'email': item.get('ufCrm6_1761731565702') or '',
                'phone': item.get('ufCrm6_1761731546152') or '',
                'course_id': item.get('ufCrm6_1761731874888'),
                'start_date': (item.get('ufCrm6_1761734468448') or '')[:10],
                'completion_date': (item.get('ufCrm6_1761735481170') or '')[:10],
                'father_name': item.get('ufCrm6_1761731958409') or '',
                'institute': item.get('ufCrm6_1761732176981') or '',
                'total_fees': item.get('ufCrm6_1761732340679') or '0',
                'stage': stage,
            })
            
    next_offset = data.get('next')
    if next_offset:
        start = next_offset
    else:
        break

print(f"\nSuccessfully fetched {len(active_students)} active students from Bitrix24:\n")
print(f"{'No.':<4} | {'Name':<22} | {'Email':<30} | {'Phone':<12} | {'Stage':<25}")
print("-" * 105)
for idx, s in enumerate(active_students, 1):
    print(f"{idx:<4} | {s['name']:<22} | {s['email']:<30} | {s['phone']:<12} | {s['stage']:<25}")
