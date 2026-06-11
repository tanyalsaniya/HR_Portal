from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleViewSet, PermissionViewSet

router = DefaultRouter()
router.register('roles', RoleViewSet, basename='role')
router.register('permissions', PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
]
