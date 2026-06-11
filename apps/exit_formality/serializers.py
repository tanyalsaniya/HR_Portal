from rest_framework import serializers
from employee_onboarding.serializers import EmployeeSerializer
from .models import ExitRequest, ExitSecureLink, ExitFormResponse

class ExitRequestSerializer(serializers.ModelSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    initiated_by_username = serializers.ReadOnlyField(source='initiated_by.username')

    class Meta:
        model = ExitRequest
        fields = '__all__'
        read_only_fields = ('initiated_by', 'initiated_at', 'status')

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
