import urllib.request
import urllib.error
import json

url = "http://127.0.0.1:8000/api/student/bitrix-active/"
try:
    response = urllib.request.urlopen(url)
    print("Status:", response.status)
    print("Body:", response.read().decode('utf-8')[:200])
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
    print("Body:", e.read().decode('utf-8')[:500])
except Exception as e:
    print("Error:", e)
