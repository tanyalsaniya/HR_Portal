# config/urls.py

from django.contrib import admin

from django.urls import include, path

from django.conf import settings

from django.conf.urls.static import static

from employee_onboarding.views import SecureDocumentServeView



urlpatterns = [

    path('', include('accounts.urls')),

    path('', include('salary.urls')),

    path('admin/', admin.site.urls),

    

    # Secure document serving interceptor

    path('media/employees/<str:emp_id>/docs/<str:filename>', SecureDocumentServeView.as_view(), name='secure_doc_serve'),

    

    path('', include('employee_onboarding.urls')),

    path('', include('exit_formality.urls')),

    path('', include('student_certificate.urls')),

    path('', include('notifications.urls')),

    path('', include('audit_logs.urls')),

    path('', include('roles.urls')),

]



# Serve media files in development (fallback for non-secure files, like profile photos)

if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

