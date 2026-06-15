# apps/notifications/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet

# API Router
router = DefaultRouter()
router.register('api/notifications/feed', NotificationViewSet, basename='notification')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
]
