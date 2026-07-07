# apps/salary/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SalaryStructureViewSet, SalaryIncrementViewSet,
    SalaryExportView, SalaryImportView, SalaryPublishView,
    SalaryEditView, SalaryHistoryView, SalarySlipDownloadView,
    SalaryImportBatchesView, SalaryEmployeeSummaryView, SalaryEmployeeHistoryExportView,
    SalaryIndividualGenerateView, SalaryGridView
)
from .dismissed_views import (
    DismissedSalaryExportView, DismissedSalaryImportView, DismissedSalaryPublishView,
    DismissedSalaryEditView, DismissedSalaryHistoryView, DismissedSalarySlipDownloadView,
    DismissedSalaryImportBatchesView, DismissedSalaryEmployeeSummaryView, DismissedSalaryEmployeeHistoryExportView,
    DismissedSalaryIndividualGenerateView, DismissedSalaryGridView
)
from accounts.views import hybrid_view

# API Router
router = DefaultRouter()
router.register('api/salary/structures', SalaryStructureViewSet, basename='salarystructure')
router.register('api/salary/increments', SalaryIncrementViewSet, basename='salaryincrement')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Hybrid View page + XHR API
    path('salaries/', hybrid_view(SalaryStructureViewSet, {'get': 'list', 'post': 'create'}), name='salaries_view'),
    path('salaries/<int:pk>/', hybrid_view(SalaryStructureViewSet, {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='salaries_detail_view'),
    path('salaries/employee/<int:employee_id>/', hybrid_view(SalaryHistoryView), name='employee_salary_history_page'),

    # Payroll specific routes
    path('api/admin/salary/export', SalaryExportView.as_view(), name='salary_export'),
    path('api/admin/salary/import', SalaryImportView.as_view(), name='salary_import'),
    path('api/admin/salary/publish', SalaryPublishView.as_view(), name='salary_publish'),
    path('api/admin/salary/grid', SalaryGridView.as_view(), name='salary_grid'),
    path('api/admin/salary/edit/<int:pk>/', SalaryEditView.as_view(), name='salary_edit'),
    path('api/salary/history', SalaryHistoryView.as_view(), name='salary_history'),
    path('api/salary/slip/download', SalarySlipDownloadView.as_view(), name='salary_download'),
    path('api/admin/salary/import-batches', SalaryImportBatchesView.as_view(), name='salary_import_batches'),
    path('api/salary/employee/<int:employee_id>/summary', SalaryEmployeeSummaryView.as_view(), name='salary_employee_summary'),
    path('api/salary/employee/<int:employee_id>/export', SalaryEmployeeHistoryExportView.as_view(), name='salary_employee_history_export'),
    path('api/admin/salary/generate-individual', SalaryIndividualGenerateView.as_view(), name='salary_generate_individual'),

    # Dismissed payroll specific routes
    path('api/admin/salary/dismissed/export', DismissedSalaryExportView.as_view(), name='dismissed_salary_export'),
    path('api/admin/salary/dismissed/import', DismissedSalaryImportView.as_view(), name='dismissed_salary_import'),
    path('api/admin/salary/dismissed/publish', DismissedSalaryPublishView.as_view(), name='dismissed_salary_publish'),
    path('api/admin/salary/dismissed/grid', DismissedSalaryGridView.as_view(), name='dismissed_salary_grid'),
    path('api/admin/salary/dismissed/edit/<int:pk>/', DismissedSalaryEditView.as_view(), name='dismissed_salary_edit'),
    path('api/salary/dismissed/history', DismissedSalaryHistoryView.as_view(), name='dismissed_salary_history'),
    path('api/salary/dismissed/slip/download', DismissedSalarySlipDownloadView.as_view(), name='dismissed_salary_download'),
    path('api/admin/salary/dismissed/import-batches', DismissedSalaryImportBatchesView.as_view(), name='dismissed_salary_import_batches'),
    path('api/salary/dismissed/employee/<int:employee_id>/summary', DismissedSalaryEmployeeSummaryView.as_view(), name='dismissed_salary_employee_summary'),
    path('api/salary/dismissed/employee/<int:employee_id>/export', DismissedSalaryEmployeeHistoryExportView.as_view(), name='dismissed_salary_employee_history_export'),
    path('api/admin/salary/dismissed/generate-individual', DismissedSalaryIndividualGenerateView.as_view(), name='dismissed_salary_generate_individual'),
]
