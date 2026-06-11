# apps/salary/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalaryStructureViewSet, SalarySlipViewSet, SalaryIncrementViewSet

router = DefaultRouter()
router.register('structures', SalaryStructureViewSet, basename='salarystructure')
router.register('slips', SalarySlipViewSet, basename='salaryslip')
router.register('increments', SalaryIncrementViewSet, basename='salaryincrement')

urlpatterns = [
    path('', include(router.urls)),
]
