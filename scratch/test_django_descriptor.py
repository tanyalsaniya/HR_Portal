# scratch/test_django_descriptor.py
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'apps'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import models
from django.db.models.query_utils import DeferredAttribute
from decimal import Decimal
from common.fields import EncryptedDecimalField

class EncryptedDecimalDescriptor(DeferredAttribute):
    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = self.field.to_python(value)

# Let's dynamically add contribute_to_class override or test it directly on a mock model
class TestModel(models.Model):
    gross = EncryptedDecimalField()
    
    class Meta:
        app_label = 'salary' # use existing app label to avoid AppRegistryNotReady

# Let's inspect the descriptor on the model
print("Original descriptor class:", type(TestModel.gross))

# Apply our custom descriptor to gross
TestModel.gross = EncryptedDecimalDescriptor(TestModel._meta.get_field('gross'))

print("New descriptor class:", type(TestModel.gross))

# Let's instantiate and test assignment
obj = TestModel(gross="20000.50")
print("gross value:", obj.gross, type(obj.gross))
assert isinstance(obj.gross, Decimal)
assert obj.gross == Decimal("20000.50")

obj.gross = "100.25"
print("gross updated value:", obj.gross, type(obj.gross))
assert isinstance(obj.gross, Decimal)
assert obj.gross == Decimal("100.25")

print("All assertions passed!")
