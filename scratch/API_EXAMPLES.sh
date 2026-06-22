#!/bin/bash
# API Examples for Active Students Bitrix24 Integration
# Base URL: http://localhost:8000 (adjust for your environment)

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_BASE="http://localhost:8000/api/students"
TOKEN="your-auth-token"  # Replace with actual token if needed

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Bitrix24 Active Students API Examples${NC}"
echo -e "${BLUE}================================================${NC}"

# Example 1: Fetch all active students
echo -e "\n${YELLOW}1. Fetch ALL active students (no pagination)${NC}"
echo "Command:"
echo -e "${GREEN}curl -X GET \"${API_BASE}/active-from-bitrix/\"${NC}"
echo -e "\nResponse: Will return all active, currently enrolled students"
echo "Sample:"
echo '{
  "count": 25,
  "students": [
    {
      "bitrix_id": "1044",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "9876543210",
      "status": "ACTIVE",
      "joining_date": "2024-01-15",
      "completion_date": "2024-07-15",
      "institute": "XYZ Institute",
      "course_name": "Python Development",
      "mentor": "Mentor Name",
      "father_name": "Father Name"
    }
  ]
}'

# Example 2: Fetch with pagination
echo -e "\n${YELLOW}2. Fetch active students WITH pagination (page 1)${NC}"
echo "Command:"
echo -e "${GREEN}curl -X GET \"${API_BASE}/active-from-bitrix/?paginate=true&page_size=50&offset=0\"${NC}"
echo -e "\nResponse: Returns first 50 records with next_offset for pagination"

# Example 3: Fetch next page
echo -e "\n${YELLOW}3. Fetch NEXT page (page 2)${NC}"
echo "Command:"
echo -e "${GREEN}curl -X GET \"${API_BASE}/active-from-bitrix/?paginate=true&page_size=50&offset=50\"${NC}"

# Example 4: Fetch without formatting
echo -e "\n${YELLOW}4. Fetch raw Bitrix data (without formatting)${NC}"
echo "Command:"
echo -e "${GREEN}curl -X GET \"${API_BASE}/active-from-bitrix/?format_data=false\"${NC}"
echo -e "\nResponse: Returns raw Bitrix24 CRM fields (all UF_* custom fields included)"

# Example 5: Sync to database
echo -e "\n${YELLOW}5. SYNC active students to database${NC}"
echo "Command:"
echo -e "${GREEN}curl -X POST \"${API_BASE}/sync-active-from-bitrix/\" \\${NC}"
echo -e "${GREEN}  -H \"Content-Type: application/json\" \\${NC}"
echo -e "${GREEN}  -H \"Authorization: Bearer ${TOKEN}\" \\${NC}"
echo -e "${GREEN}  -d '{${NC}"
echo -e "${GREEN}    \"department_id\": 1,${NC}"
echo -e "${GREEN}    \"created_by_id\": 5,${NC}"
echo -e "${GREEN}    \"auto_enroll_course\": true,${NC}"
echo -e "${GREEN}    \"course_id\": 3${NC}"
echo -e "${GREEN}  }'${NC}"
echo -e "\nResponse: Returns count of created, updated, and skipped records"
echo "Sample Response:"
echo '{
  "message": "Sync completed successfully",
  "created": 12,
  "updated": 3,
  "skipped": 0,
  "total_processed": 15,
  "total_imported": 15
}'

# Example 6: Minimal sync (required fields only)
echo -e "\n${YELLOW}6. SYNC with minimum required fields${NC}"
echo "Command:"
echo -e "${GREEN}curl -X POST \"${API_BASE}/sync-active-from-bitrix/\" \\${NC}"
echo -e "${GREEN}  -H \"Content-Type: application/json\" \\${NC}"
echo -e "${GREEN}  -d '{${NC}"
echo -e "${GREEN}    \"department_id\": 1,${NC}"
echo -e "${GREEN}    \"created_by_id\": 5${NC}"
echo -e "${GREEN}  }'${NC}"
echo -e "\nNote: Without auto_enroll_course, students won't be enrolled in any course"

# Example 7: Using jq for better output formatting
echo -e "\n${YELLOW}7. Fetch and format with jq${NC}"
echo "Command:"
echo -e "${GREEN}curl -s -X GET \"${API_BASE}/active-from-bitrix/?paginate=true&page_size=10&offset=0\" | jq '.students[] | {name, email, course_name}'${NC}"

# Example 8: Filter students by course
echo -e "\n${YELLOW}8. Fetch and filter by course with jq${NC}"
echo "Command:"
echo -e "${GREEN}curl -s -X GET \"${API_BASE}/active-from-bitrix/\" | jq '.students[] | select(.course_name == \"Python Development\")'${NC}"

# Example 9: Export to CSV
echo -e "\n${YELLOW}9. Fetch and export to CSV${NC}"
echo "Command:"
echo -e "${GREEN}curl -s -X GET \"${API_BASE}/active-from-bitrix/\" | jq -r '.students[] | [.name, .email, .phone, .course_name, .joining_date, .completion_date] | @csv' > active_students.csv${NC}"

# Example 10: Count active students
echo -e "\n${YELLOW}10. Count total active students${NC}"
echo "Command:"
echo -e "${GREEN}curl -s -X GET \"${API_BASE}/active-from-bitrix/\" | jq '.count'${NC}"

# Example 11: Using Python requests
echo -e "\n${YELLOW}11. Fetch using Python requests${NC}"
echo -e "${GREEN}import requests${NC}"
echo -e "${GREEN}url = '${API_BASE}/active-from-bitrix/'${NC}"
echo -e "${GREEN}params = {${NC}"
echo -e "${GREEN}    'paginate': 'true',${NC}"
echo -e "${GREEN}    'page_size': 50,${NC}"
echo -e "${GREEN}    'offset': 0${NC}"
echo -e "${GREEN}  }${NC}"
echo -e "${GREEN}response = requests.get(url, params=params)${NC}"
echo -e "${GREEN}students = response.json()['students']${NC}"

# Example 12: Using curl with headers
echo -e "\n${YELLOW}12. Fetch with custom headers${NC}"
echo "Command:"
echo -e "${GREEN}curl -X GET \"${API_BASE}/active-from-bitrix/?paginate=true&page_size=50\" \\${NC}"
echo -e "${GREEN}  -H \"Authorization: Bearer ${TOKEN}\" \\${NC}"
echo -e "${GREEN}  -H \"Accept: application/json\" \\${NC}"
echo -e "${GREEN}  -H \"User-Agent: MyApp/1.0\"${NC}"

# Example 13: Large batch pagination
echo -e "\n${YELLOW}13. Fetch all students with pagination (large dataset)${NC}"
echo -e "${GREEN}#!/bin/bash${NC}"
echo -e "${GREEN}offset=0${NC}"
echo -e "${GREEN}page_size=100${NC}"
echo -e "${GREEN}all_students=()${NC}"
echo -e ""
echo -e "${GREEN}while true; do${NC}"
echo -e "${GREEN}  response=\$(curl -s \"${API_BASE}/active-from-bitrix/?paginate=true&page_size=\${page_size}&offset=\${offset}\")${NC}"
echo -e "${GREEN}  students=\$(echo \$response | jq -r '.students[]')${NC}"
echo -e "${GREEN}  if [ -z \"\$students\" ]; then break; fi${NC}"
echo -e "${GREEN}  offset=\$(echo \$response | jq '.next_offset // empty')${NC}"
echo -e "${GREEN}  if [ -z \"\$offset\" ]; then break; fi${NC}"
echo -e "${GREEN}done${NC}"

# Example 14: Error handling
echo -e "\n${YELLOW}14. Error handling with curl${NC}"
echo "Command:"
echo -e "${GREEN}curl -X POST \"${API_BASE}/sync-active-from-bitrix/\" \\${NC}"
echo -e "${GREEN}  -H \"Content-Type: application/json\" \\${NC}"
echo -e "${GREEN}  -d '{}' \\${NC}"
echo -e "${GREEN}  -w \"\\nStatus: %{http_code}\\n\"${NC}"
echo -e "\nResponse (error):"
echo '{
  "error": "department_id and created_by_id are required"
}'

# Example 15: Successful response codes
echo -e "\n${YELLOW}15. HTTP Status Codes${NC}"
echo "  200 OK - Request successful"
echo "  400 Bad Request - Missing or invalid parameters"
echo "  401 Unauthorized - Missing or invalid authentication"
echo "  403 Forbidden - Insufficient permissions"
echo "  500 Internal Server Error - Server error"

echo -e "\n${BLUE}================================================${NC}"
echo -e "${BLUE}Testing Tips:${NC}"
echo -e "${BLUE}================================================${NC}"
echo "1. Replace 'localhost:8000' with your actual API URL"
echo "2. Replace 'your-auth-token' with actual JWT/API token"
echo "3. Use 'jq' for pretty-printing JSON responses"
echo "4. Use '-v' flag with curl to see request/response headers"
echo "5. Use '-X' flag to specify HTTP method (GET, POST, etc.)"
echo "6. Always include 'Content-Type: application/json' for POST requests"
echo ""
echo -e "${BLUE}Install jq for JSON formatting:${NC}"
echo "  Ubuntu/Debian: sudo apt-get install jq"
echo "  macOS: brew install jq"
echo "  Windows: choco install jq"
echo ""
