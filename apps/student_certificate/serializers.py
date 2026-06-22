from rest_framework import serializers
from decimal import Decimal
from .models import Student, StudentFeeInstallment, Course, StudentCertificate, StudentDocument
from employee_onboarding.serializers import DepartmentSerializer

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'


class StudentFeeInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentFeeInstallment
        fields = '__all__'
        read_only_fields = ('student', 'status', 'paid_amount', 'paid_date')


class StudentDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.ReadOnlyField(source='uploaded_by.username')
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentDocument
        fields = '__all__'
        read_only_fields = ('uploaded_by', 'upload_date')

    def get_file_name(self, obj):
        return obj.file.name.split('/')[-1] if obj.file else ""

    def validate_file(self, value):
        from rules import MAX_DOCUMENT_SIZE_BYTES
        if value.size > MAX_DOCUMENT_SIZE_BYTES:
            raise serializers.ValidationError("File size must be less than 10 MB.")
            
        allowed_extensions = ['.pdf', '.jpeg', '.jpg', '.png']
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError("Only PDF, JPEG, and PNG files are allowed.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['uploaded_by'] = request.user
        return super().create(validated_data)


class StudentSerializer(serializers.ModelSerializer):
    installments = StudentFeeInstallmentSerializer(many=True, read_only=True)
    documents = StudentDocumentSerializer(many=True, read_only=True)
    installments_schedule = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    training_duration = serializers.ReadOnlyField()
    department_details = DepartmentSerializer(source='department', read_only=True)
    enrolled_course_details = CourseSerializer(source='enrolled_course', read_only=True)

    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ('cert_no', 'cert_pdf', 'status', 'created_by', 'created_at')

    def create(self, validated_data):
        schedule = validated_data.pop('installments_schedule', [])
        
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
            
        student = super().create(validated_data)
        
        # Initialize fee installments from schedule
        for idx, item in enumerate(schedule, start=1):
            StudentFeeInstallment.objects.create(
                student=student,
                installment_number=idx,
                amount=Decimal(str(item.get('amount', 0))),
                due_date=item.get('due_date'),
                status='UNPAID'
            )
            
        # Trigger welcome email task (Trigger 22)
        try:
            from .tasks import send_student_welcome_email
            send_student_welcome_email.delay(student.id)
        except Exception:
            pass
            
        return student


class StudentCertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.name')
    course_name = serializers.ReadOnlyField(source='course.course_name')

    class Meta:
        model = StudentCertificate
        fields = '__all__'
        read_only_fields = ('serial_no', 'pdf_file', 'created_at')

