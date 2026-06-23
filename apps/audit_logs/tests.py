from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import datetime

from roles.models import Role, Permission
from employee_onboarding.models import Department
from audit_logs.models import AuditLog

User = get_user_model()

class AuditLogsTestCase(APITestCase):
    def setUp(self):
        # Create permissions
        self.perm_audit_read = Permission.objects.create(codename='audit.read', name='Read Audit Logs')
        
        # Create Admin Role & User
        self.role_admin = Role.objects.create(code='ADMIN', name='Admin', is_active=True)
        self.role_admin.permissions.add(self.perm_audit_read)
        
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='password123',
            role=self.role_admin
        )
        
        # Create non-admin role and user
        self.role_user = Role.objects.create(code='USER', name='User', is_active=True)
        self.normal_user = User.objects.create_user(
            username='user_test',
            email='user@test.com',
            password='password123',
            role=self.role_user
        )

    def test_automatic_model_tracking(self):
        self.client.force_authenticate(user=self.admin_user)
        
        # Action: Create a department
        dept = Department.objects.create(name='Marketing')
        
        # Assert: A log entry was created
        log = AuditLog.objects.filter(action='DEPARTMENT_CREATED').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.module_name, 'employee_onboarding')
        self.assertEqual(log.new_values['name'], 'Marketing')
        
        # Action: Update the department
        dept.name = 'Finance'
        dept.save()
        
        # Assert: Update log entry created
        log_update = AuditLog.objects.filter(action='DEPARTMENT_UPDATED').first()
        self.assertIsNotNone(log_update)
        self.assertEqual(log_update.old_values['name'], 'Marketing')
        self.assertEqual(log_update.new_values['name'], 'Finance')

    def test_log_immutability(self):
        log = AuditLog.objects.create(
            action='TEST_ACTION',
            description='Test description'
        )
        
        # Assert: Editing the log raises PermissionError
        log.description = 'Updated description'
        with self.assertRaises(PermissionError):
            log.save()

    def test_log_deletion_security(self):
        log = AuditLog.objects.create(
            action='TEST_ACTION',
            description='Test description'
        )
        
        # Assert: Deleting log without superuser raises PermissionError
        with self.assertRaises(PermissionError):
            log.delete()

    def test_admin_only_access(self):
        # Authenticate as normal user
        self.client.force_authenticate(user=self.normal_user)
        url = reverse('auditlog-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Authenticate as admin user
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_endpoints(self):
        self.client.force_authenticate(user=self.admin_user)
        
        # Create some logs to export
        AuditLog.objects.create(action='TEST_EXPORT_1', description='Desc 1')
        AuditLog.objects.create(action='TEST_EXPORT_2', description='Desc 2')
        
        # Export CSV
        url_csv = reverse('auditlog-export-logs') + '?export_format=csv'
        response = self.client.get(url_csv)
        print("CSV RESPONSE:", response.status_code, response.content[:200])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('TEST_EXPORT_1', response.content.decode())

        # Export Excel
        url_excel = reverse('auditlog-export-logs') + '?export_format=excel'
        response = self.client.get(url_excel)
        print("EXCEL RESPONSE:", response.status_code, response.content[:200])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # Export PDF
        url_pdf = reverse('auditlog-export-logs') + '?export_format=pdf'
        response = self.client.get(url_pdf)
        print("PDF RESPONSE:", response.status_code, response.content[:200])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
