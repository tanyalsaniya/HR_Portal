import requests
from datetime import datetime, date

webhook_url = "https://devexhub.bitrix24.in/rest/1/vpas32pze4n94125/crm.item.list.json"
entity_type_id = 1044

active_students = []
start = 0
today = date.today()

print(f"Connecting to Bitrix24 CRM to fetch active students...")

while True:
    params = {
        'entityTypeId': entity_type_id,
        'start': start,
        'filter': {
            'STATUS': 'ACTIVE',
        },
        'select': ['*', 'uf_*']
    }
    
    response = requests.post(webhook_url, json=params, timeout=15)
    if response.status_code != 200:
        print(f"Error calling Bitrix API: {response.status_code} - {response.text}")
        break
        
    data = response.json()
    result = data.get('result', [])
    if not result:
        break
        
    for item in result:
        has_student_fields = (
            item.get('UF_COMPLETION_DATE') or 
            item.get('UF_JOINING_DATE') or 
            item.get('UF_COURSE_NAME') or
            item.get('UF_INSTITUTE') or
            item.get('TITLE') or
            item.get('NAME')
        )
        
        has_employee_fields = (
            item.get('WORK_EMAIL') or 
            item.get('WORK_PHONE') or
            item.get('UF_EMPLOYMENT_DATE') or
            (item.get('PERSONAL_BIRTHDAY') and 
             not (item.get('UF_JOINING_DATE') or item.get('UF_COURSE_NAME')))
        )
        
        if has_employee_fields and not (item.get('UF_COURSE_NAME') or item.get('UF_INSTITUTE')):
            continue
            
        if not has_student_fields:
            continue
            
        completion_date_str = item.get('UF_COMPLETION_DATE') or item.get('completion_date')
        
        try:
            if completion_date_str:
                completion_date = datetime.strptime(
                    completion_date_str.split('T')[0] if 'T' in completion_date_str else completion_date_str, 
                    '%Y-%m-%d'
                ).date()
                
                if completion_date > today:
                    active_students.append(item)
            else:
                active_students.append(item)
        except (ValueError, TypeError, AttributeError):
            active_students.append(item)
            
    next_start = data.get('next')
    if next_start:
        start = next_start
    else:
        break

print(f"\nFetched {len(active_students)} active students from Bitrix24:")
print("=" * 60)
for idx, s in enumerate(active_students, 1):
    name = s.get('NAME') or s.get('TITLE') or 'Unknown'
    email = s.get('EMAIL') or s.get('UF_EMAIL') or 'N/A'
    course = s.get('UF_COURSE_NAME') or s.get('UF_COURSE') or 'N/A'
    completion = s.get('UF_COMPLETION_DATE') or 'N/A'
    if completion != 'N/A' and 'T' in completion:
        completion = completion.split('T')[0]
    print(f"{idx}. Name: {name:<25} | Email: {email:<30} | Course: {course:<30} | Completion: {completion}")
