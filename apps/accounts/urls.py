from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from django.views.generic import TemplateView
from .views import (
    CustomTokenObtainPairView,
    UserDetailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    DashboardAPIView,
    hybrid_view,
    client_log_view
)

from .user_views import UserViewSet

urlpatterns = [
    # Legacy / API Endpoints (backward compatibility)
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/me/', UserDetailView.as_view(), name='user_detail'),
    path('api/auth/dashboard/', DashboardAPIView.as_view(), name='dashboard_stats'),
    path('api/auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Portal Users CRUD Endpoints (Admin access only)
    path('api/auth/users/', UserViewSet.as_view({'get': 'list', 'post': 'create'}), name='portal_users_list'),
    path('api/auth/users/<int:pk>/', UserViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='portal_users_detail'),

    # Clean Web Frontend & API Unified (Hybrid) Endpoints
    path('login/', TemplateView.as_view(template_name='accounts/login.html'), name='login'),
    path('reset-password/', TemplateView.as_view(template_name='accounts/reset_password.html'), name='reset_password'),
    
    # Root dashboard
    path('', hybrid_view(DashboardAPIView), name='dashboard'),
    path('dashboard/', hybrid_view(DashboardAPIView), name='dashboard_view'),
    path('api/client-log/', client_log_view, name='client_log'),
]