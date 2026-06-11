from rest_framework import serializers
from decimal import Decimal
from employee_onboarding.serializers import EmployeeSerializer
from .models import SalaryStructure, SalarySlip, SalaryIncrementReminder, SalaryIncrementApproval

class SalaryStructureSerializer(serializers.ModelSerializer):
    gross_salary = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    employee_details = EmployeeSerializer(source='employee', read_only=True)

    class Meta:
        model = SalaryStructure
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class SalarySlipSerializer(serializers.ModelSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    generated_by_username = serializers.ReadOnlyField(source='generated_by.username')

    class Meta:
        model = SalarySlip
        fields = '__all__'
        read_only_fields = ('payslip_no', 'lop_days', 'gross', 'total_deductions', 'net_pay', 'pdf_file', 'generated_by', 'generated_at')

    def validate(self, attrs):
        working_days = attrs.get('working_days')
        days_worked = attrs.get('days_worked')

        if days_worked > working_days:
            raise serializers.ValidationError({
                'days_worked': "Actual days worked cannot exceed total working days in the month."
            })

        return attrs


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
        
        # Fetch active salary structure to validate against current basic
        active_structure = SalaryStructure.objects.filter(employee=employee).order_by('-effective_from').first()
        if not active_structure:
            raise serializers.ValidationError("This employee does not have an active salary structure to increment.")
            
        new_basic = attrs.get('new_basic')
        if new_basic < Decimal(active_structure.basic):
            raise serializers.ValidationError({
                'new_basic': f"New basic salary (Rs. {new_basic}) must be greater than or equal to current basic salary (Rs. {active_structure.basic})."
            })
            
        return attrs
