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
        Filters for:
        - STUDENTS ONLY (excludes employees and other entity types)
        - Students with ACTIVE status (not COMPLETED or DISCONTINUED)
        - Students currently enrolled (completion_date > today)
        
        Args:
            entity_type_id: The Bitrix24 CRM entity type ID (default: 1044 for students)
            force_refresh: Force refresh from API (ignore cache)
            
        Returns:
            List of active, currently enrolled students with pagination support
        """
        cache_key = f"bitrix24_active_students_{entity_type_id}"
        
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        webhook = cls.get_webhook_url()
        base_url = f"{webhook}/crm.item.list.json"
        
        active_students = []
        start = 0
        today = date.today()
        
        try:
            logger.info(f"Fetching active STUDENTS from Bitrix24 CRM (entityTypeId={entity_type_id})")
            while True:
                # Build API request with filters for active, ongoing STUDENTS ONLY
                # Filter 1: Status must be ACTIVE (not COMPLETED or DISCONTINUED)
                # Filter 2: Completion date is in the future (currently ongoing)
                # Filter 3: Has student-specific fields (UF_JOINING_DATE, UF_COMPLETION_DATE) - NOT employee data
                
                params = {
                    'entityTypeId': entity_type_id,
                    'start': start,
                    'filter': {
                        'STATUS': 'ACTIVE',  # Only active students
                    },
                    'select': ['*', 'uf_*']  # Select all standard and custom fields
                }
                
                response = requests.post(
                    base_url,
                    json=params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('result', [])
                    
                    # Filter for STUDENT DATA ONLY (not employee data)
                    for item in result:
                        # STUDENT VALIDATION: Check for student-specific fields
                        # Students must have course/learning related fields, not employment fields
                        has_student_fields = (
                            item.get('UF_COMPLETION_DATE') or 
                            item.get('UF_JOINING_DATE') or 
                            item.get('UF_COURSE_NAME') or
                            item.get('UF_INSTITUTE') or
                            item.get('TITLE') or
                            item.get('NAME')
                        )
                        
                        # EMPLOYEE EXCLUSION: Exclude if it has employee-specific fields
                        # Employees typically have these fields; students should not
                        has_employee_fields = (
                            item.get('WORK_EMAIL') or 
                            item.get('WORK_PHONE') or
                            item.get('UF_EMPLOYMENT_DATE') or
                            item.get('PERSONAL_BIRTHDAY') and 
                            not (item.get('UF_JOINING_DATE') or item.get('UF_COURSE_NAME'))
                        )
                        
                        # Skip if this is employee data
                        if has_employee_fields and not (item.get('UF_COURSE_NAME') or item.get('UF_INSTITUTE')):
                            logger.debug(f"Skipping employee record: {item.get('NAME')} (ID: {item.get('ID')})")
                            continue
                        
                        # Must have at least one student field
                        if not has_student_fields:
                            logger.debug(f"Skipping record without student fields: {item.get('NAME')} (ID: {item.get('ID')})")
                            continue
                        
                        # Now check completion date for currently enrolled students
                        completion_date_str = item.get('UF_COMPLETION_DATE') or item.get('completion_date')
                        
                        try:
                            if completion_date_str:
                                completion_date = datetime.strptime(
                                    completion_date_str.split('T')[0] if 'T' in completion_date_str else completion_date_str, 
                                    '%Y-%m-%d'
                                ).date()
                                
                                # Only include if completion date is in the future (currently enrolled)
                                if completion_date > today:
                                    active_students.append(item)
                                else:
                                    logger.debug(f"Excluding completed student: {item.get('NAME')} (completion: {completion_date})")
                            else:
                                # Include if no completion date set (ongoing by default)
                                logger.debug(f"Including student with no completion date: {item.get('NAME')}")
                                active_students.append(item)
                        except (ValueError, TypeError, AttributeError) as e:
                            logger.warning(f"Error parsing dates for student {item.get('ID')}: {e}")
                            # Include if date parsing fails but has student fields
                            active_students.append(item)
                    
                    # Check for next page
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
            logger.info(f"Successfully fetched {len(active_students)} active STUDENTS from Bitrix24 CRM (employees excluded)")
            return active_students
        except Exception as e:
            logger.error(f"Failed to cache students: {e}")
            return active_students

    @classmethod
    def get_active_students_paginated(cls, entity_type_id=1044, page_size=50, offset=0):
        """
        Fetches active STUDENTS ONLY with pagination support.
        Excludes employee data automatically.
        
        Args:
            entity_type_id: The Bitrix24 CRM entity type ID (default: 1044)
            page_size: Number of records per page
            offset: Starting record position
            
        Returns:
            Dict with 'items' (student list only), 'next_offset' (for pagination), and 'total_count'
        """
        webhook = cls.get_webhook_url()
        base_url = f"{webhook}/crm.item.list.json"
        today = date.today()
        
        try:
            # Request page of data
            params = {
                'entityTypeId': entity_type_id,
                'start': offset,
                'limit': page_size,
                'filter': {
                    'STATUS': 'ACTIVE'  # Only active students
                },
                'select': ['*', 'uf_*']
            }
            
            response = requests.post(base_url, json=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', [])
                
                # Filter for STUDENT DATA ONLY (not employees) and currently enrolled
                active_enrolled_students = []
                for item in result:
                    # STUDENT VALIDATION: Check for student-specific fields
                    has_student_fields = (
                        item.get('UF_COMPLETION_DATE') or 
                        item.get('UF_JOINING_DATE') or 
                        item.get('UF_COURSE_NAME') or
                        item.get('UF_INSTITUTE') or
                        item.get('TITLE') or
                        item.get('NAME')
                    )
                    
                    # EMPLOYEE EXCLUSION: Exclude if it has employee-specific fields
                    has_employee_fields = (
                        item.get('WORK_EMAIL') or 
                        item.get('WORK_PHONE') or
                        item.get('UF_EMPLOYMENT_DATE') or
                        (item.get('PERSONAL_BIRTHDAY') and 
                         not (item.get('UF_COURSE_NAME') or item.get('UF_INSTITUTE')))
                    )
                    
                    # Skip if this looks like employee data
                    if has_employee_fields and not (item.get('UF_COURSE_NAME') or item.get('UF_INSTITUTE')):
                        logger.debug(f"[Pagination] Skipping employee record: {item.get('NAME')} (ID: {item.get('ID')})")
                        continue
                    
                    # Must have at least one student field
                    if not has_student_fields:
                        logger.debug(f"[Pagination] Skipping record without student fields: {item.get('NAME')}")
                        continue
                    
                    # Check completion date for currently enrolled students
                    completion_date_str = item.get('UF_COMPLETION_DATE') or item.get('completion_date')
                    
                    try:
                        if completion_date_str:
                            completion_date = datetime.strptime(
                                completion_date_str.split('T')[0] if 'T' in completion_date_str else completion_date_str,
                                '%Y-%m-%d'
                            ).date()
                            if completion_date > today:
                                active_enrolled_students.append(item)
                            else:
                                logger.debug(f"[Pagination] Excluding completed student: {item.get('NAME')}")
                        else:
                            # Include if no completion date set (ongoing by default)
                            active_enrolled_students.append(item)
                    except (ValueError, TypeError):
                        # Include if date parsing fails but has student fields
                        active_enrolled_students.append(item)
                
                return {
                    'items': active_enrolled_students,
                    'next_offset': data.get('next', None),
                    'total_count': len(active_enrolled_students)  # Actual student count, not including employees
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
            if isinstance(val, str):
                try:
                    parsed_date = datetime.datetime.strptime(val, '%Y-%m-%d').date()
                    setattr(self, date_field, parsed_date)
                except Exception:
                    setattr(self, date_field, datetime.date.today())
            elif val is None:
                setattr(self, date_field, datetime.date.today())

    @property
    def pk(self):
        return self.id

    @property
    def id(self):
        # Return integer ID for compatibility with views/serializers expecting int primary keys
        try:
            return int(self._data.get('id', 0))
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

