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
from .models import Student, StudentFeeInstallment
from .serializers import StudentSerializer, StudentFeeInstallmentSerializer
from .services import generate_student_certificate_pdf, send_fee_warning_email

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
            generate_student_certificate_pdf(student, user=request.user)
            
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
                    generate_student_certificate_pdf(student, user=request.user)
                
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
