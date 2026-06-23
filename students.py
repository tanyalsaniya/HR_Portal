import requests
from datetime import datetime
import pytz

BASE_URL = "https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/"
ENTITY_TYPE_ID = 1044
today = datetime.now(pytz.timezone('Etc/GMT-3')).replace(hour=0, minute=0, second=0, microsecond=0)
print(f"Today's date (API timezone): {today}\n")

def fetch_ongoing_started_students(debug=True):
    start = 0
    ongoing_students = []
    
    while True:
        params = {
            "entityTypeId": ENTITY_TYPE_ID,
            "filter[stageId]": "DT1044_20:UC_%",
            "start": start
        }
        print(f"Fetching page with start={start}...")
        response = requests.get(f"{BASE_URL}crm.item.list.json", params=params)
        data = response.json()
        items = data.get("result", {}).get("items", [])
        
        if debug:
            print(f"Page returned {len(items)} students with UC_ stages.")
        
        for item in items:
            title = item.get("title")
            stage = item.get("stageId")
            start_date_str = item.get("ufCrm6_1761735340146")
            
            # Debug decision log
            if debug:
                print(f"\n--- Checking: {title} (ID: {item['id']}) ---")
                print(f"  Stage: {stage}")
                print(f"  Start Date Raw: {start_date_str}")
            
            if not start_date_str:
                if debug: print("  ❌ Skipped: Start date is empty/null.")
                continue
                
            try:
                # Parse the date (handle the 'Z' or '+03:00' format)
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                if debug: print(f"  Parsed Start Date: {start_date}")
                
                if start_date <= today:
                    if debug: print("  ✅ INCLUDED: Start date is today or in the past.")
                    ongoing_students.append({
                        "id": item["id"],
                        "title": title,
                        "stage": stage,
                        "start_date": start_date_str,
                    })
                else:
                    if debug: print("  ❌ Skipped: Start date is in the future.")
                    
            except Exception as e:
                if debug: print(f"  ❌ Skipped: Date parsing failed - {e}")

        next_start = data.get("next")
        if not next_start:
            break
        start = next_start
        
    return ongoing_students

# Run it
result = fetch_ongoing_started_students(debug=True)
print(f"\n\n✅ FINAL COUNT: {len(result)} ongoing students found.")
for s in result:
    print(f" - {s['title']} (ID: {s['id']})")