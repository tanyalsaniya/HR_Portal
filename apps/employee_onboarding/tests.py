# apps/employee_onboarding/tests.py
import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase
from roles.models import Role, Permission
from employee_onboarding.models import Department, EmployeeDocument
from common.bitrix_client import BitrixEmployeeMock, BitrixClient

User = get_user_model()

class OnboardingModuleTests(APITestCase):

    def setUp(self):
        # Clear cache to isolate tests
        cache.clear()

        # Create master roles and permissions
        self.admin_role, _ = Role.objects.get_or_create(name="Admin", code="ADMIN")
        self.hr_role, _ = Role.objects.get_or_create(name="HR", code="HR")
        self.recruiter_role, _ = Role.objects.get_or_create(name="Recruiter", code="RECRUITER")
        
        # Add basic permissions
        self.read_perm, _ = Permission.objects.get_or_create(name="Read Onboarding", codename="onboarding.read", module="onboarding")
        self.create_perm, _ = Permission.objects.get_or_create(name="Create Onboarding", codename="onboarding.create", module="onboarding")
        self.update_perm, _ = Permission.objects.get_or_create(name="Update Onboarding", codename="onboarding.update", module="onboarding")
        
        self.hr_role.permissions.add(self.read_perm, self.create_perm, self.update_perm)
        self.recruiter_role.permissions.add(self.read_perm)
        
        # Create users
        self.admin_user, _ = User.objects.get_or_create(username="admin", email="admin@test.com", defaults={"role": self.admin_role, "is_superuser": True, "is_staff": True})
        if not self.admin_user.check_password("password"):
            self.admin_user.set_password("password")
            self.admin_user.save()
            
        self.hr_user, _ = User.objects.get_or_create(username="hr", email="hr@test.com", defaults={"role": self.hr_role})
        if not self.hr_user.check_password("password"):
            self.hr_user.set_password("password")
            self.hr_user.save()
            
        self.rec_user, _ = User.objects.get_or_create(username="recruiter", email="rec@test.com", defaults={"role": self.recruiter_role})
        if not self.rec_user.check_password("password"):
            self.rec_user.set_password("password")
            self.rec_user.save()
            
        # Create department
        self.dept, _ = Department.objects.get_or_create(name="Engineering")

    def test_mock_employee_wrapper(self):
        raw_data = {
            'ID': '10',
            'NAME': 'John',
            'LAST_NAME': 'Doe',
            'EMAIL': 'john.doe@test.com',
            'UF_EMPLOYMENT_DATE': '2026-06-01T00:00:00Z',
            'PERSONAL_BIRTHDAY': '1995-05-10T00:00:00Z',
            'PERSONAL_GENDER': 'M',
            'WORK_POSITION': 'Software Engineer'
        }
        normalized = BitrixClient._normalize_user(raw_data)
        mock_emp = BitrixEmployeeMock(normalized)
        
        self.assertEqual(mock_emp.id, 10)
        self.assertEqual(mock_emp.bitrix_id, "10")
        self.assertEqual(mock_emp.name, "John Doe")
        self.assertEqual(mock_emp.email, "john.doe@test.com")
        self.assertEqual(mock_emp.gender, "Male")
        self.assertEqual(mock_emp.joining_date, datetime.date(2026, 6, 1))
        self.assertEqual(mock_emp.dob, datetime.date(1995, 5, 10))

    @patch('common.bitrix_client.BitrixClient.get_all_users')
    def test_employee_list_view(self, mock_get_all_users):
        mock_get_all_users.return_value = [
            {
                'id': '10',
                'emp_id': 'BITRIX-10',
                'first_name': 'John',
                'last_name': 'Doe',
                'name': 'John Doe',
                'email': 'john.doe@test.com',
                'phone': '9876543210',
                'designation': 'Software Engineer',
                'department_name': 'Engineering',
                'dob': '1995-05-10',
                'gender': 'Male',
                'joining_date': '2026-06-01',
                'status': 'Active',
                'onboarding_complete': True
            }
        ]
        self.client.force_authenticate(user=self.hr_user)
        url = reverse('employee-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['name'], 'John Doe')

    @patch('common.bitrix_client.BitrixClient.get_user_detail')
    def test_employee_retrieve_view(self, mock_get_user_detail):
        mock_get_user_detail.return_value = {
            'id': '10',
            'emp_id': 'BITRIX-10',
            'first_name': 'John',
            'last_name': 'Doe',
            'name': 'John Doe',
            'email': 'john.doe@test.com',
            'phone': '9876543210',
            'designation': 'Software Engineer',
            'department_name': 'Engineering',
            'dob': '1995-05-10',
            'gender': 'Male',
            'joining_date': '2026-06-01',
            'status': 'Active',
            'onboarding_complete': True
        }
        self.client.force_authenticate(user=self.hr_user)
        url = reverse('employee-detail', args=[10])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'John Doe')

    def test_secure_document_streaming_permissions(self):
        # Create document
        doc = EmployeeDocument.objects.create(
            bitrix_user_id="10",
            doc_type="RESUME",
            file="employees/10/docs/test_file.pdf"
        )
        
        # Try to access without auth (should return 401/403)
        url = reverse('secure_doc_serve', args=["BITRIX-10", "test_file.pdf"])
        self.client.force_authenticate(user=None)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to access as recruiter (no admin/hr role permission for streaming)
        self.client.force_authenticate(user=self.rec_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Access as Admin (should allow but file doesn't exist on disk, return 404 instead of 403)
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
