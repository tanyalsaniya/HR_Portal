#!/usr/bin/env python
"""
Example script showing how to use the Active Students Bitrix24 integration.
Run from Django shell: python manage.py shell < example_active_students_usage.py
"""

import django
import os
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.student_certificate.services import (
    fetch_active_students_from_bitrix,
    fetch_active_students_paginated,
    format_bitrix_student_data
)
from apps.student_certificate.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("EXAMPLE 1: Fetch All Active Students (No Pagination)")
print("=" * 80)

try:
    students = fetch_active_students_from_bitrix()
    print(f"\n✓ Found {len(students)} active students\n")
    
    for i, student in enumerate(students[:5], 1):  # Show first 5
        formatted = format_bitrix_student_data(student)
        print(f"{i}. {formatted['name']}")
        print(f"   Email: {formatted['email']}")
        print(f"   Phone: {formatted['phone']}")
        print(f"   Joining: {formatted['joining_date']} → Completion: {formatted['completion_date']}")
        print(f"   Course: {formatted['course_name']}")
        print()
    
    if len(students) > 5:
        print(f"... and {len(students) - 5} more students\n")
        
except Exception as e:
    print(f"✗ Error: {str(e)}\n")


print("=" * 80)
print("EXAMPLE 2: Fetch with Pagination")
print("=" * 80)

try:
    page_size = 10
    offset = 0
    page = 1
    
    while True:
        result = fetch_active_students_paginated(page_size=page_size, offset=offset)
        students = result['items']
        next_offset = result['next_offset']
        total = result['total_count']
        
        if not students:
            break
        
        print(f"\nPage {page} (Showing {len(students)} of {total} total):")
        print("-" * 80)
        
        for i, student in enumerate(students[:3], 1):  # Show first 3 per page
            formatted = format_bitrix_student_data(student)
            print(f"  {i}. {formatted['name']} ({formatted['email']})")
        
        if len(students) > 3:
            print(f"  ... and {len(students) - 3} more on this page")
        
        # Check for next page
        if next_offset is None:
            break
        
        offset = next_offset
        page += 1
        
        if page >= 3:  # Show only first 3 pages as example
            print(f"\n... (showing first 3 pages)")
            break
            
except Exception as e:
    print(f"✗ Error: {str(e)}\n")


print("=" * 80)
print("EXAMPLE 3: Format Student Data")
print("=" * 80)

try:
    students = fetch_active_students_from_bitrix()
    if students:
        student = students[0]
        formatted = format_bitrix_student_data(student)
        
        print("\nFormatted Student Data:")
        print("-" * 80)
        print(f"Bitrix ID:       {formatted['bitrix_id']}")
        print(f"Name:            {formatted['name']}")
        print(f"Email:           {formatted['email']}")
        print(f"Phone:           {formatted['phone']}")
        print(f"Status:          {formatted['status']}")
        print(f"Institute:       {formatted['institute']}")
        print(f"Course:          {formatted['course_name']}")
        print(f"Joining Date:    {formatted['joining_date']}")
        print(f"Completion Date: {formatted['completion_date']}")
        print(f"Mentor:          {formatted['mentor']}")
        print(f"Father Name:     {formatted['father_name']}")
        print()
        
except Exception as e:
    print(f"✗ Error: {str(e)}\n")


print("=" * 80)
print("EXAMPLE 4: Sync Active Students to Database")
print("=" * 80)

try:
    # Get sample admin user (or any user)
    admin_user = User.objects.filter(is_staff=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    if not admin_user:
        print("✗ No users found in database. Skipping sync example.\n")
    else:
        students = fetch_active_students_from_bitrix()
        
        if students:
            print(f"\nSyncing {len(students[:3])} sample students to database...")
            print("-" * 80)
            
            created_count = 0
            updated_count = 0
            
            for bitrix_student in students[:3]:  # Sync first 3 as example
                try:
                    formatted = format_bitrix_student_data(bitrix_student)
                    email = formatted['email']
                    name = formatted['name']
                    
                    if email and name:
                        joining_date = datetime.datetime.strptime(
                            formatted['joining_date'].split('T')[0],
                            '%Y-%m-%d'
                        ).date() if formatted['joining_date'] else datetime.date.today()
                        
                        completion_date = datetime.datetime.strptime(
                            formatted['completion_date'].split('T')[0],
                            '%Y-%m-%d'
                        ).date() if formatted['completion_date'] else datetime.date.today() + datetime.timedelta(days=180)
                        
                        student_obj, created = Student.objects.update_or_create(
                            email=email,
                            defaults={
                                'name': name,
                                'phone': formatted['phone'] or '',
                                'institute': formatted['institute'] or '',
                                'course_at_institute': formatted['course_name'] or '',
                                'joining_date': joining_date,
                                'completion_date': completion_date,
                                'mentor': formatted['mentor'] or '',
                                'father_name': formatted['father_name'] or '',
                                'status': 'ACTIVE',
                                'student_type': 'TRAINEE',
                                'program_name': formatted['course_name'] or 'General',
                                'cert_type': 'TRAINING_CERT',
                                'created_by_id': admin_user.id if created else None,
                            }
                        )
                        
                        if created:
                            print(f"  ✓ Created: {name} ({email})")
                            created_count += 1
                        else:
                            print(f"  ↻ Updated: {name} ({email})")
                            updated_count += 1
                            
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
            
            print("-" * 80)
            print(f"Summary: {created_count} created, {updated_count} updated\n")
            
except Exception as e:
    print(f"✗ Error: {str(e)}\n")


print("=" * 80)
print("EXAMPLE 5: Generate Report of Active Students")
print("=" * 80)

try:
    students = fetch_active_students_from_bitrix()
    
    if students:
        # Group by course
        courses_dict = {}
        for student in students:
            formatted = format_bitrix_student_data(student)
            course = formatted['course_name'] or 'Unassigned'
            
            if course not in courses_dict:
                courses_dict[course] = []
            courses_dict[course].append(formatted)
        
        print("\nActive Students by Course:")
        print("-" * 80)
        
        for course, course_students in sorted(courses_dict.items()):
            print(f"\n{course}: {len(course_students)} students")
            for student in course_students[:2]:  # Show first 2 per course
                print(f"  • {student['name']} ({student['email']})")
            if len(course_students) > 2:
                print(f"  ... and {len(course_students) - 2} more")
        
        print()
        
except Exception as e:
    print(f"✗ Error: {str(e)}\n")


print("=" * 80)
print("Examples completed!")
print("=" * 80)
