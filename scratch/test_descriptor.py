# scratch/test_descriptor.py
from decimal import Decimal

class EncryptedDecimalDescriptor:
    def __init__(self, field_name):
        self.field_name = field_name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.field_name)

    def __set__(self, instance, value):
        # simulate to_python
        if value is None:
            converted = value
        elif isinstance(value, Decimal):
            converted = value
        else:
            converted = Decimal(str(value))
        instance.__dict__[self.field_name] = converted

class MockModel:
    gross_salary = EncryptedDecimalDescriptor('gross_salary')
    pf_contribution = EncryptedDecimalDescriptor('pf_contribution')
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def total_deductions(self):
        return self.pf_contribution

    @property
    def net_salary(self):
        return self.gross_salary - self.total_deductions

# Test assignment
obj = MockModel(gross_salary="20000", pf_contribution="1000")
print("gross_salary:", obj.gross_salary, type(obj.gross_salary))
print("pf_contribution:", obj.pf_contribution, type(obj.pf_contribution))
print("net_salary:", obj.net_salary, type(obj.net_salary))
