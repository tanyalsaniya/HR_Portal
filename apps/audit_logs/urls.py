# apps/audit_logs/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet
from accounts.views import hybrid_view

# API Router
router = DefaultRouter()
router.register('api/audit/logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Hybrid View page + XHR API
    path('logs/', hybrid_view(AuditLogViewSet, {'get': 'list'}), name='logs_view'),
]
