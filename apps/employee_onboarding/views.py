from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from roles.permissions import HasModelPermission
from rules import ROLE_ADMIN
from .models import Department, Employee, EmployeeDocument
from .serializers import DepartmentSerializer, EmployeeSerializer, EmployeeDocumentSerializer
from .services import generate_offer_letter, generate_appointment_letter, generate_bond_letter

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer
    permission_classes = [HasModelPermission]

class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        # Only show employees who are not soft-deleted
        return Employee.objects.filter(is_deleted=False).order_by('-created_at')

    def destroy(self, request, *args, **kwargs):
        # Soft delete is restricted via HasModelPermission (onboarding.delete)
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST'], url_path='generate-offer-letter')
    def generate_offer_letter_api(self, request, pk=None):
        employee = self.get_object()
        try:
            doc = generate_offer_letter(employee, user=request.user)
            return Response({
                'message': 'Offer letter generated successfully.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-appointment-letter')
    def generate_appointment_letter_api(self, request, pk=None):
        employee = self.get_object()
        try:
            doc = generate_appointment_letter(employee, user=request.user)
            return Response({
                'message': 'Appointment letter generated successfully.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-bond-letter')
    def generate_bond_letter_api(self, request, pk=None):
        employee = self.get_object()
        if employee.bond_period_months <= 0:
            return Response({
                'error': 'This employee does not have a bond period specified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            doc = generate_bond_letter(employee, user=request.user)
            return Response({
                'message': 'Bond letter generated successfully.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        queryset = EmployeeDocument.objects.all().order_by('-upload_date')
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return queryset
