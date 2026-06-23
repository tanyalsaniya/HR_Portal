# apps/notifications/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from roles.models import Role
from notifications.models import Notification, BitrixSyncLog
from notifications.tasks import check_salary_structure_missing, check_document_completion, check_salary_increment_reminders

User = get_user_model()

class NotificationModelsAndAPITests(APITestCase):
    def setUp(self):
        # Create roles
        self.admin_role = Role.objects.create(name="Admin", code="ADMIN")
        self.hr_role = Role.objects.create(name="HR", code="HR")
        
        # Create users
        self.admin_user = User.objects.create_user(
            username="admin_test",
            password="adminpassword",
            email="admin@mtlv.com",
            role=self.admin_role
        )
        self.hr_user = User.objects.create_user(
            username="hr_test",
            password="hrpassword",
            email="hr@mtlv.com",
            role=self.hr_role
        )

    def test_notification_creation_and_choices(self):
        # Test INFO notification
        notif = Notification.objects.create(
            recipient=self.hr_user,
            notif_type='INFO',
            message="Test Info Notification",
            link="/employees/1/"
        )
        self.assertEqual(notif.notif_type, 'INFO')
        self.assertFalse(notif.is_read)
        self.assertEqual(str(notif), f"Notification for {self.hr_user.username} - Read: False")

        # Test URGENT notification
        notif_urgent = Notification.objects.create(
            recipient=self.admin_user,
            notif_type='URGENT',
            message="Urgent Review",
            link="/increment/1/"
        )
        self.assertEqual(notif_urgent.notif_type, 'URGENT')

    def test_notification_feed_api(self):
        # Authenticate HR User
        self.client.login(username="hr_test", password="hrpassword")
        # Direct token login simulation
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.hr_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Create some notifications
        notif = Notification.objects.create(
            recipient=self.hr_user,
            notif_type='WARNING',
            message="First warning",
            link="/employees/2/"
        )
        
        # Fetch notifications
        response = self.client.get('/api/notifications/feed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle list vs paginated list
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['message'], "First warning")

        # Mark read
        mark_read_url = f"/api/notifications/feed/{notif.id}/mark-read/"
        resp_mark = self.client.post(mark_read_url)
        self.assertEqual(resp_mark.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

        # Create another and mark all read
        notif2 = Notification.objects.create(
            recipient=self.hr_user,
            notif_type='INFO',
            message="Second warning"
        )
        resp_all = self.client.post('/api/notifications/feed/mark-all-read/')
        self.assertEqual(resp_all.status_code, status.HTTP_200_OK)
        notif2.refresh_from_db()
        self.assertTrue(notif2.is_read)
