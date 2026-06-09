# apps/authentication/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import AccessToken
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value, is_staff=True).exists():
            raise serializers.ValidationError("No HR user with this email")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_token(self, value):
        from rest_framework_simplejwt.exceptions import TokenError
        try:
            access_token = AccessToken(value)
            user_id = access_token.get('user_id')
            if not user_id:
                raise serializers.ValidationError("Invalid token")
            user = User.objects.get(id=user_id, is_staff=True)
            self.user = user
        except (TokenError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid or expired token")
        return value

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()