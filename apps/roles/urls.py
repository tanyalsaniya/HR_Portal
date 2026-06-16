from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleViewSet, PermissionViewSet
from accounts.views import hybrid_view

# API Router
router = DefaultRouter()
router.register('api/roles/roles', RoleViewSet, basename='role')
router.register('api/roles/permissions', PermissionViewSet, basename='permission')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Hybrid View page + XHR API
    path('roles/', hybrid_view(RoleViewSet, {'get': 'list', 'post': 'create'}), name='roles_view'),
    path('roles/permissions/', hybrid_view(PermissionViewSet, {'get': 'list', 'post': 'create'}), name='permissions_view'),
    path('roles/<int:pk>/', hybrid_view(RoleViewSet, {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='roles_detail_view'),
]
