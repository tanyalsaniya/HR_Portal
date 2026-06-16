import requests
import json

def fetch_users():
    # The API URL provided by you
    api_url = "https://devexhub.bitrix24.in/rest/1/vpas32pze4n94125/user.get.json?ACTIVE=1"
    
    print(f"Sending request to: {api_url}")
    try:
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            users = data.get('result', [])
            print(f"Successfully retrieved {len(users)} active users.")
            
            # Print first 3 users as a preview
            for i, user in enumerate(users[:3]):
                print(f"\n--- User {i+1} ---")
                print(f"ID: {user.get('ID')}")
                print(f"Name: {user.get('NAME')} {user.get('LAST_NAME')}")
                print(f"Email: {user.get('EMAIL')}")
                print(f"Work Position/Designation: {user.get('WORK_POSITION')}")
                print(f"On Board: {'Yes' if user.get('ACTIVE') == 'Y' else 'No'}")
            
            # Save the raw JSON data for review
            output_file = "scratch/bitrix_users_response.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"\nFull response saved to {output_file}")
        else:
            print(f"Failed to fetch data. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    fetch_users()
