import sys
import uuid
import logging

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models, transaction
from django.utils.functional import cached_property


logger = logging.getLogger(__name__)


class NoVersionManager(models.Manager):
    def get_queryset(self):
        """
        By default we always fetch the last version transparently
        """
        return super().get_queryset().filter(is_current=True)


class VersionManager(models.Manager):
    def history(self, instance):
        return self.filter(**instance.get_version_identity())
    
    def get_previous_version(self, instance):
        pass
    
    def get_next_version(self, instance):
        pass


class Versioned(models.Model):
    """
    Naïve versioning.

    version_identity_fields is a tuple of field names that identify an object as unique, 
    meaning all versions of it will share the same value for these fields.
    
    It is advised to create an partial unique index to add a constraint on is_current, exp:
    operations = [
    migrations.RunSQL("CREATE UNIQUE INDEX partial_index ON table_name(is_current)
                       WHERE is_current"),
    ]

    """
    revision = models.UUIDField(default=uuid.uuid4, editable=False)
    # allows for fast fetching
    is_current = models.BooleanField(null=True, db_index=True, default=True)
    
    source = models.CharField(max_length=128,
                              default=getattr(settings, 'VERSIONING_DEFAULT_SOURCE'))
    
    # username, can't use FK because can be external
    author = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    version_identity_fields = None
    
    objects = NoVersionManager()
    versions = VersionManager()
    
    def get_version_identity(self):
        if self.version_identity_fields is None:
            raise ValueError("version_identity_fields attribute can not be empty.")
        return {field: self.__dict__[field]
                for field in self.version_identity_fields}
    
    @cached_property
    def current_version(self):
        try:
            return self.history().get(is_current=True)
        except self._meta.model.DoesNotExist:
            logger.error("Current version not found for %s.", self)
            return None
    
    def make_new_version(self):
        kwargs = {}
        for field in self._meta.fields:
            if field.name not in ('id', 'revision'):
                kwargs[field.name] = getattr(self, field.name)
        new = self._meta.model(**kwargs)
        try:
            del self.current_version
        except AttributeError:
            pass
        return new
            
    def history(self):
        """
        Returns a unevaluated queryset of all versions of this object
        """
        return self._meta.model.versions.history(self)
    
    def make_current(self):
        # this is wrapped in a transaction because if the second save fails,
        # we want to rollback the current_version
        with transaction.atomic():
            self.unset_current_version()
            self.is_current = True
            self.save()
    
    def unset_current_version(self):
        """
        remove the is_current from the current version
        """
        if self.current_version:
            self.current_version.is_current = False
            self.current_version.save()
        del self.current_version
    
    def revert_to(self, target):
        target.make_current()
    
    def revert_to_revision(self, revision):
        try:
            target = self.history().get(revision=revision)
        except self._meta.model.DoesNotExist:
            # catch the .get(), no need to rollback at this point
            logger.warning("Couldn't find revision %s for %s.", revision, self)
        else:
            target.make_current()
    
    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_current and self.current_version != self:
                self.unset_current_version()
            return super().save(*args, **kwargs)
    
    class Meta:
        abstract = True
        ordering = ('-updated_at',)


if 'test' in sys.argv:
    class TestModel(Versioned):
        identity = models.IntegerField()
        content = models.CharField(max_length=128)
        version_identity_fields = ('identity',)

        def __str__(self):
            return self.content
