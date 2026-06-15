# apps/salary/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalaryStructureViewSet, SalarySlipViewSet, SalaryIncrementViewSet
from accounts.views import hybrid_view

# API Router
router = DefaultRouter()
router.register('api/salary/structures', SalaryStructureViewSet, basename='salarystructure')
router.register('api/salary/slips', SalarySlipViewSet, basename='salaryslip')
router.register('api/salary/increments', SalaryIncrementViewSet, basename='salaryincrement')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Hybrid View page + XHR API
    path('salaries/', hybrid_view(SalaryStructureViewSet, {'get': 'list', 'post': 'create'}), name='salaries_view'),
    path('salaries/<int:pk>/', hybrid_view(SalaryStructureViewSet, {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='salaries_detail_view'),
]
