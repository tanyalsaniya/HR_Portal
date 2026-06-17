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
        self.assertEqual(ws.cell(row=2, column=1).value, 1)
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
            "Sr. No.", "Name", "Designation", "Month days", "Worked days", 
            "Weekend", "CL", "Extra", "Payable Days", "Month Salary", 
            "Payable Salary", "Extra days working", "Fine/Advance", "Net Payable", 
            "Bank A/c No.", "Bank"
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
            [1, "John Doe", "Software Engineer", 30.0, 26.0, 4.0, 0.0, 0.0, 30.0, 87000.0, 87000.0, 0.0, 0.0, 87000.0, "123456", "ICICI"]
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
        self.assertEqual(slip.month_salary, Decimal('87000.00'))
        self.assertEqual(slip.fine_advance, Decimal('0.00'))
        self.assertEqual(slip.net_payable, Decimal('87000.00'))
        self.assertTrue(slip.pdf_file)

    def test_admin_salary_import_partial_failure(self):
        self.client.force_authenticate(user=self.admin_user)
        excel_content = self.create_excel_file([
            # Success row
            [1, "John Doe", "Software Engineer", 30.0, 26.0, 4.0, 0.0, 0.0, 30.0, 87000.0, 87000.0, 0.0, 0.0, 87000.0, "123456", "ICICI"],
            # Failure row: invalid Name
            [2, "Invalid Name", "Design", 30.0, 26.0, 4.0, 0.0, 0.0, 30.0, 40000.0, 40000.0, 0.0, 0.0, 40000.0, "654321", "HDFC"]
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
            # Failure row 1: invalid Name
            [1, "Invalid Name", "Design", 30.0, 26.0, 4.0, 0.0, 0.0, 30.0, 40000.0, 40000.0, 0.0, 0.0, 40000.0, "654321", "HDFC"],
            # Failure row 2: invalid gross/month salary amount (-500)
            [2, "John Doe", "Software Engineer", 30.0, 26.0, 4.0, 0.0, 0.0, 30.0, -500.0, -500.0, 0.0, 0.0, -500.0, "123456", "ICICI"]
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
            month_salary=87000.00,
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
            bitrix_user_id=self.employee.bitrix_id, month=5, year=2026, month_salary=87000.00, status='published'
        )
        slip2 = SalarySlip.objects.create(
            bitrix_user_id=self.employee.bitrix_id, month=6, year=2026, month_salary=90000.00, status='draft'
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
            bitrix_user_id=self.employee.bitrix_id, month=4, year=2026, month_salary=87000.00, status='published'
        )
        slip2 = SalarySlip.objects.create(
            bitrix_user_id=self.employee.bitrix_id, month=5, year=2026, month_salary=87000.00, status='published'
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

    def test_bank_details_autosave_and_prefill(self):
        # Update mock values to fully-populated user dictionaries to prevent serializer KeyError
        user_dict_complete = {
            'id': '10',
            'emp_id': 'BITRIX-10',
            'first_name': 'John',
            'last_name': 'Doe',
            'name': 'John Doe',
            'email': 'emp@test.com',
            'work_email': 'emp@test.com',
            'personal_email': '',
            'phone': '9876543210',
            'designation': 'Software Engineer',
            'department_name': 'Engineering',
            'dob': '1995-05-10',
            'gender': 'Male',
            'joining_date': '2026-06-01',
            'status': 'Active',
            'onboarding_complete': True,
            'alternate_phone': '',
            'address_line1': 'Mohali',
            'address_line2': '',
            'city': 'Mohali',
            'state': 'Punjab',
            'pin_code': '160055',
            'employment_type': 'Full Time',
            'emergency_contact_name': 'Emergency Contact',
            'emergency_relationship': 'Friend',
            'emergency_phone': '9876543210'
        }
        self.mock_get_detail.return_value = user_dict_complete
        self.mock_get_all.return_value = [user_dict_complete]

        from salary.models import EmployeeBankDetail
        # Verify no bank details exist initially
        self.assertEqual(EmployeeBankDetail.objects.count(), 0)

        # 1. Test Auto-save on Excel Import
        self.client.force_authenticate(user=self.admin_user)
        excel_content = self.create_excel_file([
            [1, "John Doe", "Software Engineer", 30.0, 26.0, 4.0, 0.0, 0.0, 30.0, 87000.0, 87000.0, 0.0, 0.0, 87000.0, "987654321", "MockBank"]
        ])
        uploaded_file = SimpleUploadedFile("salary.xlsx", excel_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        url = reverse('salary_import')
        res = self.client.post(url, {'file': uploaded_file, 'month': 6, 'year': 2026}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify EmployeeBankDetail is saved
        bank_detail = EmployeeBankDetail.objects.get(bitrix_user_id=self.employee.bitrix_id)
        self.assertEqual(bank_detail.bank_account_no, "987654321")
        self.assertEqual(bank_detail.bank_name, "MockBank")

        # 2. Test Prefill on Excel Import when Excel is blank
        excel_content_blank = self.create_excel_file([
            [1, "John Doe", "Software Engineer", 30.0, 26.0, 4.0, 0.0, 0.0, 30.0, 87000.0, 87000.0, 0.0, 0.0, 87000.0, "", ""]
        ])
        uploaded_file_blank = SimpleUploadedFile("salary_blank.xlsx", excel_content_blank, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        # Let's delete the old slip to test creation
        SalarySlip.objects.all().delete()
        res = self.client.post(url, {'file': uploaded_file_blank, 'month': 6, 'year': 2026}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify slip has the prefilled bank account/name from database
        slip = SalarySlip.objects.get(bitrix_user_id=self.employee.bitrix_id, month=6, year=2026)
        self.assertEqual(slip.bank_account_no, "987654321")
        self.assertEqual(slip.bank_name, "MockBank")

        # 3. Test update on Salary slip edit
        edit_url = reverse('salary_edit', kwargs={'pk': slip.id})
        res = self.client.put(edit_url, {'bank_account_no': '111222333', 'bank_name': 'NewMockBank'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify persistent EmployeeBankDetail is updated
        bank_detail.refresh_from_db()
        self.assertEqual(bank_detail.bank_account_no, "111222333")
        self.assertEqual(bank_detail.bank_name, "NewMockBank")

        # 4. Test Prefill in Employee Details API & view
        emp_detail_url = reverse('employees_detail_view', kwargs={'pk': int(self.employee.bitrix_id)})
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(emp_detail_url, {'format': 'json'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['bank_account'], "111222333")
        self.assertEqual(res.data['bank_name'], "NewMockBank")

        # 5. Test update via Employee details PATCH request
        res = self.client.patch(emp_detail_url + "?format=json", {'bank_account': '555666777', 'bank_name': 'FinalMockBank'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify updated bank details are saved to database
        bank_detail.refresh_from_db()
        self.assertEqual(bank_detail.bank_account_no, "555666777")
        self.assertEqual(bank_detail.bank_name, "FinalMockBank")
