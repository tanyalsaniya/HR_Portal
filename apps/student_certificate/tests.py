# apps/student_certificate/tests.py
import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from employee_onboarding.models import Department
from .models import Student, Course, StudentCertificate
from .utils import calculate_completed_duration

User = get_user_model()

class StudentCertificateValidationTests(TestCase):
    def setUp(self):
        # Create department
        self.dept = Department.objects.create(name="Engineering")
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='testpassword'
        )
        
        # Authenticate client via simplejwt
        self.token = AccessToken.for_user(self.admin_user)
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.token}'
        
        # Create course
        self.course = Course.objects.create(
            course_name="Python Backend",
            default_duration="6 Months",
            skills_list=["Django", "REST Framework"]
        )
        
        # Create student with completion date in the future (early student)
        self.joining_date = datetime.date.today() - datetime.timedelta(days=60) # 2 months ago
        self.completion_date = datetime.date.today() + datetime.timedelta(days=120) # 4 months from now
        
        self.student = Student.objects.create(
            name="Alice Smith",
            email="alice@test.com",
            institute="University of Test",
            course_at_institute="CS",
            student_type="TRAINEE",
            program_name="Internship",
            department=self.dept,
            joining_date=self.joining_date,
            completion_date=self.completion_date,
            enrolled_course=self.course,
            gender="FEMALE",
            father_name="Bob Smith",
            address="123 Test Street"
        )

    def test_calculate_completed_duration(self):
        # 60 days is approx 2 months
        duration = calculate_completed_duration(self.joining_date, datetime.date.today())
        self.assertIn("Month", duration)
        self.assertIn("Completed", duration)

    def test_generate_early_certificate_validation(self):
        # 1. Generate certificate without override -> warning expected
        response = self.client.post(
            f"/api/student/students/{self.student.id}/generate-certificate/",
            data={},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("warning", response.json())
        self.assertTrue(response.json().get("requires_override"))
        
        # 2. Generate certificate with override but without reason -> error expected
        response = self.client.post(
            f"/api/student/students/{self.student.id}/generate-certificate/",
            data={"confirm_override": True},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        
        # 3. Generate certificate with override and reason -> success expected
        reason = "Needed early for university credits submission"
        response = self.client.post(
            f"/api/student/students/{self.student.id}/generate-certificate/",
            data={
                "confirm_override": True,
                "early_generation_reason": reason
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
        
        # Verify database record
        cert = StudentCertificate.objects.filter(student=self.student).first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.early_generation_reason, reason)
        self.assertIsNotNone(cert.calculated_completed_duration)
        self.assertEqual(cert.generated_by, self.admin_user)
        
        # Verify content shows completed duration instead of full course duration
        self.assertNotIn("6 Months", cert.cert_content)
        self.assertIn(cert.calculated_completed_duration, cert.cert_content)
