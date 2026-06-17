# apps/salary/tests.py
import datetime
import io
import openpyxl
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

# Python 3.14 compatibility patch for django template context copy
from django.template.context import BaseContext
def patch_copy(self):
    dup = self.__class__()
    dup.dicts = self.dicts[:]
    return dup
BaseContext.__copy__ = patch_copy

from roles.models import Role
from employee_onboarding.models import Department
from salary.models import SalaryStructure, SalarySlip, SalaryImportBatch
from common.bitrix_client import BitrixEmployeeMock

User = get_user_model()

class SalaryModuleTests(APITestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        # Setup mock patchers
        self.get_all_users_patcher = patch('common.bitrix_client.BitrixClient.get_all_users')
        self.mock_get_all = self.get_all_users_patcher.start()
        
        self.get_user_detail_patcher = patch('common.bitrix_client.BitrixClient.get_user_detail')
        self.mock_get_detail = self.get_user_detail_patcher.start()

        user_dict = {
            'id': '10',
            'emp_id': 'BITRIX-10',
            'first_name': 'John',
            'last_name': 'Doe',
            'name': 'John Doe',
            'email': 'emp@test.com',
            'phone': '9876543210',
            'designation': 'Software Engineer',
            'department_name': 'Engineering',
            'dob': '1995-05-10',
            'gender': 'Male',
            'joining_date': '2026-06-01',
            'status': 'Active'
        }
        self.mock_get_all.return_value = [user_dict]
        self.mock_get_detail.return_value = user_dict

        self.employee = BitrixEmployeeMock(user_dict)

        # Create roles
        self.admin_role = Role.objects.create(name="Admin", code="ADMIN")
        self.hr_role = Role.objects.create(name="HR", code="HR")
        self.employee_role = Role.objects.create(name="Employee", code="EMPLOYEE")

        # Create users
        self.admin_user = User.objects.create_superuser(
            username="admin@test.com", email="admin@test.com", password="password", role=self.admin_role
        )
        self.hr_user = User.objects.create_user(
            username="hr@test.com", email="hr@test.com", password="password", role=self.hr_role
        )
        self.employee_user = User.objects.create_user(
            username="emp@test.com", email="emp@test.com", password="password", role=self.employee_role
        )

        # Create department
        self.dept = Department.objects.create(name="Engineering")

        # Create salary structure
        self.structure = SalaryStructure.objects.create(
            bitrix_user_id=self.employee.bitrix_id,
            gross_salary=Decimal('87000.00'),
            pf_contribution=Decimal('6000.00'),
            esi=Decimal('0.00'),
            labour_welfare_fund=Decimal('0.00'),
            professional_tax=Decimal('200.00'),
            other_deductions=Decimal('0.00'),
            effective_from=datetime.date(2026, 6, 1)
        )

    def tearDown(self):
        self.get_all_users_patcher.stop()
        self.get_user_detail_patcher.stop()

    def test_admin_salary_export_template(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('salary_export') + "?month=6&year=2026"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        # Load exported sheet
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        ws = wb.active
        self.assertEqual(ws.cell(row=2, column=1).value, self.employee.emp_id)
        self.assertEqual(ws.cell(row=2, column=2).value, self.employee.name)

    def test_unauthorized_salary_export_fails(self):
        self.client.force_authenticate(user=self.hr_user)
        url = reverse('salary_export') + "?month=6&year=2026"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Employee cannot export template
        self.client.force_authenticate(user=self.employee_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def create_excel_file(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        headers = [
            "Emp ID", "Emp Name", "Department", "Location", "Gross Salary", 
            "PF Contribution", "ESI", "Labour Welfare Fund", "Professional Tax", 
            "Other Deductions", "Leaves Available", "Working Days", "Leave Encashment / Extra Days"
        ]
        ws.append(headers)
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue()

    def test_admin_salary_import_success(self):
        self.client.force_authenticate(user=self.admin_user)
        excel_content = self.create_excel_file([
            [self.employee.emp_id, "John Doe", "Engineering", "Mohali", 87000.00, 6000.00, 0.00, 0.00, 200.00, 0.00, 0.00, 30.00, 0.00]
        ])
        
        uploaded_file = SimpleUploadedFile("salary.xlsx", excel_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        url = reverse('salary_import')
        data = {
            'file': uploaded_file,
            'month': 6,
            'year': 2026
        }
        res = self.client.post(url, data, format='multipart')
        if res.status_code != 200:
            print("IMPORT SUCCESS TEST FAIL DATA:", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['success'], 1)
        self.assertEqual(res.data['failed'], 0)

        # Check slip is created in DB as draft
        slip = SalarySlip.objects.get(bitrix_user_id=self.employee.bitrix_id, month=6, year=2026)
        self.assertEqual(slip.status, 'draft')
        self.assertEqual(slip.gross_salary, Decimal('87000.00'))
        self.assertEqual(slip.total_deductions, Decimal('6200.00')) # 6000 PF + 200 PT
        self.assertEqual(slip.net_salary, Decimal('80800.00'))
        self.assertTrue(slip.pdf_file)

    def test_admin_salary_import_partial_failure(self):
        self.client.force_authenticate(user=self.admin_user)
        excel_content = self.create_excel_file([
            # Success row
            [self.employee.emp_id, "John Doe", "Engineering", "Mohali", 87000.00, 6000.00, 0.00, 0.00, 200.00, 0.00, 0.00, 30.00, 0.00],
            # Failure row: invalid Employee ID
            ["EMP-INVALID", "Jane Doe", "Design", "Mohali", 40000.00, 4800.00, 0.00, 0.00, 200.00, 0.00, 0.00, 30.00, 0.00]
        ])
        
        uploaded_file = SimpleUploadedFile("salary_partial.xlsx", excel_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        url = reverse('salary_import')
        data = {
            'file': uploaded_file,
            'month': 6,
            'year': 2026
        }
        res = self.client.post(url, data, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['success'], 1)
        self.assertEqual(res.data['failed'], 1)
        self.assertIsNotNone(res.data['error_report_url'])

        # Verify batch status is partial
        batch = SalaryImportBatch.objects.first()
        self.assertEqual(batch.status, 'partial')

    def test_admin_salary_import_total_failure_rollback(self):
        self.client.force_authenticate(user=self.admin_user)
        excel_content = self.create_excel_file([
            # Failure row 1: invalid Employee ID
            ["EMP-INVALID-1", "Jane Doe", "Design", "Mohali", 40000.00, 4800.00, 0.00, 0.00, 200.00, 0.00, 0.00, 30.00, 0.00],
            # Failure row 2: invalid gross salary amount (-500)
            [self.employee.emp_id, "John Doe", "Engineering", "Mohali", -500.00, 6000.00, 0.00, 0.00, 200.00, 0.00, 0.00, 30.00, 0.00]
        ])

        uploaded_file = SimpleUploadedFile("salary_failed.xlsx", excel_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        url = reverse('salary_import')
        data = {
            'file': uploaded_file,
            'month': 6,
            'year': 2026
        }
        res = self.client.post(url, data, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['failed'], 2)

        # Verify no slips created at all
        self.assertEqual(SalarySlip.objects.count(), 0)

    def test_publish_workflow(self):
        # Create draft slip
        slip = SalarySlip.objects.create(
            bitrix_user_id=self.employee.bitrix_id,
            month=6,
            year=2026,
            gross_salary=87000.00,
            status='draft'
        )
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('salary_publish')
        res = self.client.post(url, {'month': 6, 'year': 2026}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # Verify slip is published
        slip.refresh_from_db()
        self.assertEqual(slip.status, 'published')

    def test_salary_history_scoping(self):
        # Create slips
        slip1 = SalarySlip.objects.create(
            bitrix_user_id=self.employee.bitrix_id, month=5, year=2026, gross_salary=87000.00, status='published'
        )
        slip2 = SalarySlip.objects.create(
            bitrix_user_id=self.employee.bitrix_id, month=6, year=2026, gross_salary=90000.00, status='draft'
        )

        # Test employee request
        self.client.force_authenticate(user=self.employee_user)
        url = reverse('salary_history')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Employees should only see their own published records (slip1)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['month'], 5)

        # Test HR request (can see draft too)
        self.client.force_authenticate(user=self.hr_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)

    def test_salary_slip_pdf_and_zip_download(self):
        # Create multiple published slips
        slip1 = SalarySlip.objects.create(
            bitrix_user_id=self.employee.bitrix_id, month=4, year=2026, gross_salary=87000.00, status='published'
        )
        slip2 = SalarySlip.objects.create(
            bitrix_user_id=self.employee.bitrix_id, month=5, year=2026, gross_salary=87000.00, status='published'
        )

        # Download single month
        self.client.force_authenticate(user=self.employee_user)
        url = reverse('salary_download') + "?type=single&month=4&year=2026"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], "application/pdf")

        # Download multi-month (last3) should zip
        url = reverse('salary_download') + "?type=last3"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], "application/zip")
