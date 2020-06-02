import sys
import uuid
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models


def _dummy_db(*args, **kwargs):
    raise RuntimeError("Can not save/delete an old version.")


class NoChangeException(Exception):
    pass


class Versioned(models.Model):
    """
    Allows the flat versioning of a model instance, every revisions is stored in the versions field
    this technique allows to not have to deal with changing references to this 'object'.
    cons: get clobbered somewhat fast depending on the quantity of versioned data

    API:
    instance.history : is a property returning a list of instances corresponding to the versions.
    instance.new_version() : store the current data in versions. Does not call save().
    instance.revert(revision) : store the current data in versions and revert to the given revision
                                does not call save(), it needs to be done manually.
    instance.delete_revision(revision)

    Model class attributes:
    version_ignore_fields = () : model fields that won't be added to the versions
    version_history_max_length = 10 : maximum number of revisions to store in the history

    revisions = [{
      revision: <uuid>,
      source: <kraken>,
      author: <karen>,
      created_at: <utc iso>,
      updated_at: <utc iso>,
      data: {}  # no need to pickle since jsonb is compiled anyway
    ]}
    """
    # these fields store the 'current' revision
    revision = models.UUIDField(default=uuid.uuid4, editable=False)
    version_source = models.CharField(editable=False, max_length=128,
                                      default=getattr(settings, 'VERSIONING_DEFAULT_SOURCE'))
    # can't use FK because can be external
    version_author = models.CharField(editable=False, max_length=128)
    version_created_at = models.DateTimeField(editable=False, auto_now_add=True)
    version_updated_at = models.DateTimeField(editable=False, auto_now=True)

    # this is a stack, more recents to the top
    # on postgres it's stored as jsonb, super fast and indexable!
    versions = JSONField(editable=False, default=list)
    version_ignore_fields = ()
    version_history_max_length = 20

    def pack(self, **kwargs):
        """
        Create a dict from the current instance to be added to the history
        """
        data = {}
        for field in self._meta.fields:
            if (field.name not in ('id', 'revision', 'versions')
                and field.name not in self._meta.model.version_ignore_fields
                and not field.name.startswith('version_')):
                data[field.name] = getattr(self, field.name)
        data.update(kwargs)
        return {
            'revision': self.revision.hex,
            'source': self.version_source,
            'author': self.version_author,
            'created_at': self.version_created_at.isoformat(),
            'updated_at': self.version_updated_at.isoformat(),
            'data': data
        }

    def unpack(self, version):
        """
        Create an instance (not saved in db) from a dict (usually coming from the history)
        """
        v = version.copy()
        fields = v.pop('data')
        fields['revision'] = uuid.UUID(v.pop('revision'))
        # version_source, version_author, version_created_at, version_updated_at
        fields.update(**{'version_%s' % key: value for key, value in v.items()})
        # update the instance with the left over fields
        fields.update(**{field: getattr(self, field) for field in self.version_ignore_fields})
        data = {f: fields[f] for f in fields if f in [mf.name for mf in self._meta.fields]}
        instance = self._meta.model(**data)
        # disable database operations
        instance.save = _dummy_db
        instance.delete = _dummy_db
        return instance

    def new_version(self, author=None, source=None, **kwargs):
        packed = self.pack(**kwargs)
        author_ = author or self.version_author
        source_ = source or self.version_author

        if self.versions:
            last = self.versions[0]
            if (packed['data'] == last['data']
                and author_ == self.version_author
                and source_ == self.version_source):
                raise NoChangeException
        self.versions.insert(0, packed)
        # if we passed version_history_max_length we delete the last one
        if (self.version_history_max_length
            and len(self.versions) > self.version_history_max_length):
            self.delete_revision(self.versions[self.version_history_max_length]['revision'])

        self.revision = uuid.uuid4()  # new revision number
        self.version_author = author_
        self.version_source = source_
        self.version_created_at = datetime.now(timezone.utc)
        self.version_updated_at = datetime.now(timezone.utc)

    def revert(self, revision):
        """
        revision is a hex of the uuid field as stored in the history
        does not save to base
        """
        for version in self.versions:
            if version['revision'] == revision:
                # insert current state
                self.versions.insert(0, self.pack())
                # pop revision
                self.versions.pop(self.versions.index(version))

                # load its data
                self.revision = uuid.UUID(revision)
                for field_name, value in version['data'].items():
                    setattr(self, field_name, value)
                self.version_source = version['source']
                self.version_author = version['author']
                # 3.7 only
                # self.version_created_at = datetime.fromisoformat(version['created_at'])
                self.version_created_at = datetime.strptime(
                    version['created_at'][:26], "%Y-%m-%dT%H:%M:%S.%f")
                self.version_updated_at = datetime.now(timezone.utc)
                break
        else:
            # get here if we don't break
            raise ValueError("Revision %s not found for %s" % (revision, self))

    def delete_revision(self, revision):
        for i, version in enumerate(self.versions):
            if version['revision'] == revision:
                del self.versions[i]
                break
        else:
            raise ValueError("Revision %s not found for %s" % (revision, self))

    def flush_history(self):
        self.versions = []

    @property
    def history(self):
        return [self.unpack(version) for version in self.versions]

    class Meta:
        abstract = True


if 'test' in sys.argv:
    class TestModel(Versioned):
        content = models.CharField(max_length=128)
        ignored = models.SmallIntegerField(default=5)
        version_ignore_fields = ('ignored',)
        version_history_max_length = 5

        def __str__(self):
            return self.content
