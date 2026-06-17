# apps/student_certificate/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, StudentFeeInstallmentViewSet, CourseViewSet, StudentCertificateViewSet
from accounts.views import hybrid_view

# API Router
router = DefaultRouter()
router.register('api/student/students', StudentViewSet, basename='student')
router.register('api/student/installments', StudentFeeInstallmentViewSet, basename='studentfeeinstallment')
router.register('api/student/courses', CourseViewSet, basename='course')
router.register('api/student/certificates', StudentCertificateViewSet, basename='studentcertificate')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Hybrid View page + XHR API
    path('students/', hybrid_view(StudentViewSet, {'get': 'list', 'post': 'create'}), name='students_view'),
    path('students/<int:pk>/', hybrid_view(StudentViewSet, {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='students_detail_view'),
    path('students/<int:student_id>/generate-certificate/', hybrid_view(StudentViewSet, {'post': 'generate_certificate'}), name='students_generate_certificate'),
]

