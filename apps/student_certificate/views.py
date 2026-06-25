import io
import json
import zipfile
import datetime
import urllib.request
import urllib.parse
import re
from decimal import Decimal
from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from openpyxl import Workbook

from roles.permissions import HasModelPermission
from .models import Student, StudentFeeInstallment, Course, StudentCertificate, StudentDocument
from .serializers import (
    StudentSerializer, StudentFeeInstallmentSerializer, CourseSerializer, StudentCertificateSerializer, StudentDocumentSerializer
)
from .services import (
    generate_student_certificate_pdf, 
    send_fee_warning_email,
    fetch_active_students_from_bitrix,
    fetch_active_students_paginated,
    format_bitrix_student_data,
    get_students_by_status_category,
    get_students_by_stage_detailed
)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('course_name')
    serializer_class = CourseSerializer
    permission_classes = [HasModelPermission]
                                    

class StudentCertificateViewSet(viewsets.ModelViewSet):
    queryset = StudentCertificate.objects.all().order_by('-created_at')
    serializer_class = StudentCertificateSerializer
    permission_classes = [HasModelPermission]
 
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        from .utils import parse_duration_days, calculate_completed_duration
        
        student_id = request.data.get('student')
        if not student_id:
            return Response({'error': 'student is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # ----- Duration & Completion Date Calculation -----
        # Use duration from the payload (from the fixed dropdown)
        selected_duration = request.data.get('duration', '').strip()
        if selected_duration:
            days_to_add = parse_duration_days(selected_duration)
            new_completion_date = student.joining_date + datetime.timedelta(days=days_to_add)
            # Persist updated selected duration and completion_date on the student
            student.selected_duration = selected_duration
            student.completion_date = new_completion_date
            student.save(update_fields=['selected_duration', 'completion_date'])
        # ---------------------------------------------------
            
        confirm_override = request.data.get('confirm_override', False)
        early_generation_reason = request.data.get('early_generation_reason', '').strip()
        today = datetime.date.today()
        
        # Check completion date warning rule
        if student.completion_date > today:
            if not confirm_override:
                return Response({
                    'warning': "This student's course duration has not been completed yet. Are you sure you want to generate the certificate before the completion date?",
                    'requires_override': True
                }, status=status.HTTP_400_BAD_REQUEST)
            elif not early_generation_reason:
                return Response({
                    'error': "A valid reason must be provided for generating the certificate before the course completion date.",
                    'requires_reason': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        is_early = student.completion_date > today
        
        # Calculate completed duration & display date if early
        completed_duration = None
        display_completion_date = student.completion_date
        if is_early:
            completed_duration = calculate_completed_duration(student.joining_date, today)
            display_completion_date = today  # Show today as completion date on the certificate

        extra_args = {'display_completion_date': display_completion_date}
        if is_early:
            extra_args['early_generation_reason'] = early_generation_reason
            extra_args['calculated_completed_duration'] = completed_duration
        if request.user and request.user.is_authenticated:
            extra_args['generated_by'] = request.user

        self.perform_create(serializer, **extra_args)
        
        # Trigger Notification to Admins
        cert_instance = serializer.instance
        from notifications.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(role__code='ADMIN')
        
        username = request.user.username if request.user.is_authenticated else 'System'
        message = f"Certificate {cert_instance.serial_no} was generated for {student.name} by {username}."
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type='INFO',
                message=message,
                link=f"/students/{student.id}/"
            )
            
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

 
    @transaction.atomic
    def perform_create(self, serializer, **kwargs):
        student = serializer.validated_data['student']
        course = serializer.validated_data['course']
        
        # Get completion year for serial number
        completion_year = student.completion_date.year
        batch_code = str(completion_year)[-2:]
        batch_prefix = f"DHUB|{batch_code}|"
        
        # select_for_update to prevent race conditions and gaps
        last_cert = StudentCertificate.objects.filter(
            serial_no__startswith=batch_prefix
        ).select_for_update().order_by('-id').first()
        
        if last_cert:
            parts = last_cert.serial_no.split('|')
            if len(parts) >= 3:
                try:
                    next_seq = int(parts[2]) + 1
                except ValueError:
                    next_seq = 1
            else:
                next_seq = 1
        else:
            next_seq = 250
            
        serial_no = f"{batch_prefix}{next_seq}"
        
        # Save the certificate instance
        instance = serializer.save(serial_no=serial_no, **kwargs)
        
        # Now trigger the PDF generation
        from .services import generate_student_certificate_pdf
        generate_student_certificate_pdf(instance)



class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [HasModelPermission]

    def _get_filtered_queryset(self, queryset=None):
        queryset = queryset or Student.objects.all()
        queryset = queryset.order_by('-joining_date')

        status_param = self.request.query_params.get('status')
        student_type = self.request.query_params.get('student_type')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if student_type:
            queryset = queryset.filter(student_type=student_type)

        return queryset

    def get_queryset(self):
        return self._get_filtered_queryset()

    @action(detail=True, methods=['GET'], url_path='enrollment-details')
    def enrollment_details(self, request, pk=None):
        student = self.get_object()
        
        # Self-healing: try to fetch missing father's name or address from Bitrix24
        if not student.father_name or not student.address:
            try:
                bitrix_students = fetch_active_students_from_bitrix()
                for bs in bitrix_students:
                    formatted = format_bitrix_student_data(bs)
                    if formatted.get('email') == student.email:
                        updated = False
                        if not student.father_name and formatted.get('father_name'):
                            student.father_name = formatted.get('father_name')
                            updated = True
                        if not student.address and formatted.get('address'):
                            student.address = formatted.get('address')
                            updated = True
                        if updated:
                            student.save()
                        break
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Self-healing father_name fetch failed in enrollment_details: {e}")
                
        course = student.enrolled_course
        
        # Gender pronoun resolution
        gender = student.gender
        if gender == 'MALE':
            s_o_d_o = "S/O"
            he_she = "he"
            his_her = "his"
        elif gender == 'FEMALE':
            s_o_d_o = "D/O"
            he_she = "she"
            his_her = "her"
        else:
            s_o_d_o = "S/O or D/O"
            he_she = "he/she"
            his_her = "his/her"
            
        course_name = course.course_name if course else student.course_at_institute
        
        # Always return the FULL assigned duration (not shortened).
        # The frontend dropdown will handle display + early calculation.
        duration = student.training_duration or (course.default_duration if course else '6 Months')
        
        # Format completion month based on stored completion_date
        try:
            completion_month = student.completion_date.strftime("%B %Y")
        except:
            completion_month = ""
            
        address_str = student.address or ""
        father_name_str = student.father_name or ""
        
        # Default paragraph layouts (frontend recalculates when duration changes)
        default_paragraph = (
            f"This is to certify that **{student.name}** **{s_o_d_o} {father_name_str}**, {address_str}. "
            f"Has successfully Completed {duration} \"**{course_name}**\" course ."
        )
        
        default_paragraph_with_dates = (
            f"This is to certify that **{student.name}** **{s_o_d_o} {father_name_str}**, {address_str}. "
            f"Has successfully Completed \"**{course_name}**\" course in the month of **{completion_month}**."
        )

        skills = course.skills_list if course else []
        
        return Response({
            'student_id': student.id,
            'student_name': student.name,
            'gender': gender,
            'father_name': father_name_str,
            'address': address_str,
            'course_id': course.id if course else None,
            'course_name': course_name,
            'duration': duration,
            'joining_date': student.joining_date,
            'completion_date': student.completion_date,
            'completion_month': completion_month,
            's_o_d_o': s_o_d_o,
            'he_she': he_she,
            'his_her': his_her,
            'skills': skills,
            'default_paragraph': default_paragraph,
            'default_paragraph_with_dates': default_paragraph_with_dates,
        })

    @action(detail=True, methods=['POST'], url_path='generate-certificate')
    @transaction.atomic
    def generate_certificate(self, request, pk=None):
        from .utils import parse_duration_days, calculate_completed_duration
        student = self.get_object()
        
        # Self-healing: try to fetch missing father's name or address from Bitrix24
        if not student.father_name or not student.address:
            try:
                bitrix_students = fetch_active_students_from_bitrix()
                for bs in bitrix_students:
                    formatted = format_bitrix_student_data(bs)
                    if formatted.get('email') == student.email:
                        updated = False
                        if not student.father_name and formatted.get('father_name'):
                            student.father_name = formatted.get('father_name')
                            updated = True
                        if not student.address and formatted.get('address'):
                            student.address = formatted.get('address')
                            updated = True
                        if updated:
                            student.save()
                        break
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Self-healing father_name fetch failed in generate_certificate: {e}")

        confirm_override = request.data.get('confirm_override', False)
        early_generation_reason = request.data.get('early_generation_reason', '').strip()
        today = datetime.date.today()
        
        # ----- Duration & Completion Date Calculation -----
        selected_duration = request.data.get('duration', '').strip()
        if selected_duration:
            days_to_add = parse_duration_days(selected_duration)
            new_completion_date = student.joining_date + datetime.timedelta(days=days_to_add)
            student.selected_duration = selected_duration
            student.completion_date = new_completion_date
            student.save(update_fields=['selected_duration', 'completion_date'])
        # ---------------------------------------------------
        
        # Check completion date warning rule
        if student.completion_date > today:
            if not confirm_override:
                return Response({
                    'warning': "This student's course duration has not been completed yet. Are you sure you want to generate the certificate before the completion date?",
                    'requires_override': True
                }, status=status.HTTP_200_OK) # return warning trigger payload
            elif not early_generation_reason:
                return Response({
                    'error': "A valid reason must be provided for generating the certificate before the course completion date.",
                    'requires_reason': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            course = student.enrolled_course
            if not course:
                # Create a default course if none enrolled
                course, _ = Course.objects.get_or_create(
                    course_name=student.course_at_institute,
                    defaults={'default_duration': student.training_duration, 'skills_list': []}
                )
                student.enrolled_course = course
                student.save()
            
            # Resolve pronouns and default content
            gender = student.gender
            s_o_d_o = "D/O" if gender == 'FEMALE' else "S/O"
            father_name_str = student.father_name or ""
            address_str = student.address or ""
            
            completed_duration = None
            is_early = student.completion_date > today
            if is_early:
                completed_duration = calculate_completed_duration(student.joining_date, today)
                # Display shortened duration AND use today as the display completion date
                duration = completed_duration
                display_completion_date = today
            else:
                duration = student.training_duration or course.default_duration
                display_completion_date = student.completion_date
                
            course_name = course.course_name
            
            default_content = (
                f"This is to certify that **{student.name}** **{s_o_d_o} {father_name_str}**, {address_str}. "
                f"Has successfully Completed {duration} \"**{course_name}**\" course ."
            )
            
            ratings = {skill: 'Excellent' for skill in course.skills_list}
            
            # Get completion year for serial number
            completion_year = student.completion_date.year
            batch_code = str(completion_year)[-2:]
            batch_prefix = f"DHUB|{batch_code}|"
            
            last_cert = StudentCertificate.objects.filter(
                serial_no__startswith=batch_prefix
            ).select_for_update().order_by('-id').first()
            
            if last_cert:
                parts = last_cert.serial_no.split('|')
                if len(parts) >= 3:
                    try:
                        next_seq = int(parts[2]) + 1
                    except ValueError:
                        next_seq = 1
                else:
                    next_seq = 1
            else:
                next_seq = 250
                
            serial_no = f"{batch_prefix}{next_seq}"
            
            cert = StudentCertificate.objects.create(
                student=student,
                course=course,
                skill_ratings=ratings,
                show_dates=False,
                issue_date=today,
                serial_no=serial_no,
                cert_content=default_content,
                place="Mohali",
                display_completion_date=display_completion_date,
                early_generation_reason=early_generation_reason if is_early else None,
                calculated_completed_duration=completed_duration if is_early else None,
                generated_by=request.user if request.user and request.user.is_authenticated else None
            )
            
            # Generate PDF using WeasyPrint
            generate_student_certificate_pdf(cert)
            
            # Send notification to Admin (Admin will see in-app bell)
            from notifications.models import Notification
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(role__code='ADMIN')
            
            message = f"Certificate {student.cert_no} was generated for {student.name} by {request.user.username}."
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notif_type='INFO',
                    message=message,
                    link=f"/students/{student.id}/"
                )
                
            return Response({
                'message': 'Certificate generated successfully.',
                'cert_pdf': student.cert_pdf.url if student.cert_pdf else ""
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='send-certificate')
    def send_certificate(self, request, pk=None):
        student = self.get_object()
        if not student.cert_pdf:
            return Response({'error': 'Certificate PDF must be generated before sending.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Trigger Celery task
        from notifications.tasks import send_certificate_email
        send_certificate_email.delay(student.id)
        
        return Response({'message': 'Certificate email queued successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='export-excel')
    def export_excel(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Student Directory"
        
        # Headers
        headers = [
            "Cert No", "Student Name", "Email", "Phone", "Institute", 
            "Course", "Type", "Program Name", "Joining Date", 
            "Completion Date", "Mentor", "Fees (Rs.)", "Status"
        ]
        ws.append(headers)
        
        students = self._get_filtered_queryset()
        for student in students:
            ws.append([
                student.cert_no, student.name, student.email, student.phone or "", 
                student.institute, student.course_at_institute, student.get_student_type_display(),
                student.program_name, student.joining_date.strftime("%Y-%m-%d"), 
                student.completion_date.strftime("%Y-%m-%d"), student.mentor or "",
                float(student.total_fees), student.get_status_display()
            ])
            
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=students_directory.xlsx"
        return response

    @action(detail=False, methods=['POST'], url_path='bulk-generate')
    def bulk_generate_zip(self, request):
        student_ids = request.data.get('student_ids', [])
        if not student_ids:
            return Response({'error': 'No student IDs specified.'}, status=status.HTTP_400_BAD_REQUEST)
            
        students = Student.objects.filter(id__in=student_ids)
        if not students.exists():
            return Response({'error': 'No matching students found.'}, status=status.HTTP_400_BAD_REQUEST)
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for student in students:
                # Ensure certificate is generated
                if not student.cert_pdf:
                    # Look up latest student certificate or generate default
                    cert = StudentCertificate.objects.filter(student=student).order_by('-created_at').first()
                    if not cert:
                        # Create default
                        course = student.enrolled_course
                        if not course:
                            course, _ = Course.objects.get_or_create(
                                course_name=student.course_at_institute,
                                defaults={'default_duration': student.training_duration, 'skills_list': []}
                            )
                        
                        gender = student.gender
                        s_o_d_o = "D/O" if gender == 'FEMALE' else "S/O"
                        father_name_str = student.father_name or ""
                        address_str = student.address or ""
                        
                        today = datetime.date.today()
                        if student.completion_date > today:
                            from .utils import calculate_completed_duration
                            completed_duration = calculate_completed_duration(student.joining_date, today)
                            duration_str = completed_duration
                            early_gen_reason = "Bulk generated early"
                        else:
                            completed_duration = None
                            duration_str = course.default_duration
                            early_gen_reason = None
                        
                        default_content = (
                            f"This is to certify that **{student.name}** **{s_o_d_o} {father_name_str}**, {address_str}. "
                            f"Has successfully Completed {duration_str} \"**{course.course_name}**\" course ."
                        )
                        
                        completion_year = student.completion_date.year
                        batch_code = str(completion_year)[-2:]
                        batch_prefix = f"DHUB|{batch_code}|"
                        
                        with transaction.atomic():
                            last_cert = StudentCertificate.objects.filter(
                                serial_no__startswith=batch_prefix
                            ).select_for_update().order_by('-id').first()
                            
                            if last_cert:
                                parts = last_cert.serial_no.split('|')
                                if len(parts) >= 3:
                                    try:
                                        next_seq = int(parts[2]) + 1
                                    except ValueError:
                                        next_seq = 1
                                else:
                                    next_seq = 1
                            else:
                                next_seq = 250
                                
                            serial_no = f"{batch_prefix}{next_seq}"
                            
                            cert = StudentCertificate.objects.create(
                                student=student,
                                course=course,
                                skill_ratings={skill: 'Excellent' for skill in course.skills_list},
                                show_dates=False,
                                issue_date=today,
                                serial_no=serial_no,
                                cert_content=default_content,
                                place="Mohali",
                                early_generation_reason=early_gen_reason,
                                calculated_completed_duration=completed_duration,
                                generated_by=request.user if request.user and request.user.is_authenticated else None
                            )
                        generate_student_certificate_pdf(cert)
                    else:
                        generate_student_certificate_pdf(cert)
                
                # Add to ZIP
                if student.cert_pdf:
                    pdf_path = student.cert_pdf.path
                    arcname = f"{student.cert_no}_{student.name.replace(' ', '_')}.pdf"
                    zip_file.write(pdf_path, arcname=arcname)
                    
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=certificates.zip'
        return response

    @action(detail=False, methods=['GET'], url_path='active-from-bitrix')
    def fetch_active_from_bitrix(self, request):
        """
        Fetches ONLY active, currently enrolled STUDENTS from Bitrix24 CRM.
        
        **IMPORTANT**: This endpoint returns ONLY STUDENT data, NOT employee data.
        - Automatically separates and filters out employee records
        - Students and employees are managed via different APIs
        - Only students with learning/course fields are included
        
        Returns:
            - Students with status = ACTIVE (not COMPLETED or DISCONTINUED)
            - Students currently enrolled (completion_date > today)
            - STUDENT DATA ONLY (employees excluded)
            
        Query Parameters:
            - paginate (bool): Use pagination. Defaults to False (fetch all)
            - page_size (int): Records per page. Defaults to 50
            - offset (int): Starting position. Defaults to 0
            - format_data (bool): Format the data. Defaults to True
            
        Examples:
            GET /api/students/active-from-bitrix/  (All students, no employees)
            GET /api/students/active-from-bitrix/?paginate=true&page_size=50&offset=0
            
        Response:
            {
              "count": 25,
              "students": [
                {
                  "bitrix_id": "1044",
                  "name": "John Doe",
                  "email": "john@example.com",
                  "course_name": "Python Development",
                  ...
                }
              ]
            }
        """
        try:
            use_pagination = request.query_params.get('paginate', '').lower() == 'true'
            page_size = int(request.query_params.get('page_size', 50))
            offset = int(request.query_params.get('offset', 0))
            format_data = request.query_params.get('format_data', 'true').lower() == 'true'
            
            if use_pagination:
                result = fetch_active_students_paginated(page_size=page_size, offset=offset)
                students = result.get('items', [])
                next_offset = result.get('next_offset')
            else:
                students = fetch_active_students_from_bitrix()
                next_offset = None
            
            # Format data if requested
            if format_data:
                formatted_students = [format_bitrix_student_data(s) for s in students]
            else:
                formatted_students = students
            
            response_data = {
                'count': len(formatted_students),
                'students': formatted_students
            }
            
            if use_pagination:
                response_data['next_offset'] = next_offset
                response_data['has_more'] = next_offset is not None
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching active students from Bitrix: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to fetch active students: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['POST'], url_path='sync-active-from-bitrix')
    @transaction.atomic
    def sync_active_from_bitrix(self, request):
        """
        Syncs active STUDENTS ONLY from Bitrix24 CRM into the local Student model.
        
        **IMPORTANT**: This syncs ONLY STUDENT data, NOT employee data.
        - Automatically filters out employee records
        - Creates new Student records for students not yet in the database
        - Updates existing records if their data has changed
        - Employees are synced via separate API/endpoint
        
        Request Body (required fields):
            {
                "department_id": 1,              // Required: Department ID
                "created_by_id": 1,             // Required: User ID of the importer
                "auto_enroll_course": false,    // Optional: Auto-enroll in a course
                "course_id": 1                  // Optional: Course ID (if auto_enroll_course is true)
            }
            
        Returns:
            Summary of sync operation including created, updated, and skipped records.
            (Skipped = no student fields or employee data)
            
        Example:
            POST /api/students/sync-active-from-bitrix/
            {
              "department_id": 1,
              "created_by_id": 5,
              "auto_enroll_course": true,
              "course_id": 3
            }
            
        Response:
            {
              "message": "Sync completed successfully",
              "created": 12,
              "updated": 3,
              "skipped": 0,
              "total_imported": 15
            }
        """
        try:
            department_id = request.data.get('department_id')
            created_by_id = request.data.get('created_by_id')
            
            if not department_id or not created_by_id:
                return Response(
                    {'error': 'department_id and created_by_id are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            auto_enroll_course = request.data.get('auto_enroll_course', False)
            course_id = request.data.get('course_id')
            
            # Fetch active students from Bitrix
            bitrix_students = fetch_active_students_from_bitrix()
            
            if not bitrix_students:
                return Response(
                    {'message': 'No active students found in Bitrix24 CRM'}, 
                    status=status.HTTP_200_OK
                )
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            for bitrix_student in bitrix_students:
                try:
                    email = bitrix_student.get('EMAIL') or bitrix_student.get('UF_EMAIL')
                    name = bitrix_student.get('NAME') or ''
                    
                    if not email or not name:
                        skipped_count += 1
                        continue
                    
                    # Format the data
                    formatted = format_bitrix_student_data(bitrix_student)
                    
                    # Check if student exists
                    dob_val = None
                    if formatted.get('dob'):
                        try:
                            dob_val = datetime.datetime.strptime(formatted.get('dob').split('T')[0], '%Y-%m-%d').date()
                        except ValueError:
                            pass

                    student, created = Student.objects.update_or_create(
                        email=email,
                        defaults={
                            'name': name,
                            'phone': formatted.get('phone', ''),
                            'institute': formatted.get('institute', ''),
                            'course_at_institute': formatted.get('course_name', ''),
                            'joining_date': datetime.datetime.strptime(
                                formatted.get('joining_date', '2024-01-01').split('T')[0],
                                '%Y-%m-%d'
                            ).date() if formatted.get('joining_date') else datetime.date.today(),
                            'completion_date': datetime.datetime.strptime(
                                formatted.get('completion_date', '2024-12-31').split('T')[0],
                                '%Y-%m-%d'
                            ).date() if formatted.get('completion_date') else datetime.date.today() + datetime.timedelta(days=180),
                            'mentor': formatted.get('mentor', ''),
                            'father_name': formatted.get('father_name', ''),
                            'status': 'ACTIVE',
                            'student_type': formatted.get('student_type', 'TRAINEE'),
                            'program_name': formatted.get('course_name', 'General'),
                            'cert_type': formatted.get('cert_type', 'TRAINING_CERT'),
                            'department_id': department_id,
                            'created_by_id': created_by_id if created else None,
                            'gender': formatted.get('gender', 'MALE'),
                            'address': formatted.get('address', ''),
                            'dob': dob_val,
                            'total_fees': Decimal(re.sub(r'[^\d.]', '', str(formatted.get('total_fees', '0'))) or '0') if formatted.get('total_fees') else Decimal('0.00'),
                        }
                    )
                    
                    if auto_enroll_course and course_id:
                        student.enrolled_course_id = course_id
                        student.save()
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error syncing student {bitrix_student.get('NAME')}: {str(e)}")
                    skipped_count += 1
                    continue
            
            return Response({
                'message': f'Sync completed successfully',
                'created': created_count,
                'updated': updated_count,
                'skipped': skipped_count,
                'total_processed': created_count + updated_count + skipped_count,
                'total_imported': created_count + updated_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error syncing active students from Bitrix: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Sync failed: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['GET'], url_path='status-summary')
    def status_summary(self, request):
        """
        Returns a summary of students grouped by completion status.
        
        Returns students in three categories:
        - COMPLETED: Finished courses (stage: UC_69T3IT with past completion date)
        - INCOMPLETE: Failed/discontinued (stage: FAIL)
        - ONGOING: Currently enrolled (all other stages)
        
        Example:
            GET /api/students/status-summary/
            
        Response:
            {
              "summary": {
                "total": 45,
                "completed": 10,
                "incomplete": 4,
                "ongoing": 31
              },
              "students_by_status": {
                "COMPLETED": [...],
                "INCOMPLETE": [...],
                "ONGOING": [...]
              },
              "stage_summary": {
                "UC_69T3IT": {"count": 10, "student_ids": [...]},
                "FAIL": {"count": 4, "student_ids": [...]}
              }
            }
        """
        try:
            result = get_students_by_status_category()
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching status summary: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to fetch status summary: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['GET'], url_path='stage-breakdown')
    def stage_breakdown(self, request):
        """
        Returns detailed stage-wise breakdown of students.
        
        Shows students grouped by their pipeline stage with detailed information:
        - ✅ Completed: UC_69T3IT stage (finished courses)
        - ❌ Incomplete/Failed: FAIL stage (discontinued students)
        - 🔄 Ongoing: CLIENT, UC_8CP2UP, UC_QXBN3E, UC_10M2QN, UC_26OISW (various stages)
        
        Example:
            GET /api/students/stage-breakdown/
            
        Response:
            {
              "summary": {"total": 45, "completed": 10, "incomplete": 4, "ongoing": 31},
              "stage_breakdown": [
                {
                  "stage_id": "DT1044_20:UC_69T3IT",
                  "stage_code": "UC_69T3IT",
                  "stage_name": "Final - Course Completed",
                  "count": 10,
                  "student_ids": ["110", "114", "116", ...],
                  "students": [...]
                },
                {
                  "stage_id": "DT1044_20:FAIL",
                  "stage_code": "FAIL",
                  "stage_name": "Failed",
                  "count": 4,
                  "student_ids": ["136", "276", "278", "280"],
                  "students": [...]
                }
              ],
              "status_summary": {
                "✅ Completed": {"count": 10, "stage": "UC_69T3IT", "student_ids": [...]},
                "❌ Incomplete/Failed": {"count": 4, "stage": "FAIL", "student_ids": [...]},
                "🔄 Ongoing": {"count": 31, "stage": "Multiple...", "student_ids": [...]}
              }
            }
        """
        try:
            result = get_students_by_stage_detailed()
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching stage breakdown: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to fetch stage breakdown: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['GET'], url_path='status-stats')
    def status_stats(self, request):
        """
        Quick statistics endpoint for student status distribution.
        
        Returns lightweight summary for dashboards and quick stats display.
        
        Example:
            GET /api/students/status-stats/
            
        Response:
            {
              "total_students": 45,
              "completed": {"count": 10, "percentage": 22.2, "student_ids": [...]},
              "incomplete": {"count": 4, "percentage": 8.9, "student_ids": [...]},
              "ongoing": {"count": 31, "percentage": 68.9, "student_ids": [...]}
            }
        """
        try:
            result = get_students_by_status_category()
            summary = result['summary']
            total = summary['total']
            
            stats = {
                'total_students': total,
                'completed': {
                    'count': summary['completed'],
                    'percentage': round((summary['completed'] / total * 100), 1) if total > 0 else 0,
                    'student_ids': [s['bitrix_id'] for s in result['students_by_status']['COMPLETED']]
                },
                'incomplete': {
                    'count': summary['incomplete'],
                    'percentage': round((summary['incomplete'] / total * 100), 1) if total > 0 else 0,
                    'student_ids': [s['bitrix_id'] for s in result['students_by_status']['INCOMPLETE']]
                },
                'ongoing': {
                    'count': summary['ongoing'],
                    'percentage': round((summary['ongoing'] / total * 100), 1) if total > 0 else 0,
                    'student_ids': [s['bitrix_id'] for s in result['students_by_status']['ONGOING']]
                }
            }
            
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching status stats: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to fetch status stats: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['POST'], url_path='get-or-create-from-bitrix')
    @transaction.atomic
    def get_or_create_from_bitrix(self, request):
        email = request.data.get('email')
        name = request.data.get('name')
        if not email or not name:
            return Response({'error': 'name and email are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        bitrix_id = request.data.get('id')
        phone = request.data.get('phone', '')
        institute = request.data.get('institute', '')
        course_name = request.data.get('course_name') or request.data.get('course_at_institute') or 'General'
        course_name = str(course_name)
        joining_date_str = request.data.get('start_date') or request.data.get('joining_date')
        completion_date_str = request.data.get('completion_date')
        father_name = request.data.get('father_name', '')
        total_fees = request.data.get('total_fees', '0')
        dob_str = request.data.get('dob')
        gender = request.data.get('gender', 'MALE')
        address = request.data.get('address', '')
        student_type = request.data.get('student_type', 'TRAINEE')
        cert_type = request.data.get('cert_type', 'TRAINING_CERT')
        
        # Parse dates
        today = datetime.date.today()
        
        completion_date = None
        if completion_date_str:
            try:
                completion_date = datetime.datetime.strptime(completion_date_str.split('T')[0], '%Y-%m-%d').date()
            except ValueError:
                pass
                
        joining_date = None
        if joining_date_str:
            try:
                joining_date = datetime.datetime.strptime(joining_date_str.split('T')[0], '%Y-%m-%d').date()
            except ValueError:
                pass

        dob = None
        if dob_str:
            try:
                dob = datetime.datetime.strptime(dob_str.split('T')[0], '%Y-%m-%d').date()
            except ValueError:
                pass

        # Handle missing dates logically
        if not joining_date and not completion_date:
            joining_date = today
            completion_date = today + datetime.timedelta(days=180)
        elif not joining_date:
            joining_date = completion_date - datetime.timedelta(days=180)
        elif not completion_date:
            completion_date = joining_date + datetime.timedelta(days=180)

        # Find or create department
        from employee_onboarding.models import Department
        dept = Department.objects.filter(name__iexact="Training").first()
        if not dept:
            dept = Department.objects.filter(name__iexact="Software Engineering").first()
        if not dept:
            dept = Department.objects.first()
        if not dept:
            dept = Department.objects.create(name="Training")
            
        # Find or create course
        course = Course.objects.filter(course_name__iexact=course_name).first()
        if not course:
            course = Course.objects.create(
                course_name=course_name,
                default_duration="6 months",
                skills_list=["Java", "Python", "Web Development"]
            )

        # Determine days to add based on course duration
        duration_str = course.default_duration.lower()
        days_to_add = 180
        if 'month' in duration_str:
            try:
                months = int(''.join(filter(str.isdigit, duration_str)) or '6')
                days_to_add = months * 30
            except ValueError:
                pass
        elif 'week' in duration_str:
            try:
                weeks = int(''.join(filter(str.isdigit, duration_str)) or '4')
                days_to_add = weeks * 7
            except ValueError:
                pass
        elif 'day' in duration_str:
            try:
                days_to_add = int(''.join(filter(str.isdigit, duration_str)) or '180')
            except ValueError:
                pass

        # Handle missing dates logically
        if joining_date and completion_date and joining_date >= completion_date:
            completion_date = None

        if not joining_date and not completion_date:
            joining_date = today
            completion_date = today + datetime.timedelta(days=days_to_add)
        elif not joining_date:
            joining_date = completion_date - datetime.timedelta(days=days_to_add)
        elif not completion_date:
            completion_date = joining_date + datetime.timedelta(days=days_to_add)

        # Parse total fees robustly (removing currency formatting like "Rs. 20,000", commas, etc.)
        parsed_fees = Decimal('0.00')
        if total_fees:
            import re
            cleaned_fees_str = re.sub(r'[^\d.]', '', str(total_fees))
            if cleaned_fees_str:
                try:
                    parsed_fees = Decimal(cleaned_fees_str)
                except Exception:
                    pass

        student, created = Student.objects.update_or_create(
            email=email,
            defaults={
                'name': name,
                'phone': phone,
                'institute': institute,
                'course_at_institute': course_name,
                'enrolled_course': course,
                'joining_date': joining_date,
                'completion_date': completion_date,
                'father_name': father_name,
                'status': 'ACTIVE',
                'student_type': student_type or 'TRAINEE',
                'program_name': course_name,
                'cert_type': cert_type or 'TRAINING_CERT',
                'department': dept,
                'total_fees': parsed_fees,
                'dob': dob,
                'gender': gender or 'MALE',
                'address': address,
                'created_by': request.user if request.user.is_authenticated else None
            }
        )

        return Response({
            'id': student.id,
            'name': student.name,
            'email': student.email,
            'cert_no': student.cert_no
        }, status=status.HTTP_200_OK)


class StudentFeeInstallmentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentFeeInstallmentSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        queryset = StudentFeeInstallment.objects.all().order_by('due_date')
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        return queryset

    @action(detail=True, methods=['POST'], url_path='record-payment')
    @transaction.atomic
    def record_payment(self, request, pk=None):
        installment = self.get_object()
        amount_paid = request.data.get('amount_paid')
        remarks = request.data.get('remarks', '')
        
        if not amount_paid:
            return Response({'error': 'amount_paid is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            payment = Decimal(str(amount_paid))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid payment amount.'}, status=status.HTTP_400_BAD_REQUEST)
            
        installment.paid_amount += payment
        installment.paid_date = datetime.date.today()
        installment.remarks = remarks
        
        if installment.paid_amount >= installment.amount:
            installment.status = 'PAID'
        else:
            installment.status = 'PARTIALLY_PAID'
            
        installment.save()
        
        # Trigger Notification to Admins
        from notifications.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(role__code='ADMIN')
        
        message = f"Installment {installment.installment_number} payment of Rs. {payment} recorded for Student {installment.student.name}."
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type='INFO',
                message=message,
                link=f"/students/{installment.student.id}/"
            )
            
        return Response(StudentFeeInstallmentSerializer(installment).data)

    @action(detail=True, methods=['POST'], url_path='send-warning')
    def send_warning(self, request, pk=None):
        installment = self.get_object()
        if installment.status == 'PAID':
            return Response({'error': 'This installment is already fully paid.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            send_fee_warning_email(installment)
            return Response({'message': 'Fee warning email sent successfully to the student.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BitrixActiveStudentsView(APIView):
    """Fetch only currently enrolled (ongoing) students from Bitrix24 API. No DB storage."""
    permission_classes = [HasModelPermission]

    BITRIX_URL = "https://devexhub.bitrix24.in/rest/1/y1t21isqgj5qw1mc/crm.item.list.json"
    ENTITY_TYPE_ID = 1044

    # Stages that mean the student is NO LONGER active (completed / failed only)
    # Only EXCLUDE completed and failed stages
    EXCLUDED_STAGES = {
        'DT1044_20:FAIL',        # Dropped out / failed
        'DT1044_20:UC_69T3IT',   # Course completed
    }
    
    # ONGOING stages (students we WANT to show):
    # CLIENT, UC_8CP2UP, UC_QXBN3E, UC_10M2QN, UC_26OISW
    INCLUDED_STAGES = {
        'DT1044_20:CLIENT',      # Inquiry/Lead stage
        'DT1044_20:UC_8CP2UP',   # Application Submitted
        'DT1044_20:UC_QXBN3E',   # Under Review
        'DT1044_20:UC_10M2QN',   # Enrollment Started
        'DT1044_20:UC_26OISW',   # Course Starting Soon
    }

    def _is_currently_enrolled(self, item):
        """Return True only if the student is in an ongoing stage (not completed or failed)."""
        stage = item.get('stageId', '')
        
        # Exclude completed and failed students
        if stage in self.EXCLUDED_STAGES:
            return False
        
        # Safety net: exclude if stage contains FAIL
        if 'FAIL' in stage.upper():
            return False
        
        # Include if in included ongoing stages
        if stage in self.INCLUDED_STAGES:
            return True
        
        # Default: exclude if not explicitly included (safety net for unknown stages)
        return False

    def get(self, request):
        try:
            start = request.query_params.get('start', 0)
            try:
                start = int(start)
            except ValueError:
                start = 0

            limit = request.query_params.get('limit', 10)
            try:
                limit = int(limit)
            except ValueError:
                limit = 10

            # Bitrix24 REST API requires the 'start' parameter to be a multiple of 50.
            # We calculate the nearest lower multiple of 50 for Bitrix and slice the rest.
            bitrix_start = (start // 50) * 50
            relative_start = start - bitrix_start

            from django.core.cache import cache
            force_refresh = request.GET.get('refresh', '').lower() == 'true'
            cache_key = f'bitrix_active_students_list_page_{start}'
            
            if not force_refresh:
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    return Response(cached_data)

            import requests
            payload = {
                'entityTypeId': self.ENTITY_TYPE_ID,
                'start': bitrix_start,
                'limit': 50, # Bitrix default/max limit
                'filter': {
                    'stageId': list(self.INCLUDED_STAGES)
                },
                'select': ['*', 'uf_*']
            }
            
            response = requests.post(self.BITRIX_URL, json=payload, timeout=30)
            if response.status_code != 200:
                return Response(
                    {'error': f"Bitrix API returned {response.status_code}: {response.text}"},
                    status=status.HTTP_502_BAD_GATEWAY
                )

            data = response.json()
            items = data.get('result', {}).get('items', [])
            total = data.get('total', len(items))
            active_students = []
            for item in items:
                formatted = format_bitrix_student_data(item)
                active_students.append({
                    'id': formatted.get('bitrix_id'),
                    'name': formatted.get('name'),
                    'email': formatted.get('email'),
                    'phone': formatted.get('phone'),
                    'course_id': formatted.get('course_name'),
                    'start_date': formatted.get('joining_date'),
                    'completion_date': formatted.get('completion_date'),
                    'father_name': formatted.get('father_name'),
                    'institute': formatted.get('institute'),
                    'total_fees': formatted.get('total_fees'),
                    'stage': item.get('stageId', ''),
                    'dob': formatted.get('dob'),
                    'gender': formatted.get('gender'),
                    'address': formatted.get('address'),
                    'student_type': formatted.get('student_type'),
                    'cert_type': formatted.get('cert_type'),
                })

            active_students = active_students[relative_start : relative_start + limit]

            if start + limit < total:
                next_offset = start + limit
            else:
                next_offset = None

            response_data = {
                'count': len(active_students),
                'total': total,
                'results': active_students,
                'next': next_offset
            }
            
            # Cache the response for 5 minutes (300 seconds)
            cache.set(cache_key, response_data, 300)

            return Response(response_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)



class StudentDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentDocumentSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        queryset = StudentDocument.objects.all().order_by('-upload_date')
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

