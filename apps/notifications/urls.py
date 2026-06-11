# apps/notifications/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet

router = DefaultRouter()
router.register('feed', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
