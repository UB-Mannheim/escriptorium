import json
import sys
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models


class Versioned(models.Model):
    """
    Allows the versioning of a model, every revisions is stored in the revisions field
    this technique allows to not have to deal with changing references to this 'object'.
    Also takes less database place.
    
    revisions = [{
      revision: <uuid>,
      source: <kraken>,
      author: <karen>,
      created_at: <utc iso>,
      updated_at: <utc iso>,
      data: {}  # no need to pickle since jsonb is compiled anyway
    ]}
    """
    ### these fields store the 'current' revision
    revision = models.UUIDField(default=uuid.uuid4, editable=False)
    version_source = models.CharField(editable=False, max_length=128,
                                      default=getattr(settings, 'VERSIONING_DEFAULT_SOURCE'))
    # can't use FK because can be external
    version_author = models.CharField(editable=False, max_length=128)
    version_created_at = models.DateTimeField(editable=False, auto_now_add=True)
    version_updated_at = models.DateTimeField(editable=False, auto_now=True)
    
    # this is a stack, more recents to the top
    # on postgres it's stored as jsonb, super fast and indexable!
    versions = JSONField(editable=False, default='[]')
    
    def pack(self):
        """
        Create a dict from the current instance to be added to the history
        """
        data = {}
        for field in self._meta.fields:
            if field.name not in ('id', 'revision', 'versions') and not field.name.startswith('version_'):
                data[field.name] = getattr(self, field.name)
        
        return {
            'revision': self.revision.hex,
            'source': self.version_source,
            'author': self.version_author,
            'created_at': self.version_created_at.isoformat(),
            'updated_at': self.version_updated_at.isoformat(),
            'data': data
        }
    
    def instance_from_version(self, version):        
        fields = version.pop('data')
        fields['revision'] = uuid.UUID(version.pop('revision'))
        # version_source, version_author, version_created_at, version_updated_at
        fields.update(**{'version_%s' % key: value for key, value in version.items()})
        instance = self._meta.model(**fields)
        return instance
    
    def new_version(self):
        history = json.loads(self.versions)
        history.insert(0, self.pack())
        self.versions = json.dumps(history)
        
        self.revision = uuid.uuid4()  # new revision number
        self.version_created_at = datetime.utcnow()
        self.version_updated_at = datetime.utcnow()
    
    def revert(self, revision):
        """
        revision is a hex of the uuid field as stored in the history
        does not save to base
        """
        history = json.loads(self.versions)
        
        for version in history:
            if version['revision'] == revision:
                # insert current state
                history.insert(0, self.pack())
                # pop revision
                history.pop(history.index(version))
                self.version = json.dumps(history)
                
                # load its data
                self.revision = uuid.UUID(revision)
                for field_name, value in version['data'].items():
                    setattr(self, field_name, value)
                self.version_source = version['source']
                self.version_author = version['author']
                # self.version_created_at = datetime.fromisoformat(version['created_at'])  # 3.7 only
                self.version_created_at = datetime.strptime(
                    version['created_at'][:26], "%Y-%m-%dT%H:%M:%S.%f")
                self.version_updated_at = datetime.utcnow()
                self.versions = json.dumps(history)
                break
        else:
            # get here if we don't break
            raise ValueError("Revision %s not found for %s" % (revision, self))
    
    @property
    def history(self):
        versions = json.loads(self.versions)
        return [self.instance_from_version(version) for version in versions]
    
    class Meta:
        abstract = True


if 'test' in sys.argv:
    class TestModel(Versioned):
        content = models.CharField(max_length=128)

        def __str__(self):
            return self.content
