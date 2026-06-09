from django.shortcuts import render

# Create your views here.
# apps/authentication/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.authentication.permissions import IsHRUser
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsHRUser

User = get_user_model()

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email, is_staff=True)

        # Create a short-lived access token (5 minutes)
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])
        # For production, set a shorter lifetime, e.g., timedelta(minutes=5)
        # but for simplicity we reuse the same setting.

        reset_link = f"http://localhost:3000/reset-password?token={str(token)}"
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
    

class EmployeeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsHRUser]