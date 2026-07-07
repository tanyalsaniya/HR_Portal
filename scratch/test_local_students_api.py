import urllib.request
import urllib.error
import json

def test_students():
    # 1. Login to get token
    login_url = "http://127.0.0.1:8000/api/auth/login/"
    login_data = json.dumps({
        "username": "admin@company.com",
        "password": "admin123"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        login_url,
        data=login_data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            token = json.loads(res_body).get("access")
            print("Login successful.")
            
        # 2. Query active students
        students_url = "http://127.0.0.1:8000/api/student/bitrix-active/?start=0&limit=10"
        req_students = urllib.request.Request(
            students_url,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req_students) as response_students:
            res_body_students = response_students.read().decode('utf-8')
            res_json = json.loads(res_body_students)
            print("API returned status OK.")
            print(f"Total students count: {res_json.get('total')}")
            print(f"Results list size: {len(res_json.get('results', []))}")
            if res_json.get('results'):
                print("First student details:")
                print(json.dumps(res_json.get('results')[0], indent=2))
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == '__main__':
    test_students()
