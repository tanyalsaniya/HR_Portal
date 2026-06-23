import os
import requests
import json

webhook = "https://devexhub.bitrix24.in/rest/1/vpas32pze4n94125"
url = f"{webhook}/department.get.json"
try:
    res = requests.get(url, timeout=10)
    print("Status code:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        print(json.dumps(data, indent=2))
    else:
        print("Response text:", res.text)
except Exception as e:
    print("Error:", e)
