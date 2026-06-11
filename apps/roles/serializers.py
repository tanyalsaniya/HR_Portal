from rest_framework import serializers
from .models import Role, Permission

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'module']

class RoleSerializer(serializers.ModelSerializer):
    permissions_details = PermissionSerializer(source='permissions', many=True, read_only=True)
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'permissions', 'permissions_details', 'is_active', 'is_system']
        read_only_fields = ['is_system']

    def update(self, instance, validated_data):
        # Prevent modification of ADMIN or HR role codes/names if they are system critical
        if instance.is_system:
            validated_data.pop('name', None)
            validated_data.pop('code', None)
        return super().update(instance, validated_data)
