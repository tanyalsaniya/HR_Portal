# apps/student_certificate/services.py
import datetime
import os
import re
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from weasyprint import HTML
from django.template.loader import render_to_string
from rules import STUDENT_FEES_WARNING_SUBJECT, STUDENT_FEES_WARNING_BODY
from .models import Student, StudentCertificate
from common.bitrix_client import BitrixClient

def generate_student_certificate_pdf(certificate):
    """
    Generates a student certificate PDF depending on the cert_type.
    Saves PDF file in StudentCertificate model and updates Student status.
    """
    student = certificate.student
    gender = student.gender
    
    # Pronoun resolution
    if gender == 'MALE':
        he_she = "he"
        his_her = "his"
    elif gender == 'FEMALE':
        he_she = "she"
        his_her = "her"
    else:
        he_she = "he/she"
        his_her = "his/her"
        
    bg_image_path = os.path.join(settings.BASE_DIR, 'apps', 'student_certificate', 'media', 'certificate (1).png')
    logo_left_path = os.path.join(settings.BASE_DIR, 'apps', 'student_certificate', 'media', 'DevEx Hub logo.png')
    logo_right_path = os.path.join(settings.BASE_DIR, 'apps', 'student_certificate', 'media', '(accreditationpartner logo.png')
    
    # Convert windows paths for URI standard in WeasyPrint
    bg_path = bg_image_path.replace('\\', '/')
    if not bg_path.startswith('/'):
        bg_path = '/' + bg_path
        
    left_logo_uri = logo_left_path.replace('\\', '/')
    if not left_logo_uri.startswith('/'):
        left_logo_uri = '/' + left_logo_uri

    right_logo_uri = logo_right_path.replace('\\', '/')
    if not right_logo_uri.startswith('/'):
        right_logo_uri = '/' + right_logo_uri
        
    cert_content_text = certificate.cert_content or ""
    # Convert double asterisks to bold tag
    html_content = cert_content_text.replace('\n', '<br>')
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
    
    performance_heading = f"{his_her.capitalize()} Performance Given as Below"
    
    context = {
        'certificate': certificate,
        'bg_image_path': bg_path,
        'left_logo_path': left_logo_uri,
        'right_logo_path': right_logo_uri,
        'cert_content_html': html_content,
        'performance_heading': performance_heading,
        'he_she': he_she,
        'his_her': his_her,
        'skill_ratings': certificate.skill_ratings,
    }
    
    html_string = render_to_string('certificate/pdf_certificate_template.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    
    filename = f"cert_{certificate.serial_no.replace('|', '_')}.pdf"
    certificate.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
    certificate.save()
    
    # Backward compatibility with student's legacy cert_pdf field
    student.cert_pdf = certificate.pdf_file
    if student.status == 'ACTIVE':
        student.status = 'COMPLETED'
    student.save()
    
    return certificate

def send_fee_warning_email(installment):
    """
    Sends a soft, professional warning email to the student about overdue installment.
    """
    student = installment.student
    subject = STUDENT_FEES_WARNING_SUBJECT
    body = STUDENT_FEES_WARNING_BODY.format(
        student_name=student.name,
        installment_number=installment.installment_number,
        amount=installment.amount,
        due_date=installment.due_date.strftime("%d %B %Y")
    )
    
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        fail_silently=False
    )
    return True


def fetch_active_students_from_bitrix():
    """
    Fetches ALL active, currently enrolled STUDENTS ONLY from Bitrix24 CRM.
    
    **IMPORTANT**: This returns ONLY STUDENT data, NOT employee data.
    - Automatically filters out employee records
    - Employees and students are kept separate (different APIs)
    
    Returns:
        list: Student records that are:
              - Status: ACTIVE (not COMPLETED or DISCONTINUED)
              - Currently enrolled (completion_date > today)
              - STUDENT DATA ONLY (employees excluded)
              
    Usage:
        students = fetch_active_students_from_bitrix()
        for student in students:
            print(f"{student.get('NAME')} - {student.get('EMAIL')}")
    """
    return BitrixClient.get_active_students_from_crm(entity_type_id=1044)


def fetch_active_students_paginated(page_size=50, offset=0):
    """
    Fetches active STUDENTS ONLY with pagination support.
    
    **IMPORTANT**: This returns ONLY STUDENT data, NOT employee data.
    - Automatically filters out employee records from mixed data sources
    - Employees are managed via separate employee API
    
    Args:
        page_size: Number of records per page (default: 50)
        offset: Starting record position (default: 0)
        
    Returns:
        dict: Contains:
            - 'items': List of active STUDENT records ONLY (no employees)
            - 'next_offset': Next page offset for pagination (None if no more pages)
            - 'total_count': Total number of STUDENT records (employees excluded)
            
    Usage:
        # First page
        result = fetch_active_students_paginated(page_size=50, offset=0)
        students = result['items']  # Only students, no employees
        
        # Next page (if result['next_offset'] is not None)
        result = fetch_active_students_paginated(page_size=50, offset=result['next_offset'])
    """
    return BitrixClient.get_active_students_paginated(entity_type_id=1044, page_size=page_size, offset=offset)


def format_bitrix_student_data(bitrix_student_dict):
    """
    Formats raw Bitrix24 STUDENT data into a consistent format.
    
    **IMPORTANT**: Only use with student records, not employee records.
    This function assumes the input is student data with course/learning fields.
    
    Args:
        bitrix_student_dict: Raw STUDENT dict from Bitrix24 CRM API (not employee)
        
    Returns:
        dict: Formatted STUDENT data with extracted fields:
            - bitrix_id: Bitrix24 record ID
            - name: Student name
            - email: Student email
            - phone: Student phone
            - status: ACTIVE/COMPLETED/DISCONTINUED
            - joining_date: Course start date
            - completion_date: Course end date
            - institute: College/Institute name
            - course_name: Course being pursued
            - mentor: Assigned mentor
            - father_name: Father's name
            - raw_data: Original Bitrix24 record
        
    Usage:
        formatted = format_bitrix_student_data(raw_student)  # Must be student data
        print(formatted['email'])
        print(formatted['course_name'])
    """
    # Map gender
    gender_map = {970: 'MALE', 982: 'FEMALE', 984: 'OTHER', '970': 'MALE', '982': 'FEMALE', '984': 'OTHER'}
    raw_gender = bitrix_student_dict.get('GENDER') or bitrix_student_dict.get('UF_GENDER')
    gender = gender_map.get(raw_gender, 'MALE')

    # Map student type
    type_map = {96: 'TRAINEE', 98: 'INTERN', 100: 'PROJECT_STUDENT', 102: 'INDUSTRIAL_VISIT', '96': 'TRAINEE', '98': 'INTERN', '100': 'PROJECT_STUDENT', '102': 'INDUSTRIAL_VISIT'}
    raw_type = bitrix_student_dict.get('ufCrm6_1761732372') or bitrix_student_dict.get('STUDENT_TYPE') or bitrix_student_dict.get('UF_STUDENT_TYPE')
    student_type = type_map.get(raw_type, 'TRAINEE')

    # Map certificate type
    cert_map = {5798: 'TRAINING_CERT', 5800: 'INTERNSHIP_CERT', 5802: 'PROJECT_CERT', '5798': 'TRAINING_CERT', '5800': 'INTERNSHIP_CERT', '5802': 'PROJECT_CERT'}
    raw_cert = bitrix_student_dict.get('ufCrm6_1761734045') or bitrix_student_dict.get('CERT_TYPE') or bitrix_student_dict.get('UF_CERT_TYPE')
    cert_type = cert_map.get(raw_cert, 'TRAINING_CERT')

    # Map Address
    raw_address = bitrix_student_dict.get('ufCrm6_1761732143796') or bitrix_student_dict.get('ufCrm6_1761732115199') or bitrix_student_dict.get('ADDRESS') or bitrix_student_dict.get('UF_ADDRESS') or ''
    address = raw_address.split('|')[0] if raw_address else ''

    # Map DOB
    raw_dob = bitrix_student_dict.get('ufCrm6_1761732075408') or bitrix_student_dict.get('DOB') or bitrix_student_dict.get('UF_DOB') or ''
    dob = raw_dob[:10] if raw_dob else ''

    # Map Course Name
    raw_course = bitrix_student_dict.get('COURSE') or bitrix_student_dict.get('UF_COURSE_NAME') or bitrix_student_dict.get('ufCrm6_1761731874888') or ''
    course_map = {
        954: "MEAN",
        956: "MERN",
        958: "Web Designing",
        960: "Web Development",
        962: "Digital Marketing",
        964: "AI Development",
        '954': "MEAN",
        '956': "MERN",
        '958': "Web Designing",
        '960': "Web Development",
        '962': "Digital Marketing",
        '964': "AI Development"
    }
    course_name = course_map.get(raw_course, str(raw_course))

    return {
        'bitrix_id': bitrix_student_dict.get('ID') or bitrix_student_dict.get('id'),
        'name': (bitrix_student_dict.get('ufCrm6_1761817180597') or bitrix_student_dict.get('NAME') or bitrix_student_dict.get('title') or '').strip(),
        'email': bitrix_student_dict.get('EMAIL') or bitrix_student_dict.get('UF_EMAIL') or bitrix_student_dict.get('ufCrm6_1761731565702') or '',
        'phone': bitrix_student_dict.get('PHONE') or bitrix_student_dict.get('UF_PHONE') or bitrix_student_dict.get('ufCrm6_1761731546152') or '',
        'status': bitrix_student_dict.get('STATUS') or bitrix_student_dict.get('UF_STATUS') or 'ACTIVE',
        'joining_date': (bitrix_student_dict.get('UF_JOINING_DATE') or bitrix_student_dict.get('UF_START_DATE') or bitrix_student_dict.get('ufCrm6_1761735340146') or '')[:10],
        'completion_date': (bitrix_student_dict.get('UF_COMPLETION_DATE') or bitrix_student_dict.get('UF_END_DATE') or bitrix_student_dict.get('ufCrm6_1761735481170') or '')[:10],
        'institute': bitrix_student_dict.get('INSTITUTE') or bitrix_student_dict.get('UF_INSTITUTE') or bitrix_student_dict.get('ufCrm6_1761732176981') or '',
        'course_name': course_name,
        'mentor': bitrix_student_dict.get('MENTOR') or bitrix_student_dict.get('UF_MENTOR') or bitrix_student_dict.get('ufCrm6_1761815392532') or '',
        'father_name': bitrix_student_dict.get('FATHER_NAME') or bitrix_student_dict.get('UF_FATHER_NAME') or bitrix_student_dict.get('ufCrm6_1761731958409') or '',
        'total_fees': bitrix_student_dict.get('ufCrm6_1761732340679') or bitrix_student_dict.get('TOTAL_FEES') or bitrix_student_dict.get('total_fees') or '0',
        'gender': gender,
        'student_type': student_type,
        'cert_type': cert_type,
        'address': address,
        'dob': dob,
        'raw_data': bitrix_student_dict  # Keep raw data for reference
    }



def get_student_status_category(bitrix_student):
    """
    Determines the status category of a student based on Bitrix24 CRM pipeline stage.
    
    Stages:
    - COMPLETED: Final stage (UC_69T3IT) with past completion date
    - INCOMPLETE/FAILED: Explicitly marked as FAIL
    - ONGOING: All other stages (CLIENT, UC_8CP2UP, UC_QXBN3E, UC_10M2QN, UC_26OISW, etc.)
    
    Args:
        bitrix_student: Raw student dict from Bitrix24 CRM
        
    Returns:
        dict: {
            'status_category': 'COMPLETED' | 'INCOMPLETE' | 'ONGOING',
            'stage': Pipeline stage name,
            'reason': Explanation of categorization
        }
    """
    from datetime import datetime, date
    
    # Get the stage from the CRM
    stage = bitrix_student.get('stageId') or bitrix_student.get('STAGE_ID') or bitrix_student.get('UF_STAGE') or ''

    
    # Normalize stage (remove prefix if present)
    stage_normalized = stage.split(':')[-1] if stage else ''
    
    # Check completion date
    completion_date_str = bitrix_student.get('ufCrm6_1761735481170') or bitrix_student.get('UF_COMPLETION_DATE') or bitrix_student.get('closedate')

    completion_date = None
    
    if completion_date_str:
        try:
            completion_date = datetime.strptime(
                completion_date_str.split('T')[0] if 'T' in completion_date_str else completion_date_str,
                '%Y-%m-%d'
            ).date()
        except (ValueError, TypeError, AttributeError):
            pass
    
    today = date.today()
    
    # COMPLETED: Final stage UC_69T3IT with past completion date
    if 'UC_69T3IT' in stage_normalized or 'UC_69T3IT' in stage:
        if completion_date and completion_date <= today:
            return {
                'status_category': 'COMPLETED',
                'stage': stage,
                'stage_name': 'Final - Course Completed',
                'reason': f'Final pipeline stage (UC_69T3IT) with past completion date ({completion_date})',
                'completion_date': completion_date.isoformat() if completion_date else None
            }
    
    # INCOMPLETE/FAILED: Explicitly marked as FAIL
    if 'FAIL' in stage_normalized or 'FAIL' in stage:
        return {
            'status_category': 'INCOMPLETE',
            'stage': stage,
            'stage_name': 'Failed',
            'reason': 'Marked as FAIL in CRM',
            'completion_date': completion_date.isoformat() if completion_date else None
        }
    
    # ONGOING: All other stages
    return {
        'status_category': 'ONGOING',
        'stage': stage,
        'stage_name': get_stage_display_name(stage_normalized),
        'reason': f'In progress at stage: {stage_normalized}',
        'estimated_completion': completion_date.isoformat() if completion_date and completion_date > today else None
    }


def get_stage_display_name(stage_code):
    """
    Returns a human-readable name for a Bitrix24 CRM pipeline stage.
    """
    stage_names = {
        'CLIENT': 'Client/Inquiry',
        'UC_8CP2UP': 'Application Submitted',
        'UC_QXBN3E': 'Under Review',
        'UC_10M2QN': 'Enrollment Started',
        'UC_26OISW': 'Course Starting Soon',
        'UC_69T3IT': 'Course Completed',
        'FAIL': 'Failed/Discontinued'
    }
    return stage_names.get(stage_code, stage_code or 'Unknown')


def get_students_by_status_category():
    """
    Fetches all active students and categorizes them by status (Completed, Incomplete, Ongoing).
    
    Returns:
        dict: Summary with counts and detailed student lists
        {
            'summary': {
                'total': 45,
                'completed': 10,
                'incomplete': 4,
                'ongoing': 31
            },
            'students_by_status': {
                'COMPLETED': [
                    {
                        'bitrix_id': '110',
                        'name': 'John Doe',
                        'email': 'john@example.com',
                        'stage': 'UC_69T3IT',
                        'completion_date': '2026-03-19'
                    }
                ],
                'INCOMPLETE': [...],
                'ONGOING': [...]
            },
            'students_by_stage': {
                'UC_69T3IT': {'count': 10, 'students': [...]},
                'FAIL': {'count': 4, 'students': [...]},
                'CLIENT': {'count': 3, 'students': [...]},
                ...
            }
        }
    """
    students = fetch_active_students_from_bitrix()
    
    categorized = {
        'COMPLETED': [],
        'INCOMPLETE': [],
        'ONGOING': []
    }
    
    by_stage = {}
    
    for student in students:
        # Get status category
        status_info = get_student_status_category(student)
        status_category = status_info['status_category']
        stage = student.get('STAGE_ID') or student.get('UF_STAGE') or 'UNKNOWN'
        
        # Format student data
        formatted = format_bitrix_student_data(student)
        student_summary = {
            'bitrix_id': formatted['bitrix_id'],
            'name': formatted['name'],
            'email': formatted['email'],
            'phone': formatted['phone'],
            'stage': stage,
            'stage_name': status_info.get('stage_name'),
            'course_name': formatted['course_name'],
            'institute': formatted['institute'],
            'joining_date': formatted['joining_date'],
            'completion_date': formatted['completion_date'],
            'mentor': formatted['mentor'],
            'status_reason': status_info.get('reason')
        }
        
        # Add to category
        categorized[status_category].append(student_summary)
        
        # Add to stage grouping
        if stage not in by_stage:
            by_stage[stage] = {'stage_name': status_info.get('stage_name'), 'students': []}
        by_stage[stage]['students'].append(student_summary)
    
    # Count by stage
    stage_summary = {}
    for stage, stage_data in by_stage.items():
        stage_summary[stage] = {
            'count': len(stage_data['students']),
            'stage_name': stage_data['stage_name'],
            'student_ids': [s['bitrix_id'] for s in stage_data['students']]
        }
    
    return {
        'summary': {
            'total': len(students),
            'completed': len(categorized['COMPLETED']),
            'incomplete': len(categorized['INCOMPLETE']),
            'ongoing': len(categorized['ONGOING'])
        },
        'students_by_status': categorized,
        'stage_summary': stage_summary,
        'students_by_stage': by_stage
    }


def get_students_by_stage_detailed():
    """
    Returns detailed breakdown of students grouped by pipeline stage with statistics.
    
    Returns:
        dict: Detailed stage-wise breakdown with reasons and IDs
    """
    result = get_students_by_status_category()
    
    # Build detailed stage breakdown
    stage_breakdown = []
    for stage, stage_info in result['stage_summary'].items():
        students_in_stage = result['students_by_stage'].get(stage, {}).get('students', [])
        stage_code = stage.split(':')[-1] if ':' in stage else stage
        
        stage_breakdown.append({
            'stage_id': stage,
            'stage_code': stage_code,
            'stage_name': stage_info['stage_name'],
            'count': stage_info['count'],
            'student_ids': stage_info['student_ids'],
            'students': students_in_stage
        })
    
    return {
        'summary': result['summary'],
        'stage_breakdown': sorted(stage_breakdown, key=lambda x: x['count'], reverse=True),
        'status_summary': {
            '✅ Completed': {
                'count': result['summary']['completed'],
                'stage': 'UC_69T3IT',
                'description': 'Course finished, all milestones completed',
                'student_ids': [s['bitrix_id'] for s in result['students_by_status']['COMPLETED']]
            },
            '❌ Incomplete/Failed': {
                'count': result['summary']['incomplete'],
                'stage': 'FAIL',
                'description': 'Explicitly marked as failed or discontinued',
                'student_ids': [s['bitrix_id'] for s in result['students_by_status']['INCOMPLETE']]
            },
            '🔄 Ongoing': {
                'count': result['summary']['ongoing'],
                'stage': 'Multiple (CLIENT, UC_8CP2UP, UC_QXBN3E, UC_10M2QN, UC_26OISW)',
                'description': 'Currently enrolled or in various stages',
                'student_ids': [s['bitrix_id'] for s in result['students_by_status']['ONGOING']]
            }
        }
    }

