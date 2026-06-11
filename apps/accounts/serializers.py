from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to the JWT payload
        token['role'] = user.role.code if user.role else None
        token['permissions'] = list(user.role.permissions.values_list('codename', flat=True)) if user.role else []
        token['username'] = user.username
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Add custom data directly to the JSON response body
        data['role'] = self.user.role.code if self.user.role else None
        data['permissions'] = list(self.user.role.permissions.values_list('codename', flat=True)) if self.user.role else []
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['id'] = self.user.id
        return data

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email")
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
            user = User.objects.get(id=user_id)
            self.user = user
        except (TokenError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid or expired token")
        return value

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()