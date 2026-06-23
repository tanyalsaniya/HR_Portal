from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import datetime
from unittest.mock import patch

from employee_onboarding.models import Department
from roles.models import Role
from student_certificate.models import Course, Student, StudentCertificate
from student_certificate.services import generate_student_certificate_pdf

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

    def test_student_list_filters_active_only(self):
        completed_student = Student.objects.create(
            name='Rahul Verma',
            email='rahul@test.com',
            institute='Institute C',
            course_at_institute='B.Tech ECE',
            student_type='PROJECT_STUDENT',
            program_name='Winter Program',
            department=self.dept,
            joining_date=datetime.date(2025, 2, 1),
            completion_date=datetime.date(2025, 8, 1),
            total_fees=0,
            gender='MALE',
            father_name='Suresh Verma',
            address='Delhi',
            enrolled_course=self.course,
            status='COMPLETED'
        )

        url = '/api/student/students/?status=ACTIVE'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payload = response.json()
        results = payload['results'] if isinstance(payload, dict) and 'results' in payload else payload
        returned_ids = {item['id'] for item in results}

        self.assertIn(self.male_student.id, returned_ids)
        self.assertIn(self.female_student.id, returned_ids)
        self.assertNotIn(completed_student.id, returned_ids)

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

    @patch('requests.post')
    def test_bitrix_active_students_caching(self, mock_post):
        from unittest.mock import MagicMock
        from django.core.cache import cache

        # Prepare mock response data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': {
                'items': [
                    {
                        'id': '101',
                        'title': 'Test Bitrix Student',
                        'stageId': 'DT1044_20:CLIENT',
                        'ufCrm6_1761731565702': 'test@bitrix.com',
                        'ufCrm6_1761731546152': '1234567890',
                        'ufCrm6_1761731874888': '1',
                        'ufCrm6_1761735340146': '2025-01-01',
                        'ufCrm6_1761735481170': '2025-07-01',
                        'ufCrm6_1761731958409': 'Father Name',
                        'ufCrm6_1761732176981': 'Institute X',
                        'ufCrm6_1761732340679': '15000'
                    }
                ]
            },
            'next': None
        }
        mock_post.return_value = mock_response

        # Clear cache first to ensure a clean state
        cache.delete('bitrix_active_students_list_page_0')

        url = '/api/student/bitrix-active/'
        
        # First call: Should fetch from API and cache
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(mock_post.call_count, 1)
        data1 = response1.json()
        self.assertEqual(data1['count'], 1)
        self.assertEqual(data1['results'][0]['name'], 'Test Bitrix Student')

        # Second call: Should return from cache (post call count remains 1)
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(mock_post.call_count, 1)  # No extra call to post
        
        # Third call: with refresh=true, should bypass cache and call api again (post call count becomes 2)
        response3 = self.client.get(url + '?refresh=true')
        self.assertEqual(response3.status_code, 200)
        self.assertEqual(mock_post.call_count, 2)

