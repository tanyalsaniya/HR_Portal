from rest_framework import serializers
from decimal import Decimal
from employee_onboarding.serializers import EmployeeSerializer
from .models import SalaryStructure, SalarySlip, SalaryImportBatch, SalaryIncrementReminder, SalaryIncrementApproval

class SalaryImportBatchSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.ReadOnlyField(source='uploaded_by.username')

    class Meta:
        model = SalaryImportBatch
        fields = '__all__'


class SalaryStructureSerializer(serializers.ModelSerializer):
    total_deductions = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    employee_details = EmployeeSerializer(source='employee', read_only=True)

    class Meta:
        model = SalaryStructure
        fields = '__all__'


class SalarySlipSerializer(serializers.ModelSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    uploaded_batch_details = SalaryImportBatchSerializer(source='uploaded_batch', read_only=True)

    class Meta:
        model = SalarySlip
        fields = '__all__'
        read_only_fields = (
            'total_deductions', 'net_salary',
            'pdf_file', 'payslip_no', 'created_at', 'updated_at'
        )


class SalaryIncrementReminderSerializer(serializers.ModelSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    actioned_by_username = serializers.ReadOnlyField(source='actioned_by.username')

    class Meta:
        model = SalaryIncrementReminder
        fields = '__all__'


class SalaryIncrementApprovalSerializer(serializers.ModelSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    approved_by_username = serializers.ReadOnlyField(source='approved_by.username')

    class Meta:
        model = SalaryIncrementApproval
        fields = '__all__'
        read_only_fields = ('approved_by', 'approved_at', 'pdf_file', 'old_net', 'new_net', 'increment_amount', 'increment_pct')

    def validate_reason(self, value):
        if value and len(value.strip()) < 20:
            raise serializers.ValidationError("Increment reason must be at least 20 characters long.")
        return value

    def validate(self, attrs):
        employee = attrs.get('employee')
        
        # Fetch active salary structure to validate against current gross
        active_structure = SalaryStructure.objects.filter(employee=employee).order_by('-effective_from').first()
        if not active_structure:
            raise serializers.ValidationError("This employee does not have an active salary structure to increment.")
            
        new_basic = attrs.get('new_basic')
        if new_basic < Decimal(active_structure.gross_salary):
            raise serializers.ValidationError({
                'new_basic': f"New gross salary (Rs. {new_basic}) must be greater than or equal to current gross salary (Rs. {active_structure.gross_salary})."
            })
            
        return attrs
