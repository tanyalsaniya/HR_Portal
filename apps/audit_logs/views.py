from rest_framework import viewsets, serializers, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse, Http404
from django.db import models
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
import csv
import openpyxl
from openpyxl import Workbook
from weasyprint import HTML

from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import AuditLog

class QueryParamJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header_auth = super().authenticate(request)
        if header_auth is not None:
            return header_auth
            
        raw_token = request.query_params.get('token')
        if not raw_token:
            return None
            
        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception:
            raise AuthenticationFailed("Invalid or expired token.")

class IsAdminUserOnly(permissions.BasePermission):
    """
    Allows access only to superusers or users with the ADMIN role.
    """
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and (user.is_superuser or (user.role and user.role.code == 'ADMIN'))

class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.ReadOnlyField(source='actor.username')
    actor_role = serializers.ReadOnlyField(source='actor.role.name')

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_username', 'actor_role', 'user_id_val', 
            'user_name', 'user_role', 'action', 'module_name', 'description', 
            'old_values', 'new_values', 'ip_address', 'user_agent', 'status', 'timestamp'
        ]

class AuditLogPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUserOnly]
    authentication_classes = [QueryParamJWTAuthentication]
    pagination_class = AuditLogPagination

    def get_queryset(self):
        return AuditLog.objects.all().order_by('-timestamp')

    # Export endpoints
    @action(detail=False, methods=['GET'], url_path='export')
    def export_logs(self, request):
        export_format = request.query_params.get('export_format', 'csv')
        queryset = self.get_queryset()
        
        # Don't paginate the export
        logs = list(queryset)

        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="activity_logs.csv"'
            writer = csv.writer(response)
            writer.writerow(['Timestamp', 'User ID', 'User Name', 'Role', 'Action', 'Module', 'Description', 'IP Address', 'Status'])
            for log in logs:
                writer.writerow([
                    log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
                    log.user_id_val or 'N/A',
                    log.user_name or 'System',
                    log.user_role or 'N/A',
                    log.action,
                    log.module_name or 'N/A',
                    log.description,
                    log.ip_address or 'N/A',
                    log.status
                ])
            return response

        elif export_format == 'excel':
            wb = Workbook()
            ws = wb.active
            ws.title = "Activity Logs"
            
            headers = ['Timestamp', 'User ID', 'User Name', 'Role', 'Action', 'Module', 'Description', 'IP Address', 'Status']
            ws.append(headers)
            
            for log in logs:
                ws.append([
                    log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
                    log.user_id_val or 'N/A',
                    log.user_name or 'System',
                    log.user_role or 'N/A',
                    log.action,
                    log.module_name or 'N/A',
                    log.description,
                    log.ip_address or 'N/A',
                    log.status
                ])
            
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="activity_logs.xlsx"'
            wb.save(response)
            return response

        elif export_format == 'pdf':
            html_string = render_to_string('audit/pdf_audit_logs.html', {
                'logs': logs,
                'company_name': 'MTVL HR Portal'
            })
            pdf_bytes = HTML(string=html_string).write_pdf()
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="activity_logs.pdf"'
            return response

        return Response({'error': 'Invalid format'}, status=status.HTTP_400_BAD_REQUEST)
