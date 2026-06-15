# apps/employee_onboarding/tests.py
import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from roles.models import Role, Permission
from employee_onboarding.models import Department, Employee, EmployeeDocument
from notifications.tasks import run_daily_onboarding_pipeline

User = get_user_model()

class OnboardingModuleTests(APITestCase):

    def setUp(self):
        # Create master roles and permissions
        self.admin_role = Role.objects.create(name="Admin", code="ADMIN")
        self.hr_role = Role.objects.create(name="HR", code="HR")
        self.recruiter_role = Role.objects.create(name="Recruiter", code="RECRUITER")
        
        # Add basic permissions
        self.read_perm = Permission.objects.create(name="Read Onboarding", codename="onboarding.read", module="onboarding")
        self.create_perm = Permission.objects.create(name="Create Onboarding", codename="onboarding.create", module="onboarding")
        self.update_perm = Permission.objects.create(name="Update Onboarding", codename="onboarding.update", module="onboarding")
        
        self.hr_role.permissions.add(self.read_perm, self.create_perm, self.update_perm)
        self.recruiter_role.permissions.add(self.read_perm)
        
        # Create users
        self.admin_user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password", role=self.admin_role)
        self.hr_user = User.objects.create_user(username="hr", email="hr@test.com", password="password", role=self.hr_role)
        self.rec_user = User.objects.create_user(username="recruiter", email="rec@test.com", password="password", role=self.recruiter_role)
        
        # Create department
        self.dept = Department.objects.create(name="Engineering")

    def test_employee_id_generation(self):
        # Onboard employee
        emp = Employee.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@test.com",
            phone="9876543210",
            dob=datetime.date(1995, 5, 10),
            gender="MALE",
            address_line1="123 Street",
            city="Mumbai",
            state="MH",
            pin_code="400001",
            department=self.dept,
            designation="Software Engineer",
            employment_type="FULL_TIME",
            joining_date=datetime.date(2026, 6, 1)
        )
        # Verify ID format EMP-YYYY-XXXX (where YYYY matches joining date year 2026)
        self.assertEqual(emp.emp_id, "EMP-2026-0001")
        
        # Onboard second employee in same year
        emp2 = Employee.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@test.com",
            phone="9876543211",
            dob=datetime.date(1996, 6, 11),
            gender="FEMALE",
            address_line1="456 Avenue",
            city="Mumbai",
            state="MH",
            pin_code="400001",
            department=self.dept,
            designation="Product Manager",
            employment_type="FULL_TIME",
            joining_date=datetime.date(2026, 6, 2)
        )
        self.assertEqual(emp2.emp_id, "EMP-2026-0002")

    def test_15_day_graduation_pipeline(self):
        today = datetime.date.today()
        
        # Employee 1: Joined 16 days ago (should graduate)
        emp1 = Employee.objects.create(
            first_name="Alice", last_name="Grad", email="alice@test.com", phone="9876543212",
            dob=datetime.date(1990, 1, 1), gender="FEMALE", address_line1="Address 1",
            city="Delhi", state="DL", pin_code="110001", department=self.dept,
            designation="Architect", employment_type="FULL_TIME",
            joining_date=today - datetime.timedelta(days=15), onboarding_complete=False
        )

        # Employee 2: Joined 14 days ago (should NOT graduate)
        emp2 = Employee.objects.create(
            first_name="Bob", last_name="NoGrad", email="bob@test.com", phone="9876543213",
            dob=datetime.date(1991, 1, 1), gender="MALE", address_line1="Address 2",
            city="Delhi", state="DL", pin_code="110001", department=self.dept,
            designation="Engineer", employment_type="FULL_TIME",
            joining_date=today - datetime.timedelta(days=14), onboarding_complete=False
        )
        
        # Run daily pipeline task
        run_daily_onboarding_pipeline()
        
        # Reload from DB
        emp1.refresh_from_db()
        emp2.refresh_from_db()
        
        self.assertTrue(emp1.onboarding_complete)
        self.assertFalse(emp2.onboarding_complete)

    def test_immutable_email_validation(self):
        # Authenticate HR
        self.client.force_authenticate(user=self.hr_user)
        
        # Create employee
        emp = Employee.objects.create(
            first_name="Tom", last_name="Jones", email="tom@test.com", phone="9876543214",
            dob=datetime.date(1990, 1, 1), gender="MALE", address_line1="Address",
            city="Delhi", state="DL", pin_code="110001", department=self.dept,
            designation="Dev", employment_type="FULL_TIME", joining_date=datetime.date.today()
        )
        
        # Try to update email via API
        url = reverse('employee-detail', args=[emp.id])
        data = {
            "first_name": "Tom",
            "last_name": "Jones",
            "email": "updated@test.com", # modified email
            "phone": "9876543214",
            "dob": "1990-01-01",
            "gender": "MALE",
            "address_line1": "Address",
            "city": "Delhi",
            "state": "DL",
            "pin_code": "110001",
            "department": self.dept.id,
            "designation": "Dev",
            "employment_type": "FULL_TIME",
            "notice_period_days": 30,
            "emergency_contact_name": "Emergency",
            "emergency_relationship": "PARENT",
            "emergency_phone": "9876543210"
        }
        res = self.client.put(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_secure_document_streaming_permissions(self):
        # Onboard employee
        emp = Employee.objects.create(
            first_name="Secure", last_name="Doc", email="secure@test.com", phone="9876543215",
            dob=datetime.date(1990, 1, 1), gender="MALE", address_line1="Address",
            city="Delhi", state="DL", pin_code="110001", department=self.dept,
            designation="Dev", employment_type="FULL_TIME", joining_date=datetime.date.today()
        )
        # Create document
        doc = EmployeeDocument.objects.create(
            employee=emp,
            doc_type="RESUME",
            file="employees/EMP-2026-0003/docs/test_file.pdf"
        )
        
        # Try to access without auth (should return 401/403)
        url = reverse('secure_doc_serve', args=[emp.emp_id, 'test_file.pdf'])
        self.client.force_authenticate(user=None)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to access as unauthorized role (Recruiter has no admin/hr clearance)
        self.client.force_authenticate(user=self.rec_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Access as Admin (should allow but file doesn't exist on disk, should return 404 instead of 403)
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
