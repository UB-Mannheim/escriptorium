from users.models import User
from core.models import *


class CoreFactory():
    """
    A model Factory to help create data for tests.
    """
    def make_user(self):
        return User.objects.create(username='test')

    def make_document(self, **kwargs):
        attrs = kwargs.copy()
        attrs['owner'] = attrs.get('owner') or self.make_user()
        attrs.setdefault('name', 'test doc')
        return Document.objects.create(**attrs)
    
    def make_part(self, **kwargs):
        attrs = kwargs.copy()
        attrs['document'] = attrs.get('document') or self.make_document()
        attrs.setdefault('image', None)
        return DocumentPart.objects.create(**attrs)
    
    def make_transcription(self, **kwargs):
        attrs = kwargs.copy()
        attrs['document'] = attrs.get('document') or self.make_document()
        attrs.setdefault('name', 'test trans')
        return Transcription.objects.create(**attrs)
