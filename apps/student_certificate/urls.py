# apps/student_certificate/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, StudentFeeInstallmentViewSet

router = DefaultRouter()
router.register('students', StudentViewSet, basename='student')
router.register('installments', StudentFeeInstallmentViewSet, basename='studentfeeinstallment')

urlpatterns = [
    path('', include(router.urls)),
]
