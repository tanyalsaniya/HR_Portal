import re
import datetime
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rules import MAX_DOCUMENT_SIZE_BYTES, MAX_PROFILE_PHOTO_SIZE_BYTES
from .models import Department, EmployeeDocument, LetterTemplate

User = get_user_model()

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


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


class EmployeeSalaryStructureSerializer(serializers.ModelSerializer):
    gross_salary = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        from salary.models import SalaryStructure
        model = SalaryStructure
        fields = '__all__'


class EmployeeSerializer(serializers.Serializer):
    id = serializers.CharField()
    emp_id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    work_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    personal_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField()
    designation = serializers.CharField()
    department = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    department_name = serializers.SerializerMethodField()
    department_details = serializers.SerializerMethodField()
    joining_date = serializers.CharField()
    dob = serializers.CharField()
    gender = serializers.CharField()
    profile_photo = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField()
    onboarding_complete = serializers.BooleanField()
    employment_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    address_line1 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    state = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    pin_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    emergency_contact_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    emergency_relationship = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    emergency_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bitrix_contact_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # Relational documents and structures
    documents = serializers.SerializerMethodField()
    salary_structures = serializers.SerializerMethodField()
    
    # Masked placeholders for banking/pan compatibility
    aadhaar_masked = serializers.CharField(default="XXXXXXXX1234", read_only=True)
    pan_masked = serializers.CharField(default="XXXXXX1234", read_only=True)
    bank_account = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    pan_no = serializers.CharField(default="", required=False, allow_blank=True)
    bond_period_months = serializers.IntegerField(default=0, required=False)
    notice_period_days = serializers.IntegerField(default=30, required=False)

    def get_bank_account(self, obj):
        from salary.models import EmployeeBankDetail
        detail = EmployeeBankDetail.objects.filter(bitrix_user_id=obj.get('id')).first()
        return detail.bank_account_no if detail else ""

    def get_bank_name(self, obj):
        from salary.models import EmployeeBankDetail
        detail = EmployeeBankDetail.objects.filter(bitrix_user_id=obj.get('id')).first()
        return detail.bank_name if detail else ""

    def get_documents(self, obj):
        docs = EmployeeDocument.objects.filter(bitrix_user_id=obj.get('id'))
        return EmployeeDocumentSerializer(docs, many=True, context=self.context).data

    def get_salary_structures(self, obj):
        from salary.models import SalaryStructure
        structures = SalaryStructure.objects.filter(bitrix_user_id=obj.get('id'))
        return EmployeeSalaryStructureSerializer(structures, many=True, context=self.context).data

    def get_department_name(self, obj):
        dept_id = obj.get('department')
        if dept_id:
            try:
                dept = Department.objects.filter(id=dept_id).first()
                if dept:
                    return dept.name
            except Exception:
                pass
        return "Engineering"

    def get_department_details(self, obj):
        dept_id = obj.get('department')
        if dept_id:
            try:
                dept = Department.objects.filter(id=dept_id).first()
                if dept:
                    return {
                        'id': dept.id,
                        'name': dept.name
                    }
            except Exception:
                pass
        return None


class LetterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LetterTemplate
        fields = '__all__'
