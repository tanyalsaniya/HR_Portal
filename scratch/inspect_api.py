import json
import collections

with open(r"C:\Users\Pc\.gemini\antigravity\brain\fc521ec7-6d68-4344-9fe4-00177a7b8c7b\.system_generated\steps\2041\content.md", "r", encoding="utf-8") as f:
    text = f.read()

# Locate the JSON block (skip title and description metadata if any)
header_sep = "---\n\n"
if header_sep in text:
    json_part = text.split(header_sep)[1].strip()
else:
    json_part = text.strip()

data = json.loads(json_part)
items = data.get("result", {}).get("items", [])

print("Total Items Fetched:", len(items))

# 1. Inspect stages
stages = collections.Counter([item.get("stageId") for item in items])
print("\nUnique Stages and Counts:")
for stage, count in stages.most_common():
    print(f" - {stage}: {count}")

# 2. Inspect first item fields
if items:
    print("\nKeys in first item:")
    first = items[0]
    for key, value in list(first.items())[:20]:
        print(f" - {key}: {repr(value)}")
        
    # Let's search for fields related to certificate
    # Usually certificates might be stored in specific fields, let's print if any field mentions certificate
    # Let's check which fields have values that look like 'yes', 'no', dates, or certificate numbers.
    print("\nSearching for potential certificate or status fields (with sample values):")
    for key, value in first.items():
        if key.startswith("ufCrm6_") and value is not None and value != "":
            print(f" - {key}: {repr(value)}")
            
    # Let's see some students who are active/completed
    print("\nSample items:")
    for item in items[:5]:
        print(f"ID: {item.get('id')} | Title: {item.get('title')} | Stage: {item.get('stageId')} | Start: {item.get('ufCrm6_1761734468448')} | End: {item.get('ufCrm6_1761735481170')}")
else:
    print("No items found.")
