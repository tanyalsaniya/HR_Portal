# apps/employee_onboarding/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, EmployeeViewSet, EmployeeDocumentViewSet, LetterTemplateViewSet, employees_hybrid_view
from accounts.views import hybrid_view

# API Router
router = DefaultRouter()
router.register('api/onboarding/departments', DepartmentViewSet, basename='department')
router.register('api/onboarding/employees', EmployeeViewSet, basename='employee')
router.register('api/onboarding/documents', EmployeeDocumentViewSet, basename='employeedocument')
router.register('api/onboarding/templates', LetterTemplateViewSet, basename='lettertemplate')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Hybrid View page + XHR API
    path('employees/', employees_hybrid_view, name='employees_view'),
    path('employees/onboard/', employees_hybrid_view, name='employees_onboard_view'),
    path('employees/detail/', hybrid_view(EmployeeViewSet, {'get': 'list'}), name='employees_detail_page'),
    path('employees/export-excel/', hybrid_view(EmployeeViewSet, {'get': 'excel_export'}), name='employees_export_excel'),
    path('employees/import-excel/', hybrid_view(EmployeeViewSet, {'post': 'excel_import'}), name='employees_import_excel'),
    path('employees/<str:pk>/', hybrid_view(EmployeeViewSet, {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='employees_detail_view'),
    path('employees/<str:pk>/manual-graduate/', hybrid_view(EmployeeViewSet, {'post': 'manual_graduate'}), name='employees_manual_graduate'),
    path('employees/<str:pk>/retry-bitrix-sync/', hybrid_view(EmployeeViewSet, {'post': 'retry_bitrix_sync'}), name='employees_retry_bitrix_sync'),
    path('employees/<str:pk>/generate-offer-letter/', hybrid_view(EmployeeViewSet, {'post': 'generate_offer_letter_api'}), name='employees_offer_letter'),
    path('employees/<str:pk>/generate-appointment-letter/', hybrid_view(EmployeeViewSet, {'post': 'generate_appointment_letter_api'}), name='employees_appointment_letter'),
    path('employees/<str:pk>/generate-bond-letter/', hybrid_view(EmployeeViewSet, {'post': 'generate_bond_letter_api'}), name='employees_bond_letter'),
    path('employees/<str:pk>/preview-letter/', hybrid_view(EmployeeViewSet, {'post': 'preview_letter_api'}), name='employees_preview_letter'),
    path('employees/<str:pk>/send-welcome-email/', hybrid_view(EmployeeViewSet, {'post': 'send_welcome_email'}), name='employees_send_welcome_email'),
    path('employees/<str:pk>/invite-to-bitrix/', hybrid_view(EmployeeViewSet, {'post': 'invite_to_bitrix'}), name='employees_invite_to_bitrix'),
]
