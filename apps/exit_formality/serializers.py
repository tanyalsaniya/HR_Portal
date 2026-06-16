import datetime
from rest_framework import serializers
from employee_onboarding.serializers import EmployeeSerializer
from .models import ExitRequest, ExitSecureLink, ExitFormResponse, ExitFFSettlement

class ExitSecureLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitSecureLink
        fields = '__all__'

class ExitFFSettlementSerializer(serializers.ModelSerializer):
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    approved_by_username = serializers.ReadOnlyField(source='approved_by.username')
    payment_processed_by_username = serializers.ReadOnlyField(source='payment_processed_by.username')

    class Meta:
        model = ExitFFSettlement
        fields = '__all__'
        read_only_fields = ('exit_request', 'created_by', 'created_at', 'updated_at', 'approved_by', 'approved_at', 'payment_processed_by')

    def validate(self, attrs):
        exit_request = self.context.get('exit_request') or (self.instance.exit_request if self.instance else None)
        if exit_request:
            employee = exit_request.employee
            if employee.bond_period_months > 0:
                bond_end = employee.joining_date + datetime.timedelta(days=employee.bond_period_months * 30)
                if exit_request.last_working_day < bond_end:
                    bond_penalty = attrs.get('bond_penalty', 0)
                    if bond_penalty is None or float(bond_penalty) <= 0:
                        raise serializers.ValidationError({
                            'bond_penalty': "Employee is exiting during the active bond period. A bond penalty must be populated."
                        })
        return attrs

class ExitRequestSerializer(serializers.ModelSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    initiated_by_username = serializers.ReadOnlyField(source='initiated_by.username')
    overridden_by_username = serializers.ReadOnlyField(source='overridden_by.username')
    secure_link = ExitSecureLinkSerializer(read_only=True)
    ff_settlement = ExitFFSettlementSerializer(read_only=True)
    form_response = serializers.SerializerMethodField()
    last_working_day = serializers.DateField(required=False)

    class Meta:
        model = ExitRequest
        fields = '__all__'
        read_only_fields = ('initiated_by', 'initiated_at', 'status', 'overridden_by', 'overridden_at', 'secure_link_sent_at', 'secure_link_expires_at')

    def get_form_response(self, obj):
        try:
            if hasattr(obj, 'form_response'):
                return ExitFormResponseSerializer(obj.form_response).data
        except ExitFormResponse.DoesNotExist:
            pass
        return None

    def validate_exit_reason(self, value):
        if value and len(value.strip()) < 20:
            raise serializers.ValidationError("Exit reason (HR notes) must be at least 20 characters long.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['initiated_by'] = request.user
        return super().create(validated_data)


class ExitFormResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitFormResponse
        fields = '__all__'
        read_only_fields = ('exit_request', 'submitted_at')

    def validate_rating_env(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_rating_mgmt(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_rating_balance(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, attrs):
        # 1. Check if KT is completed/in-progress and requires a handover name
        kt_status = attrs.get('kt_status')
        kt_handover_to = attrs.get('kt_handover_to')
        if kt_status in ('COMPLETED', 'IN_PROGRESS') and not kt_handover_to:
            raise serializers.ValidationError({
                'kt_handover_to': "Handover recipient name is required if knowledge transfer is Completed or In Progress."
            })

        # 2. Check if reason is Other and requires explanation of min 20 chars
        reason_dropdown = attrs.get('reason_dropdown')
        reason_details = attrs.get('reason_details')
        if reason_dropdown == 'Other':
            if not reason_details or len(reason_details.strip()) < 20:
                raise serializers.ValidationError({
                    'reason_details': "Please provide details (minimum 20 characters) for leaving if you selected 'Other'."
                })

        return attrs
