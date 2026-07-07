# apps/common/fields.py
from django.db import models
from django.db.models.query_utils import DeferredAttribute
from decimal import Decimal
from common.encryption import encrypt_value, decrypt_value

class EncryptedDecimalDescriptor(DeferredAttribute):
    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = self.field.to_python(value)

class EncryptedCharField(models.TextField):
    description = "Encrypted CharField"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt_value(value)

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str) and not value.startswith('gAAAAA'):
            return value
        return decrypt_value(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return encrypt_value(str(value))

class EncryptedDecimalField(models.TextField):
    description = "Encrypted DecimalField"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        decrypted = decrypt_value(value)
        return Decimal(decrypted) if decrypted else None

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str) and not value.startswith('gAAAAA'):
            return Decimal(value) if value else None
        decrypted = decrypt_value(value)
        return Decimal(decrypted) if decrypted else None

    def get_prep_value(self, value):
        if value is None:
            return value
        # Standardize decimal to string representation
        if isinstance(value, Decimal):
            return encrypt_value(f"{value:.2f}")
        return encrypt_value(str(value))

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, EncryptedDecimalDescriptor(self))
