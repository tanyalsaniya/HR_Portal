# config/urls.py
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Core REST API Endpoints
    path('api/auth/', include('accounts.urls')),
    path('api/onboarding/', include('employee_onboarding.urls')),
    path('api/exit/', include('exit_formality.urls')),
    path('api/salary/', include('salary.urls')),
    path('api/student/', include('student_certificate.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/audit/', include('audit_logs.urls')),
    path('api/roles/', include('roles.urls')),
    
    # Web Frontend Page Shells
    path('login/', TemplateView.as_view(template_name='accounts/login.html'), name='login'),
    path('exit-questionnaire/', TemplateView.as_view(template_name='exit/questionnaire.html'), name='exit_questionnaire'),
    path('reset-password/', TemplateView.as_view(template_name='accounts/reset_password.html'), name='reset_password'),
    path('', TemplateView.as_view(template_name='base/layout.html'), name='dashboard'),
    path('dashboard/', TemplateView.as_view(template_name='base/layout.html'), name='dashboard_view'),
    path('employees/', TemplateView.as_view(template_name='base/layout.html'), name='employees_view'),
    path('salaries/', TemplateView.as_view(template_name='base/layout.html'), name='salaries_view'),
    path('exits/', TemplateView.as_view(template_name='base/layout.html'), name='exits_view'),
    path('students/', TemplateView.as_view(template_name='base/layout.html'), name='students_view'),
    path('logs/', TemplateView.as_view(template_name='base/layout.html'), name='logs_view'),
    path('roles/', TemplateView.as_view(template_name='base/layout.html'), name='roles_view'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
