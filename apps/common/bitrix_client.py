import os
import requests
import logging
from django.core.cache import cache
from datetime import datetime, date

logger = logging.getLogger(__name__)

class BitrixClient:
    CACHE_KEY_ALL_USERS = "bitrix24_all_active_users"
    CACHE_TIMEOUT_SECONDS = 300  # Cache for 5 minutes

    @staticmethod
    def get_webhook_url():
        # Retrieve webhook from environment or use user's webhook as a fallback
        url = os.getenv('BITRIX24_WEBHOOK_URL')
        if not url:
            url = "https://devexhub.bitrix24.in/rest/1/vpas32pze4n94125/"
        return url.rstrip('/')

    @staticmethod
    def get_student_webhook_url():
        url = os.getenv('BITRIX24_STUDENT_WEBHOOK_URL')
        if not url:
            url = "https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/"
        return url.rstrip('/')


    @classmethod
    def get_all_users(cls, force_refresh=False):
        """
        Fetches all users (active and inactive) from Bitrix24 using pagination.
        Caches results to optimize performance.
        """
        if not force_refresh:
            cached_data = cache.get(cls.CACHE_KEY_ALL_USERS)
            if cached_data is not None:
                return cached_data

        webhook = cls.get_webhook_url()
        base_url = f"{webhook}/user.get.json"
        
        active_users = []
        start = 0
        try:
            logger.info("Fetching active users list from Bitrix24 API with pagination")
            while True:
                api_url = f"{base_url}?start={start}"
                response = requests.get(api_url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('result', [])
                    active_users.extend(result)
                    
                    # Check for next page
                    next_start = data.get('next')
                    if next_start:
                        start = next_start
                    else:
                        break
                else:
                    logger.error(f"Bitrix24 user.get API returned error for active users: {response.text}")
                    break
        except Exception as e:
            logger.error(f"Failed to query active users from Bitrix24: {e}")

        inactive_users = []
        start = 0
        try:
            logger.info("Fetching inactive users list from Bitrix24 API with pagination")
            while True:
                api_url = f"{base_url}?start={start}&FILTER[ACTIVE]=N"
                response = requests.get(api_url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('result', [])
                    inactive_users.extend(result)
                    
                    # Check for next page
                    next_start = data.get('next')
                    if next_start:
                        start = next_start
                    else:
                        break
                else:
                    logger.error(f"Bitrix24 user.get API returned error for inactive users: {response.text}")
                    break
        except Exception as e:
            logger.error(f"Failed to query inactive users from Bitrix24: {e}")

        # Combine and deduplicate users
        seen_ids = set()
        unique_users = []
        for user in active_users + inactive_users:
            uid = str(user.get('ID') or user.get('id', ''))
            if uid and uid not in seen_ids:
                seen_ids.add(uid)
                unique_users.append(user)

        try:
            # Normalize and format results
            normalized_users = [cls._normalize_user(user) for user in unique_users]
            # Cache the list
            cache.set(cls.CACHE_KEY_ALL_USERS, normalized_users, cls.CACHE_TIMEOUT_SECONDS)
            return normalized_users
        except Exception as e:
            logger.error(f"Failed to normalize Bitrix24 users: {e}")

        # Return empty list or cached list as a fallback in case of API error
        cached_data = cache.get(cls.CACHE_KEY_ALL_USERS)
        return cached_data if cached_data is not None else []

    @classmethod
    def get_user_detail(cls, bitrix_user_id, force_refresh=False):
        """
        Retrieves a single user's detail by ID. First checks cache, then API.
        """
        users = cls.get_all_users(force_refresh=force_refresh)
        for user in users:
            if str(user.get('id')) == str(bitrix_user_id) or str(user.get('ID')) == str(bitrix_user_id):
                return user
        
        # If not found in cache list, query individual user from Bitrix API directly
        webhook = cls.get_webhook_url()
        api_url = f"{webhook}/user.get.json"
        
        try:
            logger.info(f"Fetching user ID {bitrix_user_id} details from Bitrix24 API")
            # Try active query
            response = requests.post(api_url, json={'ID': bitrix_user_id}, timeout=10)
            result = []
            if response.status_code == 200:
                result = response.json().get('result', [])
            
            # If not found, try querying with inactive filter
            if not result:
                response = requests.post(api_url, json={'ID': bitrix_user_id, 'FILTER': {'ACTIVE': 'N'}}, timeout=10)
                if response.status_code == 200:
                    result = response.json().get('result', [])
                    
            if result:
                user_data = cls._normalize_user(result[0])
                # Update cache by prepending/updating this user in the cached list
                current_cached = cache.get(cls.CACHE_KEY_ALL_USERS) or []
                updated_cached = [u for u in current_cached if str(u.get('id')) != str(bitrix_user_id)]
                updated_cached.append(user_data)
                cache.set(cls.CACHE_KEY_ALL_USERS, updated_cached, cls.CACHE_TIMEOUT_SECONDS)
                return user_data
        except Exception as e:
            logger.error(f"Error fetching user detail for ID {bitrix_user_id}: {e}")
            
        return None

    @classmethod
    def get_active_students_from_crm(cls, entity_type_id=1044, force_refresh=False):
        """
        Fetches ONLY active, currently enrolled STUDENTS from Bitrix24 CRM.
        """
        cache_key = f"bitrix24_active_students_{entity_type_id}"
        
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        webhook = cls.get_student_webhook_url()
        base_url = f"{webhook}/crm.item.list.json"
        
        active_students = []
        start = 0
        stages = [
            'DT1044_20:CLIENT',
            'DT1044_20:UC_8CP2UP',
            'DT1044_20:UC_QXBN3E',
            'DT1044_20:UC_10M2QN',
            'DT1044_20:UC_26OISW',
        ]
        
        try:
            logger.info(f"Fetching active STUDENTS from Bitrix24 CRM (entityTypeId={entity_type_id})")
            while True:
                params = {
                    'entityTypeId': entity_type_id,
                    'start': start,
                    'filter': {
                        'stageId': stages,
                    },
                    'select': ['*', 'uf_*']
                }
                
                response = requests.post(
                    base_url,
                    json=params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('result', {}).get('items', [])
                    active_students.extend(result)
                    
                    next_start = data.get('next')
                    if next_start:
                        start = next_start
                    else:
                        break
                else:
                    logger.error(f"Bitrix24 CRM API returned error: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"Failed to fetch active students from Bitrix24 CRM: {e}")

        try:
            # Cache the filtered results
            cache.set(cache_key, active_students, 300)  # Cache for 5 minutes
            logger.info(f"Successfully fetched {len(active_students)} active STUDENTS from Bitrix24 CRM")
            return active_students
        except Exception as e:
            logger.error(f"Failed to cache students: {e}")
            return active_students


    @classmethod
    def get_active_students_paginated(cls, entity_type_id=1044, page_size=50, offset=0):
        """
        Fetches active STUDENTS ONLY with pagination support.
        """
        webhook = cls.get_student_webhook_url()
        base_url = f"{webhook}/crm.item.list.json"
        stages = [
            'DT1044_20:CLIENT',
            'DT1044_20:UC_8CP2UP',
            'DT1044_20:UC_QXBN3E',
            'DT1044_20:UC_10M2QN',
            'DT1044_20:UC_26OISW',
        ]
        
        try:
            params = {
                'entityTypeId': entity_type_id,
                'start': offset,
                'limit': page_size,
                'filter': {
                    'stageId': stages,
                },
                'select': ['*', 'uf_*']
            }
            
            response = requests.post(base_url, json=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {}).get('items', [])
                
                return {
                    'items': result,
                    'next_offset': data.get('next', None),
                    'total_count': len(result)
                }
            else:
                logger.error(f"CRM API error: {response.text}")
                return {'items': [], 'next_offset': None, 'total_count': 0}
                
        except Exception as e:
            logger.error(f"Failed to fetch paginated students: {e}")
            return {'items': [], 'next_offset': None, 'total_count': 0}


    @staticmethod
    def _normalize_user(raw_user):
        """
        Translates raw Bitrix24 user API fields into standard HR Portal fields.
        """
        # Parse joining date safely
        joining_date_raw = raw_user.get('UF_EMPLOYMENT_DATE') or raw_user.get('DATE_REGISTER') or ''
        joining_date = None
        if joining_date_raw:
            try:
                joining_date = joining_date_raw.split('T')[0]
            except Exception:
                pass

        # Parse DOB safely
        dob_raw = raw_user.get('PERSONAL_BIRTHDAY') or ''
        dob = None
        if dob_raw:
            try:
                dob = dob_raw.split('T')[0]
            except Exception:
                pass

        # Normalize gender to choices expected by HR Portal ('Male', 'Female', 'Other')
        raw_gender = raw_user.get('PERSONAL_GENDER') or ''
        gender = 'Male'
        if raw_gender == 'F':
            gender = 'Female'
        elif raw_gender == 'O':
            gender = 'Other'

        # Department parsing (defaults to 'Engineering' or first mapped dept name)
        dept_ids = raw_user.get('UF_DEPARTMENT') or []
        department_name = "Engineering"  # Default fallback

        first_name = raw_user.get('NAME') or ''
        last_name = raw_user.get('LAST_NAME') or ''

        # Map status dynamically
        is_active = raw_user.get('ACTIVE')
        status_str = 'Active' if is_active is True or str(is_active).lower() in ('true', '1', 'y', 'yes') else 'Exited'

        normalized = {
            'id': str(raw_user.get('ID', '')),
            'emp_id': f"BITRIX-{raw_user.get('ID')}",
            'first_name': first_name,
            'last_name': last_name,
            'name': f"{first_name} {last_name}".strip(),
            'email': raw_user.get('EMAIL') or '',
            'work_email': raw_user.get('EMAIL') or '',
            'personal_email': raw_user.get('UF_PERSONAL_EMAIL') or raw_user.get('PERSONAL_MAILBOX') or '',
            'phone': raw_user.get('PERSONAL_MOBILE') or raw_user.get('WORK_PHONE') or '',
            'designation': raw_user.get('WORK_POSITION') or 'Software Engineer',
            'department': dept_ids[0] if dept_ids else 1,
            'department_name': department_name,
            'dob': dob or '',
            'gender': gender,
            'joining_date': joining_date or '2024-01-01',
            'address_line1': raw_user.get('PERSONAL_CITY') or 'Mohali',
            'city': raw_user.get('PERSONAL_CITY') or 'Mohali',
            'state': 'Punjab',
            'pin_code': '160055',
            'employment_type': 'Full Time',
            'emergency_contact_name': 'Emergency Contact',
            'emergency_relationship': 'Friend',
            'emergency_phone': '9876543210',
            'profile_photo': raw_user.get('PERSONAL_PHOTO') or '',
            'status': status_str,
            'bond_period_months': 0,
            'notice_period_days': 30,
            'bitrix_contact_id': str(raw_user.get('ID', '')),
            'bank_account': '',
            'pan_no': '',
            'onboarding_complete': True,
        }

        # Merge raw fields so that any arbitrary field in the JSON (e.g. XML_ID) is accessible
        normalized.update(raw_user)
        return normalized


class BitrixEmployeeMock:
    def __init__(self, data_dict):
        if not isinstance(data_dict, dict):
            data_dict = {}
        self._data = data_dict
        for k, v in data_dict.items():
            if k != 'id':
                setattr(self, k, v)
        
        # Parse dates to datetime.date objects for compatibility
        import datetime
        for date_field in ('dob', 'joining_date'):
            val = data_dict.get(date_field)
            if isinstance(val, str) and val.strip():
                try:
                    parsed_date = datetime.datetime.strptime(val.strip(), '%Y-%m-%d').date()
                    setattr(self, date_field, parsed_date)
                except Exception:
                    setattr(self, date_field, None)
            elif isinstance(val, (datetime.date, datetime.datetime)):
                setattr(self, date_field, val.date() if isinstance(val, datetime.datetime) else val)
            else:
                setattr(self, date_field, None)

    @property
    def pk(self):
        return self.id

    @property
    def id(self):
        # Return integer ID for compatibility with views/serializers expecting int primary keys
        raw_id = self._data.get('id', '0')
        if isinstance(raw_id, str) and raw_id.startswith('LOCAL-'):
            try:
                return int(raw_id.split('-')[1])
            except (IndexError, ValueError):
                return 0
        try:
            return int(raw_id)
        except (ValueError, TypeError):
            return 0

    @property
    def bitrix_id(self):
        return str(self._data.get('id', ''))

    @property
    def salary_structures(self):
        from salary.models import SalaryStructure
        return SalaryStructure.objects.filter(bitrix_user_id=self.bitrix_id)

    @property
    def documents(self):
        from employee_onboarding.models import EmployeeDocument
        return EmployeeDocument.objects.filter(bitrix_user_id=self.bitrix_id)

    def get_gender_display(self):
        return self._data.get('gender', 'Male')

    def get_state_display(self):
        return self._data.get('state', 'Punjab')

    def get_employment_type_display(self):
        return self._data.get('employment_type', 'Full Time')

    def get_emergency_relationship_display(self):
        return self._data.get('emergency_relationship', 'Friend')

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getattr__(self, name):
        # Fallback for arbitrary model attributes
        return self._data.get(name, "")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.emp_id})"

