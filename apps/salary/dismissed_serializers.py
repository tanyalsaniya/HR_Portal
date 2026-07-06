from rest_framework import serializers
from .models import (
    DismissedSalaryStructure, DismissedSalarySlip, DismissedSalaryImportBatch
)

class DismissedSalaryStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = DismissedSalaryStructure
        fields = '__all__'


class DismissedSalarySlipSerializer(serializers.ModelSerializer):
    class Meta:
        model = DismissedSalarySlip
        fields = '__all__'


class DismissedSalaryImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = DismissedSalaryImportBatch
        fields = '__all__'
