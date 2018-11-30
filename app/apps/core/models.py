from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField

from ordered_model.models import OrderedModel

# from versioning.models import Versioned


# class Typology():
#     """
#     Document: map, poem, novel ..
#     Part: page, log, cover ..
#     Block: main text, floating text, illustration, 
#     """
#     TARGET_DOCUMENT = 1
#     TARGET_PART = 2
#     TARGET_BLOCK = 3
#     TARGET_CHOICES = (
#         (TARGET_DOCUMENT, 'Document'),
#         (TARGET_PART, 'Part'),
#         (TARGET_BLOCK, 'Block'), 
#     )
#     name = models.CharField(max_length=128)
#     target = models.PositiveSmallIntegerField()

    
# class Document():
#     name = models.CharField(max_length=512)
#     typology = models.ForeignKey(Typology, null=True, on_delete=models.SET_NULL,
#                                  limit_choices_to={'target': Typology.TARGET_DOCUMENT})
#     created_at
#     updated_at
#     workflow
#     access

# class Transcription():
#     name = models.CharField(max_length=512)
#     document = models.ForeignKey(Document, on_delete=models.CASCADE)
#     created_at
#     updated_at

# class DocumentPart():  # OrderedModel
#     """
#     Represents a physical part of a larger document that is usually a page
#     """
#     image = models.ImageField()
#     typology = models.ForeignKey(Typology, null=True, on_delete=models.SET_NULL,
#                                  limit_choices_to={'target': Typology.TARGET_PART})
#     document = models.ForeignKey(Document, on_delete=models.CASCADE)
#     order_with_respect_to = 'document'
    
#     class Meta(OrderedModel.Meta):
#         pass


# class Block():
#     """
#     Represents a visualy close group of graphemes (characters) bound by the same semantic 
#     example: a paragraph, a margin note or floating text
#     A Block is not directly bound to a DocumentPart to avoid a useless join or denormalization
#     when fetching the content of a DocumentPart.
#     """
#     # box = models.BoxField()  # in case we use PostGIS
#     box = ArrayField(models.IntegerField(), size=4)
#     typology = models.ForeignKey(Typology, null=True, on_delete=models.SET_NULL,
#                                  limit_choices_to={'target': Typology.TARGET_BLOCK})
#     document_part = models.ForeignKey(DocumentPart, on_delete=models.CASCADE)


# class Line():  # Versioned, OrderedModel
#     """
#     Represents a transcripted line of a document part in a given transcription
#     """
#     text = models.TextField(null=True)
#     # box = models.BoxField()  # in case we use PostGIS
#     box = ArrayField(models.IntegerField(), size=4)

#     # graphs = [  # WIP
#     # {c: <graph_code>, bbox: ((x1, y1), (x2, y2)), confidence: 0-1/7}
#     # ]
#     graphs = JSONField()  # on postgres it maps to jsonb!
#     transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)
#     document_part = models.ForeignKey(DocumentPart, on_delete=models.CASCADE)
    
#     block = models.ForeignKey(Block, null=True, on_delete=models.SET_NULL)

#     order_with_respect_to = 'document_part'
#     version_identity_fields = ('transcription', 'document_part', 'order')
        
#     class Meta(OrderedModel.Meta):
#         pass
    
#     # def save(self, *args, **kwargs):
#     #     # validate char_boxes
#     #     return super().save(*args, **kwargs)

