from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from .models import Role, Permission
from .serializers import RoleSerializer, PermissionSerializer
from .permissions import HasModelPermission

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by('id')
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasModelPermission]

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError("System critical roles (ADMIN and HR) cannot be deleted.")
        # Re-assign users of this role to No Role or default to prevent errors
        instance.users.all().update(role=None)
        instance.delete()

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all().order_by('module', 'name')
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasModelPermission]
    pagination_class = None

    @action(detail=False, methods=['POST'], url_path='add-permission')
    def add_permission(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
