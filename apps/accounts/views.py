from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CustomTokenObtainPairSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.code if user.role else None,
            'permissions': list(user.role.permissions.values_list('codename', flat=True)) if user.role else [],
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
        })

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        # Create a short-lived access token
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)

        reset_link = f"http://localhost:8000/reset-password?token={str(token)}"
        send_mail(
            subject="HR Portal Password Reset",
            message=f"Click the link to reset your password: {reset_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return Response({'message': 'Reset link sent to email'}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.contrib.auth.signals import user_logged_out
        user_logged_out.send(sender=request.user.__class__, request=request, user=request.user)
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)



from student_certificate.models import Student
from exit_formality.models import ExitRequest
from salary.models import SalaryIncrementReminder
from audit_logs.models import AuditLog
from audit_logs.views import AuditLogSerializer

class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'total_employees': 0,
            'active_employees': 0,
            'active_students': 0,
            'pending_exits': 0,
            'anniversaries_count': 0,
            'recent_logs': []
        }

        is_admin = user.is_superuser or (user.role and user.role.code == 'ADMIN')
        user_perms = set(user.role.permissions.values_list('codename', flat=True)) if user.role else set()

        if is_admin or 'onboarding.read' in user_perms:
            from common.bitrix_client import BitrixClient
            users = BitrixClient.get_all_users()
            data['total_employees'] = len(users)
            data['active_employees'] = sum(1 for u in users if u.get('status') == 'Active')

        if is_admin or 'student.read' in user_perms:
            data['active_students'] = Student.objects.filter(status='ACTIVE').count()

        if is_admin or 'exit.read' in user_perms:
            data['pending_exits'] = ExitRequest.objects.exclude(status='COMPLETED').count()

        if is_admin or 'salary.approve_increments' in user_perms:
            data['anniversaries_count'] = SalaryIncrementReminder.objects.filter(status='Pending').count()

        if is_admin or 'audit.read' in user_perms:
            logs = AuditLog.objects.all().order_by('-timestamp')[:5]
            serializer = AuditLogSerializer(logs, many=True)
            data['recent_logs'] = serializer.data

        return Response(data)

from django.shortcuts import render

def hybrid_view(view_class_or_func, actions=None, template_name='base/layout.html'):
    """
    Returns an API response if the request is an AJAX/JSON request (Accept: application/json or XHR header),
    otherwise renders the base layout template for the browser.
    """
    if hasattr(view_class_or_func, 'as_view'):
        if actions:
            api_view_func = view_class_or_func.as_view(actions)
        else:
            api_view_func = view_class_or_func.as_view()
    else:
        api_view_func = view_class_or_func

    def wrapper(request, *args, **kwargs):
        is_json = (
            'application/json' in request.META.get('HTTP_ACCEPT', '') or
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.GET.get('format') == 'json'
        )
        if is_json:
            response = api_view_func(request, *args, **kwargs)
            if hasattr(response, 'render'):
                response.render()
            return response
        else:
            return render(request, template_name)
    return wrapper

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def client_log_view(request):
    if request.method == 'POST':
        print("CLIENT LOG:", request.body.decode('utf-8'))
    return HttpResponse("OK")