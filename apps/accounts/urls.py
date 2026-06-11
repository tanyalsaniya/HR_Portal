from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    UserDetailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    DashboardAPIView
)

urlpatterns = [
    # JWT login and refresh (using custom pair view)
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Authenticated user info
    path('me/', UserDetailView.as_view(), name='user_detail'),
    
    # Dashboard stats
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard_stats'),

    # Custom password reset
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]