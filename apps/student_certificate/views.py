import io
import zipfile
import datetime
from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from openpyxl import Workbook

from roles.permissions import HasModelPermission
from .models import Student, StudentFeeInstallment, Course, StudentCertificate
from .serializers import (
    StudentSerializer, StudentFeeInstallmentSerializer, CourseSerializer, StudentCertificateSerializer
)
from .services import generate_student_certificate_pdf, send_fee_warning_email

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('course_name')
    serializer_class = CourseSerializer
    permission_classes = [HasModelPermission]


class StudentCertificateViewSet(viewsets.ModelViewSet):
    queryset = StudentCertificate.objects.all().order_by('-created_at')
    serializer_class = StudentCertificateSerializer
    permission_classes = [HasModelPermission]

    @transaction.atomic
    def perform_create(self, serializer):
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
        instance = serializer.save(serial_no=serial_no)
        
        # Now trigger the PDF generation
        from .services import generate_student_certificate_pdf
        generate_student_certificate_pdf(instance)


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        queryset = Student.objects.all().order_by('-joining_date')
        status_param = self.request.query_params.get('status')
        student_type = self.request.query_params.get('student_type')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if student_type:
            queryset = queryset.filter(student_type=student_type)
        return queryset

    @action(detail=True, methods=['GET'], url_path='enrollment-details')
    def enrollment_details(self, request, pk=None):
        student = self.get_object()
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
        duration = course.default_duration if course else student.training_duration
        
        # Format completion month
        try:
            completion_month = student.completion_date.strftime("%B %Y")
        except:
            completion_month = ""
            
        address_str = student.address or ""
        father_name_str = student.father_name or ""
        
        # Default paragraph layouts
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
        student = self.get_object()
        confirm_override = request.data.get('confirm_override', False)
        
        # Check completion date warning rule
        today = datetime.date.today()
        if student.completion_date > today and not confirm_override:
            return Response({
                'warning': f"Warning: The completion date ({student.completion_date}) is in the future. Generating this certificate will complete their profile early. Do you wish to override?",
                'requires_override': True
            }, status=status.HTTP_200_OK) # return warning trigger payload
            
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
            duration = course.default_duration
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
                place="Mohali"
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
        
        students = Student.objects.all().order_by('-joining_date')
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
                        
                        default_content = (
                            f"This is to certify that **{student.name}** **{s_o_d_o} {father_name_str}**, {address_str}. "
                            f"Has successfully Completed {course.default_duration} \"**{course.course_name}**\" course ."
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
                                issue_date=datetime.date.today(),
                                serial_no=serial_no,
                                cert_content=default_content,
                                place="Mohali"
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

