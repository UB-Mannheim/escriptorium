import django
import jsonschema
from django.core.validators import BaseValidator


# Straight from https://stackoverflow.com/questions/37642742/django-postgresql-json-field-schema-validation/49755623
class JSONSchemaValidator(BaseValidator):
    def compare(self, value, schema):
        try:
            jsonschema.validate(value, schema)
        except jsonschema.exceptions.ValidationError:
            raise django.core.exceptions.ValidationError(
                "%(value)s failed JSON schema check", params={"value": value}
            )
