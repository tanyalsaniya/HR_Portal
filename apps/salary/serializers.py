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
    employee_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SalaryStructure
        fields = '__all__'

    def get_employee_details(self, obj):
        from common.bitrix_client import BitrixClient
        user = BitrixClient.get_user_detail(obj.bitrix_user_id)
        if user:
            return EmployeeSerializer(user).data
        return None


class SalarySlipSerializer(serializers.ModelSerializer):
    employee_details = serializers.SerializerMethodField(read_only=True)
    uploaded_batch_details = SalaryImportBatchSerializer(source='uploaded_batch', read_only=True)

    gross_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_credited_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    pf_contribution = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    esi = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    labour_welfare_fund = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    professional_tax = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    other_deductions = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    leaves_available = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    working_days = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    extra_days = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = SalarySlip
        fields = '__all__'
        read_only_fields = (
            'total_deductions', 'net_salary', 'net_credited_amount', 'gross_salary',
            'pdf_file', 'payslip_no', 'created_at', 'updated_at'
        )

    def get_employee_details(self, obj):
        from common.bitrix_client import BitrixClient
        user = BitrixClient.get_user_detail(obj.bitrix_user_id)
        if user:
            return EmployeeSerializer(user).data
        return None


class SalaryIncrementReminderSerializer(serializers.ModelSerializer):
    employee_details = serializers.SerializerMethodField(read_only=True)
    actioned_by_username = serializers.ReadOnlyField(source='actioned_by.username')

    class Meta:
        model = SalaryIncrementReminder
        fields = '__all__'

    def get_employee_details(self, obj):
        from common.bitrix_client import BitrixClient
        user = BitrixClient.get_user_detail(obj.bitrix_user_id)
        if user:
            return EmployeeSerializer(user).data
        return None


class SalaryIncrementApprovalSerializer(serializers.ModelSerializer):
    employee_details = serializers.SerializerMethodField(read_only=True)
    approved_by_username = serializers.ReadOnlyField(source='approved_by.username')

    class Meta:
        model = SalaryIncrementApproval
        fields = '__all__'
        read_only_fields = ('approved_by', 'approved_at', 'pdf_file', 'old_net', 'new_net', 'increment_amount', 'increment_pct')

    def get_employee_details(self, obj):
        from common.bitrix_client import BitrixClient
        user = BitrixClient.get_user_detail(obj.bitrix_user_id)
        if user:
            return EmployeeSerializer(user).data
        return None

    def validate_reason(self, value):
        if value and len(value.strip()) < 20:
            raise serializers.ValidationError("Increment reason must be at least 20 characters long.")
        return value

    def validate(self, attrs):
        bitrix_user_id = attrs.get('bitrix_user_id')
        
        # Fetch active salary structure to validate against current gross
        active_structure = SalaryStructure.objects.filter(bitrix_user_id=bitrix_user_id).order_by('-effective_from').first()
        if not active_structure:
            raise serializers.ValidationError("This employee does not have an active salary structure to increment.")
            
        new_basic = attrs.get('new_basic')
        if new_basic < Decimal(active_structure.gross_salary):
            raise serializers.ValidationError({
                'new_basic': f"New gross salary (Rs. {new_basic}) must be greater than or equal to current gross salary (Rs. {active_structure.gross_salary})."
            })
            
        return attrs
