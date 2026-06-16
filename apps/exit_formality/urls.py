# apps/exit_formality/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExitRequestViewSet, ExitPublicQuestionnaireView, RejoiningAPIView, exit_form_view
from accounts.views import hybrid_view
from django.views.generic import TemplateView

# API Router
router = DefaultRouter()
router.register('api/exit/requests', ExitRequestViewSet, basename='exitrequest')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Standard non-hybrid view routes
    path('exit/form/<str:token>/', exit_form_view, name='exit_secure_form'),
    path('api/exit/public-questionnaire/', ExitPublicQuestionnaireView.as_view(), name='exit_public_questionnaire'),
    path('api/exit/rejoin/', RejoiningAPIView.as_view(), name='rejoin_ex_employee'),
    path('exit-questionnaire/', TemplateView.as_view(template_name='exit/questionnaire.html'), name='exit_questionnaire'),
    
    # Hybrid View page + XHR API
    path('exits/', hybrid_view(ExitRequestViewSet, {'get': 'list', 'post': 'create'}), name='exits_view'),
    path('exits/<int:pk>/', hybrid_view(ExitRequestViewSet, {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='exits_detail_view'),
    path('exits/<int:pk>/send-link/', hybrid_view(ExitRequestViewSet, {'post': 'send_link_api'}), name='exits_send_link'),
    path('exits/<int:exit_id>/generate-relieving/', hybrid_view(ExitRequestViewSet, {'post': 'generate_relieving_api'}), name='exits_generate_relieving'),
    path('exits/<int:exit_id>/generate-experience/', hybrid_view(ExitRequestViewSet, {'post': 'generate_experience_api'}), name='exits_generate_experience'),
    path('exits/<int:exit_id>/generate-notice/', hybrid_view(ExitRequestViewSet, {'post': 'generate_notice_api'}), name='exits_generate_notice'),
]
