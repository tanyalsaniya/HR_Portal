import re
import datetime
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rules import MAX_DOCUMENT_SIZE_BYTES, MAX_PROFILE_PHOTO_SIZE_BYTES
from .models import Department, Employee, EmployeeDocument

User = get_user_model()

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    aadhaar = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=12)
    pan = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=10)
    aadhaar_masked = serializers.SerializerMethodField(read_only=True)
    pan_masked = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ('emp_id', 'created_by', 'created_at', 'status')

    def validate_first_name(self, value):
        if not re.match(r'^[a-zA-Z\s]+$', value):
            raise serializers.ValidationError("First name must contain letters and spaces only.")
        return value

    def validate_phone(self, value):
        if not re.match(r'^[6-9]\d{9}$', value):
            raise serializers.ValidationError("Phone number must be a 10-digit Indian mobile number (e.g., 9XXXXXXXXX).")
        return value

    def validate_alternate_phone(self, value):
        if value and not re.match(r'^[6-9]\d{9}$', value):
            raise serializers.ValidationError("Alternate phone number must be a 10-digit Indian mobile number.")
        return value

    def validate_emergency_phone(self, value):
        if not re.match(r'^[6-9]\d{9}$', value):
            raise serializers.ValidationError("Emergency phone number must be a 10-digit Indian mobile number.")
        return value

    def validate_dob(self, value):
        today = datetime.date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise serializers.ValidationError("Employee must be 18 years or older.")
        return value

    def validate_pin_code(self, value):
        if not re.match(r'^\d{6}$', value):
            raise serializers.ValidationError("PIN code must be a 6-digit numeric value.")
        return value

    def validate_joining_date(self, value):
        today = datetime.date.today()
        future_limit = today + datetime.timedelta(days=30)
        if value > future_limit:
            raise serializers.ValidationError("Joining date cannot be more than 30 days in the future.")
        return value

    def validate_aadhaar(self, value):
        if value and not re.match(r'^\d{12}$', value):
            raise serializers.ValidationError("Aadhaar number must be a 12-digit numeric value.")
        return value

    def validate_pan(self, value):
        if value and not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', value):
            raise serializers.ValidationError("PAN number must be a 10-character alphanumeric code in the format ABCDE1234F.")
        return value

    def validate_profile_photo(self, value):
        if value and value.size > MAX_PROFILE_PHOTO_SIZE_BYTES:
            raise serializers.ValidationError("Profile photo size must be less than 2 MB.")
        return value

    def get_aadhaar_masked(self, obj):
        val = obj.aadhaar_encrypted
        if val and len(val) >= 4:
            return f"XXXXXXXX{val[-4:]}"
        return val

    def get_pan_masked(self, obj):
        val = obj.pan_encrypted
        if val and len(val) >= 4:
            return f"XXXXXX{val[-4:]}"
        return val

    def create(self, validated_data):
        # Map raw fields to encrypted fields
        aadhaar = validated_data.pop('aadhaar', None)
        pan = validated_data.pop('pan', None)
        
        if aadhaar:
            validated_data['aadhaar_encrypted'] = aadhaar
        if pan:
            validated_data['pan_encrypted'] = pan
            
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
            
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Update encrypted fields if passed
        aadhaar = validated_data.pop('aadhaar', None)
        pan = validated_data.pop('pan', None)
        
        if aadhaar is not None:
            instance.aadhaar_encrypted = aadhaar
        if pan is not None:
            instance.pan_encrypted = pan
            
        return super().update(instance, validated_data)


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.ReadOnlyField(source='uploaded_by.username')
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = '__all__'
        read_only_fields = ('uploaded_by', 'upload_date')

    def get_file_name(self, obj):
        return obj.file.name.split('/')[-1] if obj.file else ""

    def validate_file(self, value):
        # Validate file size
        if value.size > MAX_DOCUMENT_SIZE_BYTES:
            raise serializers.ValidationError("File size must be less than 10 MB.")
            
        # Validate file format
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
