# apps/employee_onboarding/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, EmployeeViewSet, EmployeeDocumentViewSet

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')
router.register('employees', EmployeeViewSet, basename='employee')
router.register('documents', EmployeeDocumentViewSet, basename='employeedocument')

urlpatterns = [
    path('', include(router.urls)),
]
