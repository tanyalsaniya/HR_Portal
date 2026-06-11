# apps/exit_formality/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExitRequestViewSet, ExitPublicQuestionnaireView, RejoiningAPIView

router = DefaultRouter()
router.register('requests', ExitRequestViewSet, basename='exitrequest')

urlpatterns = [
    path('', include(router.urls)),
    path('public-questionnaire/', ExitPublicQuestionnaireView.as_view(), name='exit_public_questionnaire'),
    path('rejoin/', RejoiningAPIView.as_view(), name='rejoin_ex_employee'),
]
