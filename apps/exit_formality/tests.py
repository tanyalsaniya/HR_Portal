# apps/exit_formality/tests.py
import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from roles.models import Role, Permission
from employee_onboarding.models import Department
from exit_formality.models import ExitRequest, ExitSecureLink, ExitFormResponse, ExitFFSettlement
from common.bitrix_client import BitrixEmployeeMock

User = get_user_model()

class ExitModuleTests(APITestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        # Setup mock patchers
        self.get_all_users_patcher = patch('common.bitrix_client.BitrixClient.get_all_users')
        self.mock_get_all = self.get_all_users_patcher.start()
        
        self.get_user_detail_patcher = patch('common.bitrix_client.BitrixClient.get_user_detail')
        self.mock_get_detail = self.get_user_detail_patcher.start()

        today_str = str(datetime.date.today())
        year_ago_str = str(datetime.date.today() - datetime.timedelta(days=365))
        month_ago_str = str(datetime.date.today() - datetime.timedelta(days=30))

        self.user_dict_10 = {
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
            'joining_date': year_ago_str,
            'status': 'Active',
            'notice_period_days': 30,
            'bond_period_months': 0
        }

        self.user_dict_20 = {
            'id': '20',
            'emp_id': 'BITRIX-20',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'name': 'Jane Smith',
            'email': 'jane.smith@test.com',
            'phone': '9876543211',
            'designation': 'Manager',
            'department_name': 'Engineering',
            'dob': '1996-06-11',
            'gender': 'Female',
            'joining_date': today_str,
            'status': 'Active',
            'notice_period_days': 60,
            'bond_period_months': 0
        }

        self.user_dict_30 = {
            'id': '30',
            'emp_id': 'BITRIX-30',
            'first_name': 'Bonded',
            'last_name': 'User',
            'name': 'Bonded User',
            'email': 'bonded@test.com',
            'phone': '9876543212',
            'designation': 'Software Engineer',
            'department_name': 'Engineering',
            'dob': '1995-05-10',
            'gender': 'Male',
            'joining_date': month_ago_str,
            'status': 'Active',
            'notice_period_days': 30,
            'bond_period_months': 12
        }

        self.users = [self.user_dict_10, self.user_dict_20, self.user_dict_30]
        self.mock_get_all.return_value = self.users

        def get_detail_side_effect(uid, force_refresh=False):
            for u in self.users:
                if str(u['id']) == str(uid):
                    return u
            return None
        self.mock_get_detail.side_effect = get_detail_side_effect

        self.emp = BitrixEmployeeMock(self.user_dict_10)

        # Create master roles and permissions
        self.admin_role = Role.objects.create(name="Admin", code="ADMIN")
        self.hr_role = Role.objects.create(name="HR", code="HR")
        
        # Add permissions
        self.read_perm = Permission.objects.create(name="Read Exit", codename="exit.read", module="exit")
        self.create_perm = Permission.objects.create(name="Create Exit", codename="exit.create", module="exit")
        self.update_perm = Permission.objects.create(name="Update Exit", codename="exit.update", module="exit")
        self.letters_perm = Permission.objects.create(name="Letters Exit", codename="exit.generate_letters", module="exit")
        self.send_email_perm, _ = Permission.objects.get_or_create(codename="exit.send_email", defaults={"name": "Send Exit Documents Email", "module": "exit"})
        
        self.hr_role.permissions.add(self.read_perm, self.create_perm, self.update_perm, self.letters_perm, self.send_email_perm)
        
        # Create users
        self.admin_user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password", role=self.admin_role)
        self.hr_user = User.objects.create_user(username="hr", email="hr@test.com", password="password", role=self.hr_role)
        
        # Create department
        self.dept = Department.objects.create(name="Engineering")

    def tearDown(self):
        self.get_all_users_patcher.stop()
        self.get_user_detail_patcher.stop()

    def test_notice_period_waiver(self):
        self.client.force_authenticate(user=self.hr_user)
        
        # Case 1: Waiver = True
        url = reverse('exitrequest-list')
        data = {
            "bitrix_user_id": self.emp.bitrix_id,
            "resignation_date": str(datetime.date.today()),
            "exit_type": "RESIGNATION",
            "mode_of_resignation": "EMAIL",
            "notice_period_waiver": True,
            "exit_reason": "Moving on to a better opportunity, thank you." # at least 20 chars
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exit_req = ExitRequest.objects.get(bitrix_user_id=self.emp.bitrix_id)
        self.assertEqual(exit_req.last_working_day, datetime.date.today())

        # Case 2: Waiver = False
        data2 = {
            "bitrix_user_id": "20",
            "resignation_date": str(datetime.date.today()),
            "exit_type": "RESIGNATION",
            "mode_of_resignation": "EMAIL",
            "notice_period_waiver": False,
            "exit_reason": "Moving on to a better opportunity, thank you."
        }
        res2 = self.client.post(url, data2, format='json')
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        exit_req2 = ExitRequest.objects.get(bitrix_user_id="20")
        self.assertEqual(exit_req2.last_working_day, datetime.date.today() + datetime.timedelta(days=60))

    def test_absconding_flow(self):
        self.client.force_authenticate(user=self.hr_user)
        url = reverse('exitrequest-list')
        data = {
            "bitrix_user_id": self.emp.bitrix_id,
            "resignation_date": str(datetime.date.today()),
            "exit_type": "ABSCONDING",
            "mode_of_resignation": "VERBAL",
            "notice_period_waiver": True,
            "exit_reason": "Employee has absconded from duties since last week."
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        exit_req = ExitRequest.objects.get(bitrix_user_id=self.emp.bitrix_id)
        # Verify no secure link is created
        self.assertFalse(ExitSecureLink.objects.filter(exit_request=exit_req).exists())

        # Admin overrides this request
        self.client.force_authenticate(user=self.admin_user)
        override_url = reverse('exitrequest-override', args=[exit_req.id])
        res_override = self.client.put(override_url, {"override_reason": "Absconding Override"}, format='json')
        self.assertEqual(res_override.status_code, status.HTTP_200_OK)
        exit_req.refresh_from_db()
        self.assertEqual(exit_req.status, "OVERRIDDEN")

    def test_link_expiry_and_resend(self):
        self.client.force_authenticate(user=self.hr_user)
        
        # Initiate
        url = reverse('exitrequest-list')
        data = {
            "bitrix_user_id": self.emp.bitrix_id,
            "resignation_date": str(datetime.date.today()),
            "exit_type": "RESIGNATION",
            "mode_of_resignation": "EMAIL",
            "notice_period_waiver": False,
            "exit_reason": "Moving on to a better opportunity, thank you."
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        exit_req = ExitRequest.objects.get(bitrix_user_id=self.emp.bitrix_id)
        link = ExitSecureLink.objects.get(exit_request=exit_req)
        old_token = link.token
        
        # Expire link
        link.expires_at = timezone.now() - datetime.timedelta(hours=1)
        link.save()
        
        # Access link (GET should return 410)
        q_url = reverse('exit_public_questionnaire') + f"?token={link.token}"
        res_get = self.client.get(q_url)
        self.assertEqual(res_get.status_code, status.HTTP_410_GONE)

        # Resend link
        resend_url = reverse('exitrequest-resend-link', args=[exit_req.id])
        res_resend = self.client.post(resend_url)
        self.assertEqual(res_resend.status_code, status.HTTP_200_OK)
        
        # Verify old link is renewed (token changed, used is False, is valid)
        link.refresh_from_db()
        self.assertNotEqual(link.token, old_token)
        self.assertFalse(link.used)
        self.assertTrue(link.is_valid())

    def test_bond_penalty_validation(self):
        self.client.force_authenticate(user=self.hr_user)
        
        # Initiate
        url = reverse('exitrequest-list')
        data = {
            "bitrix_user_id": "30",
            "resignation_date": str(datetime.date.today()),
            "exit_type": "RESIGNATION",
            "mode_of_resignation": "EMAIL",
            "notice_period_waiver": True,
            "exit_reason": "Moving on to a better opportunity, thank you."
        }
        self.client.post(url, data, format='json')
        exit_req = ExitRequest.objects.get(bitrix_user_id="30")
        
        # Save clearances first so we can process F&F
        exit_req.status = 'CLEARANCES_DONE'
        exit_req.save()
        
        # Process F&F without bond penalty (should fail)
        ff_url = reverse('exitrequest-process-ff', args=[exit_req.id])
        ff_data = {
            "salary_month_days": 30,
            "salary_worked_days": 15,
            "salary_proportional": 15000,
            "bond_penalty": 0, # zero penalty
            "payment_mode": "BANK_TRANSFER"
        }
        res_ff = self.client.post(ff_url, ff_data, format='json')
        self.assertEqual(res_ff.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bond_penalty", res_ff.data)
        
        # Process F&F with bond penalty (should succeed)
        ff_data["bond_penalty"] = 50000
        res_ff_ok = self.client.post(ff_url, ff_data, format='json')
        self.assertEqual(res_ff_ok.status_code, status.HTTP_200_OK)

    def test_rbac_controls(self):
        # Initiate an exit
        self.client.force_authenticate(user=self.hr_user)
        url = reverse('exitrequest-list')
        data = {
            "bitrix_user_id": self.emp.bitrix_id,
            "resignation_date": str(datetime.date.today()),
            "exit_type": "RESIGNATION",
            "mode_of_resignation": "EMAIL",
            "notice_period_waiver": True,
            "exit_reason": "Moving on to a better opportunity, thank you."
        }
        self.client.post(url, data, format='json')
        exit_req = ExitRequest.objects.get(bitrix_user_id=self.emp.bitrix_id)
        
        # HR tries to approve F&F (should get 403)
        approve_url = reverse('exitrequest-approve-ff', args=[exit_req.id])
        res_approve = self.client.post(approve_url)
        self.assertEqual(res_approve.status_code, status.HTTP_403_FORBIDDEN)
        
        # HR tries to override exit (should get 403)
        override_url = reverse('exitrequest-override', args=[exit_req.id])
        res_override = self.client.put(override_url, {"override_reason": "HR override"}, format='json')
        self.assertEqual(res_override.status_code, status.HTTP_403_FORBIDDEN)
        
        # HR tries to generate NOC (should get 403)
        noc_url = reverse('exitrequest-generate-noc', args=[exit_req.id])
        res_noc = self.client.post(noc_url)
        self.assertEqual(res_noc.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin does all three (should succeed/allow)
        self.client.force_authenticate(user=self.admin_user)
        
        # First save F&F calculations so it can be approved
        ff_url = reverse('exitrequest-process-ff', args=[exit_req.id])
        self.client.post(ff_url, {"salary_month_days": 30, "salary_worked_days": 30, "salary_proportional": 30000}, format='json')
        
        res_approve_ok = self.client.post(approve_url)
        self.assertEqual(res_approve_ok.status_code, status.HTTP_200_OK)
        
        res_noc_ok = self.client.post(noc_url)
        self.assertEqual(res_noc_ok.status_code, status.HTTP_201_CREATED)

    def test_toggle_email_dispatch(self):
        # Initiate
        self.client.force_authenticate(user=self.hr_user)
        url = reverse('exitrequest-list')
        data = {
            "bitrix_user_id": self.emp.bitrix_id,
            "resignation_date": str(datetime.date.today()),
            "exit_type": "RESIGNATION",
            "mode_of_resignation": "EMAIL",
            "notice_period_waiver": True,
            "exit_reason": "Moving on to a better opportunity, thank you."
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exit_req = ExitRequest.objects.get(bitrix_user_id=self.emp.bitrix_id)

        # Set clearance done and process/approve F&F
        exit_req.status = 'CLEARANCES_DONE'
        exit_req.save()

        ff_url = reverse('exitrequest-process-ff', args=[exit_req.id])
        self.client.post(ff_url, {"salary_month_days": 30, "salary_worked_days": 30, "salary_proportional": 30000}, format='json')

        self.client.force_authenticate(user=self.admin_user)
        approve_url = reverse('exitrequest-approve-ff', args=[exit_req.id])
        self.client.post(approve_url)

        # Case 1: Send email is False
        self.client.force_authenticate(user=self.hr_user)
        mark_url = reverse('exitrequest-mark-fully-exited', args=[exit_req.id])
        
        res_mark = self.client.post(mark_url, {"send_email": False}, format='json')
        self.assertEqual(res_mark.status_code, status.HTTP_200_OK)
        
        exit_req.refresh_from_db()
        self.assertEqual(exit_req.status, 'FULLY_EXITED')
        self.assertFalse(exit_req.send_email_on_exit)

        # Reopen to test Case 2: Send email is True
        self.client.force_authenticate(user=self.admin_user)
        reopen_url = reverse('exitrequest-reopen', args=[exit_req.id])
        self.client.put(reopen_url)
        exit_req.refresh_from_db()
        self.assertEqual(exit_req.status, 'REOPENED')

        # Approve F&F again
        self.client.post(approve_url)

        # Mark exited again with send_email = True
        self.client.force_authenticate(user=self.hr_user)
        res_mark2 = self.client.post(mark_url, {"send_email": True}, format='json')
        self.assertEqual(res_mark2.status_code, status.HTTP_200_OK)
        exit_req.refresh_from_db()
        self.assertEqual(exit_req.status, 'FULLY_EXITED')
        self.assertTrue(exit_req.send_email_on_exit)


from django.test import TestCase

class ExitLetterCustomizationSanitizationTests(TestCase):

    def test_mock_obj_attribute_sanitization(self):
        from exit_formality.services import MockObj, sanitize_html_context
        from django.utils.safestring import SafeData
        
        class Original:
            def __init__(self):
                self.address = "Original\nAddress"
                self.first_name = "John"
        
        orig = Original()
        mock = MockObj(orig, address="Custom\nAddress\nWith <b>bold</b>")
        
        # Test custom override is sanitized when MockObj is sanitized
        sanitized_mock = sanitize_html_context(mock)
        self.assertEqual(sanitized_mock.address, "Custom<br>Address<br>With <b>bold</b>")
        self.assertTrue(isinstance(sanitized_mock.address, SafeData))
        
        # Test original attribute (not overridden) is sanitized on attribute access (via __getattr__)
        self.assertEqual(sanitized_mock.first_name, "John")
        self.assertTrue(isinstance(sanitized_mock.first_name, SafeData))

