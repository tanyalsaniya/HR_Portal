from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    submit_checklist,
    ProbationChecklistViewSet,
    ChecklistAssignmentViewSet,
    ProbationDashboardAPI,
    EmployeeTimelineAPI,
    TriggerFinalReportAPI,
    probation_page_view
)

router = DefaultRouter()
router.register(r'api/probation/checklists', ProbationChecklistViewSet, basename='probation-checklists')
router.register(r'api/probation/assignments', ChecklistAssignmentViewSet, basename='probation-assignments')

urlpatterns = [
    # Hybrid Page View
    path('probation/', probation_page_view, name='probation-page'),
    
    # Public checklist submission URL
    path('probation/submit/<int:assignment_id>/', submit_checklist, name='probation-submit'),
    
    # Admin APIs
    path('api/probation/dashboard/', ProbationDashboardAPI.as_view(), name='probation-dashboard-api'),
    path('api/probation/timeline/<str:employee_id>/', EmployeeTimelineAPI.as_view(), name='probation-timeline-api'),
    path('api/probation/final-report/<str:employee_id>/', TriggerFinalReportAPI.as_view(), name='probation-final-report-api'),
    
    # Include DRF router URLs
    path('', include(router.urls)),
]
