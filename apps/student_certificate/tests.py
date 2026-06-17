from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import datetime

from employee_onboarding.models import Department
from roles.models import Role
from .models import Course, Student, StudentCertificate
from .services import generate_student_certificate_pdf

User = get_user_model()

class StudentCertificateTestCase(APITestCase):
    def setUp(self):
        # Create Admin Role & User
        self.role_admin, _ = Role.objects.get_or_create(code='ADMIN', name='Admin', is_active=True)
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='password123',
            role=self.role_admin
        )
        self.client.force_authenticate(user=self.admin_user)
        
        # Create Department
        self.dept = Department.objects.create(name='Technology')
        
        # Create Course
        self.course = Course.objects.create(
            course_name='Frontend (React JS)',
            default_duration='6 months',
            skills_list=['HTML5', 'CSS3', 'JavaScript']
        )
        
        # Create Students (Male and Female)
        self.male_student = Student.objects.create(
            name='Tushar Kumar',
            email='tushar@test.com',
            institute='Institute A',
            course_at_institute='B.Tech CSE',
            student_type='INTERN',
            program_name='Summer Intern 2025',
            department=self.dept,
            joining_date=datetime.date(2025, 1, 1),
            completion_date=datetime.date(2025, 7, 1),
            total_fees=0,
            gender='MALE',
            father_name='Parveen Kumar',
            address='near Kheda, Haryana',
            enrolled_course=self.course
        )
        
        self.female_student = Student.objects.create(
            name='Palak Sharma',
            email='palak@test.com',
            institute='Institute B',
            course_at_institute='B.Tech IT',
            student_type='TRAINEE',
            program_name='Summer Intern 2025',
            department=self.dept,
            joining_date=datetime.date(2025, 1, 1),
            completion_date=datetime.date(2025, 7, 1),
            total_fees=0,
            gender='FEMALE',
            father_name='Ramesh Sharma',
            address='Chandigarh',
            enrolled_course=self.course
        )

    def test_enrollment_details_endpoint(self):
        url = reverse('student-enrollment-details', kwargs={'pk': self.male_student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['student_name'], 'Tushar Kumar')
        self.assertEqual(data['s_o_d_o'], 'S/O')
        self.assertEqual(data['he_she'], 'he')
        self.assertEqual(data['his_her'], 'his')
        self.assertIn('HTML5', data['skills'])

    from unittest.mock import patch

    @patch('student_certificate.services.generate_student_certificate_pdf')
    def test_certificate_creation_endpoint_sequential(self, mock_generate):
        # Create first certificate
        url = '/api/student/certificates/'
        payload = {
            'student': self.male_student.id,
            'course': self.course.id,
            'skill_ratings': {'HTML5': 'Excellent', 'CSS3': 'Good', 'JavaScript': 'Excellent'},
            'show_dates': True,
            'issue_date': '2025-08-01',
            'place': 'Mohali',
            'cert_content': 'This is to certify that...'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cert1 = StudentCertificate.objects.get(id=response.json()['id'])
        self.assertEqual(cert1.serial_no, 'DHUB|25|250') # starts at 250 as coded for empty
        
        # Create second certificate
        payload2 = {
            'student': self.female_student.id,
            'course': self.course.id,
            'skill_ratings': {'HTML5': 'Excellent', 'CSS3': 'Excellent', 'JavaScript': 'Excellent'},
            'show_dates': False,
            'issue_date': '2025-08-02',
            'place': 'Mohali',
            'cert_content': 'This is to certify that...'
        }
        response2 = self.client.post(url, payload2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        cert2 = StudentCertificate.objects.get(id=response2.json()['id'])
        self.assertEqual(cert2.serial_no, 'DHUB|25|251') # increments sequentially
        
        # Verify generation service was called twice
        self.assertEqual(mock_generate.call_count, 2)


    def test_pdf_generation_logic(self):
        cert = StudentCertificate.objects.create(
            student=self.male_student,
            course=self.course,
            skill_ratings={'HTML5': 'Excellent'},
            show_dates=True,
            issue_date=datetime.date.today(),
            serial_no='DHUB|25|999',
            cert_content='This is to certify that...',
            place='Mohali'
        )
        generate_student_certificate_pdf(cert)
        
        # Check PDF is saved
        self.assertTrue(cert.pdf_file)
        self.assertTrue(cert.student.cert_pdf)
        self.assertEqual(cert.student.status, 'COMPLETED')
