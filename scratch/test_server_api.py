import urllib.request
import urllib.error
import json

def test_api():
    print("Sending requests to http://127.0.0.1:8000...")
    
    # 1. Login (using username key)
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
            res_json = json.loads(res_body)
            print(f"Login Response Status: {response.status}")
            
            token = res_json.get("access")
            print("Login Successful. Token obtained.")
            
        # 2. Get Dashboard data
        dashboard_url = "http://127.0.0.1:8000/api/auth/dashboard/"
        req_dash = urllib.request.Request(
            dashboard_url,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req_dash) as response_dash:
            res_body_dash = response_dash.read().decode('utf-8')
            res_json_dash = json.loads(res_body_dash)
            print(f"Dashboard Response Status: {response_dash.status}")
            print("Dashboard JSON Response:")
            print(json.dumps(res_json_dash, indent=2))
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == '__main__':
    test_api()
