import string
import random
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from roles.models import Role
from .serializers import UserAccountSerializer, UserRegistrationSerializer

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        user = request.user
        is_admin = user.is_superuser or (user.role and user.role.code == 'ADMIN')
        if not is_admin:
            raise PermissionDenied("Only Administrators can manage portal users.")

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        return UserAccountSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        auto_generate = serializer.validated_data.get('auto_generate_password', True)
        raw_password = serializer.validated_data.get('password', '')
        
        if auto_generate or not raw_password:
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            raw_password = ''.join(random.choice(chars) for _ in range(10))
            
        role_id = serializer.validated_data.get('role_id')
        role_obj = None
        if role_id:
            try:
                role_obj = Role.objects.get(id=role_id)
            except Role.DoesNotExist:
                raise ValidationError({"role_id": "Selected role does not exist."})
                
        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=raw_password,
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            phone=serializer.validated_data.get('phone', ''),
            role=role_obj
        )
        
        login_url = request.build_absolute_uri('/login/')
        email_body = f"""Dear {user.first_name or user.username},

Your account has been registered on the HR Portal. Below are your login credentials:

- Username / Email: {user.email}
- Password: {raw_password}

You can log in here: {login_url}

Please change your password after logging in.

Best regards,
System Administrator
"""
        import logging
        logger = logging.getLogger(__name__)
        try:
            send_mail(
                subject="Your HR Portal Credentials",
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@company.com',
                recipient_list=[user.email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Failed to send credentials email to {user.email}: {str(e)}")
            print(f"EMAIL ERROR: {str(e)}")
            
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "role_name": user.role.name if user.role else "No Role",
            "role_code": user.role.code if user.role else "",
            "password": raw_password,
            "email_sent": True
        }, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        role_id = self.request.data.get('role_id')
        if role_id is not None:
            if role_id == '':
                serializer.save(role=None)
            else:
                try:
                    role_obj = Role.objects.get(id=role_id)
                    serializer.save(role=role_obj)
                except Role.DoesNotExist:
                    raise ValidationError({"role_id": "Selected role does not exist."})
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            raise ValidationError("You cannot delete your own admin account.")
        return super().destroy(request, *args, **kwargs)
