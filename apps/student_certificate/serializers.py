from rest_framework import serializers
from decimal import Decimal
from .models import Student, StudentFeeInstallment
from employee_onboarding.serializers import DepartmentSerializer

class StudentFeeInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentFeeInstallment
        fields = '__all__'
        read_only_fields = ('student', 'status', 'paid_amount', 'paid_date')


class StudentSerializer(serializers.ModelSerializer):
    installments = StudentFeeInstallmentSerializer(many=True, read_only=True)
    installments_schedule = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    training_duration = serializers.ReadOnlyField()
    department_details = DepartmentSerializer(source='department', read_only=True)

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
