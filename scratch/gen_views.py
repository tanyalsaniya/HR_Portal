import re

def generate_dismissed_views():
    with open('apps/salary/views.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Imports to replace
    imports_to_add = """
from .models import (
    DismissedSalaryStructure, DismissedSalarySlip, DismissedSalaryImportBatch,
    DismissedEmployeeBankDetail
)
from .dismissed_serializers import (
    DismissedSalaryStructureSerializer, DismissedSalarySlipSerializer,
    DismissedSalaryImportBatchSerializer
)
from .services import (
    generate_dismissed_payslip_pdf, generate_dismissed_payslips_zip,
    generate_dismissed_payslip_pdf_bytes, get_latest_prior_dismissed_slip,
    calculate_carry_forward_dismissed_slip
)
"""
    
    # We want to grab specific classes: 
    # SalaryExportView, SalaryImportView, SalaryPublishView, SalaryEditView, 
    # SalaryGridView, SalaryHistoryView, SalarySlipDownloadView, SalaryImportBatchesView,
    # SalaryEmployeeSummaryView, SalaryEmployeeHistoryExportView, SalaryIndividualGenerateView,
    # get_employee_slips_for_range, check_role, StandardResultsSetPagination (or just reuse from views)
    
    # Better: just replace the whole file content for generating dismissed views,
    # but that might be large. Let's do string replacements on the whole file,
    # then output it. We'll reuse `check_role`, `StandardResultsSetPagination`, `num_to_words` from views.
    
    replacements = {
        "class SalaryExportView": "class DismissedSalaryExportView",
        "class SalaryImportView": "class DismissedSalaryImportView",
        "class SalaryPublishView": "class DismissedSalaryPublishView",
        "class SalaryEditView": "class DismissedSalaryEditView",
        "class SalaryGridView": "class DismissedSalaryGridView",
        "class SalaryHistoryView": "class DismissedSalaryHistoryView",
        "class SalarySlipDownloadView": "class DismissedSalarySlipDownloadView",
        "class SalaryImportBatchesView": "class DismissedSalaryImportBatchesView",
        "class SalaryEmployeeSummaryView": "class DismissedSalaryEmployeeSummaryView",
        "class SalaryEmployeeHistoryExportView": "class DismissedSalaryEmployeeHistoryExportView",
        "class SalaryIndividualGenerateView": "class DismissedSalaryIndividualGenerateView",
        "def get_employee_slips_for_range": "def get_employee_slips_for_range_dismissed",
        "get_employee_slips_for_range(": "get_employee_slips_for_range_dismissed(",
        
        "SalaryStructure": "DismissedSalaryStructure",
        "SalarySlip": "DismissedSalarySlip",
        "SalaryImportBatch": "DismissedSalaryImportBatch",
        "EmployeeBankDetail": "DismissedEmployeeBankDetail",
        
        "SalaryStructureSerializer": "DismissedSalaryStructureSerializer",
        "SalarySlipSerializer": "DismissedSalarySlipSerializer",
        "SalaryImportBatchSerializer": "DismissedSalaryImportBatchSerializer",
        
        "generate_payslip_pdf": "generate_dismissed_payslip_pdf",
        "generate_payslips_zip": "generate_dismissed_payslips_zip",
        "generate_payslip_pdf_bytes": "generate_dismissed_payslip_pdf_bytes",
        "get_latest_prior_slip": "get_latest_prior_dismissed_slip",
        "calculate_carry_forward_slip": "calculate_carry_forward_dismissed_slip",
    }
    
    # We also need to change the active employee logic.
    # In ExportView and GridView:
    active_logic = """        for emp in user_map.values():
            if emp.status != 'Exited':
                employees.append(emp)
            else:
                has_recent_exit = False
                try:
                    exit_req = ExitRequest.objects.filter(bitrix_user_id=emp.bitrix_id).exclude(status='CANCELLED').order_by('-last_working_day').first()
                    if exit_req:
                        if exit_req.status != 'FULLY_EXITED':
                            has_recent_exit = True
                        elif exit_req.last_working_day:
                            import datetime
                            cutoff_date = datetime.date.today() - datetime.timedelta(days=60)
                            if exit_req.last_working_day >= cutoff_date:
                                has_recent_exit = True
                except Exception:
                    pass
                if has_recent_exit:
                    employees.append(emp)"""

    dismissed_logic = """        for emp in user_map.values():
            if emp.status == 'Exited':
                employees.append(emp)"""
                
    content = content.replace(active_logic, dismissed_logic)

    active_import_logic = """                        if employee.status == 'Exited':
                            from exit_formality.models import ExitRequest
                            has_pending_exit = ExitRequest.objects.filter(
                                bitrix_user_id=employee.bitrix_id
                            ).exclude(status__in=['CANCELLED', 'FULLY_EXITED']).exists()
                            if not has_pending_exit:
                                raise ValueError("Employee is exited and has no pending exit request in the system")"""

    dismissed_import_logic = """                        if employee.status != 'Exited':
                            raise ValueError("Cannot import active employee to dismissed payroll")"""
                            
    content = content.replace(active_import_logic, dismissed_import_logic)
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    # Replace imports
    # Remove the existing imports that we replaced
    # Add our new imports
    header = """import datetime
import os
import openpyxl
from decimal import Decimal
from django.db import models, transaction
from django.core.files.base import ContentFile
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination

from common.bitrix_client import BitrixClient, BitrixEmployeeMock

from .models import (
    DismissedSalaryStructure, DismissedSalarySlip, DismissedSalaryImportBatch,
    DismissedEmployeeBankDetail
)
from .dismissed_serializers import (
    DismissedSalaryStructureSerializer, DismissedSalarySlipSerializer,
    DismissedSalaryImportBatchSerializer
)
from .services import (
    generate_dismissed_payslip_pdf, generate_dismissed_payslips_zip,
    generate_dismissed_payslip_pdf_bytes, get_latest_prior_dismissed_slip,
    calculate_carry_forward_dismissed_slip, num_to_words
)
from .views import check_role, StandardResultsSetPagination
"""
    
    # Strip the original imports up to `def check_role`
    content = content.split('def check_role(user):', 1)[1]
    # Remove the standard check_role and pagination definitions, as we're importing them
    content = content.split('# Legacy viewsets for backward compatibility with UI', 1)[1]
    
    # Remove SalaryStructureViewSet and SalaryIncrementViewSet since they aren't needed here
    # Actually it's fine if they are generated as DismissedSalaryStructureViewSet but they might not be needed.
    # Let's just output the whole thing and then we will hook up urls.
    
    final_content = header + "\n# Legacy viewsets for backward compatibility with UI\n" + content

    
    with open('apps/salary/dismissed_views.py', 'w', encoding='utf-8') as f:
        f.write(final_content)
        
if __name__ == '__main__':
    generate_dismissed_views()
