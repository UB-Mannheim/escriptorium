from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.translation import gettext as _

from ordered_model.models import OrderedModel

from versioning.models import Versioned

User = get_user_model()


class Typology(models.Model):
    """
    Document: map, poem, novel ..
    Part: page, log, cover ..
    Block: main text, floating text, illustration, 
    """
    TARGET_DOCUMENT = 1
    TARGET_PART = 2
    TARGET_BLOCK = 3
    TARGET_CHOICES = (
        (TARGET_DOCUMENT, 'Document'),
        (TARGET_PART, 'Part (eg Page)'),
        (TARGET_BLOCK, 'Block (eg Paragraph)'), 
    )
    name = models.CharField(max_length=128)
    target = models.PositiveSmallIntegerField(choices=TARGET_CHOICES)

    def __str__(self):
        return self.name


class Document(models.Model):
    WORKFLOW_STATE_UNPUBLISHED = 0
    WORKFLOW_STATE_PUBLISHED = 1
    WORKFLOW_STATE_ARCHIVED = 2
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_UNPUBLISHED, _("Unpublished")),
        (WORKFLOW_STATE_PUBLISHED, _("Published")),
        (WORKFLOW_STATE_ARCHIVED, _("Archived")),
    )
    
    ACCESS_PRIVATE = 0
    ACCESS_PUBLIC = 1
    ACCESS_CHOICES = (
        (ACCESS_PRIVATE, _("Private")),
        (ACCESS_PUBLIC, _("Public")),
    )
    
    name = models.CharField(max_length=512)
    
    access = models.PositiveSmallIntegerField(
        default=ACCESS_PRIVATE, choices=ACCESS_CHOICES,
        help_text=_("A private document can be shared specifically with teams and individuals."))
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    shared_with_users = models.ManyToManyField(User, blank=True,
                                               verbose_name=_("Share with users"),
                                               related_name='shared_documents')
    shared_with_groups = models.ManyToManyField(Group, blank=True,
                                                verbose_name=_("Share with teams"),
                                                related_name='shared_documents')
    
    typology = models.ForeignKey(Typology, null=True, blank=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_DOCUMENT})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_UNPUBLISHED,
        choices=WORKFLOW_STATE_CHOICES)

    class Meta:
        ordering = ('-updated_at',)
    
    def __str__(self):
        return self.name

    @property
    def is_published(self):
        return self.workflow_state == self.WORKFLOW_STATE_PUBLISHED

    @property
    def is_archived(self):
        return self.workflow_state == self.WORKFLOW_STATE_ARCHIVED


# class Transcription(models.Model):
#     name = models.CharField(max_length=512)
#     document = models.ForeignKey(Document, on_delete=models.CASCADE)
#     ocr_backend = models.CharField(default='kraken')
#     ocr_model = models.FileField()
#     created_at
#     updated_at


class DocumentPart(OrderedModel):
    """
    Represents a physical part of a larger document that is usually a page
    """
    image = models.ImageField()
    typology = models.ForeignKey(Typology, null=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_PART})
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    order_with_respect_to = 'document'
    
    class Meta(OrderedModel.Meta):
        pass


# class Block(models.Model):
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


# class Line(models.Model):  # Versioned, OrderedModel
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
#     version_ignore_fields = ('transcription', 'document_part', 'order')
        
#     class Meta(OrderedModel.Meta):
#         pass
    
#     # def save(self, *args, **kwargs):
#     #     # validate char_boxes
#     #     return super().save(*args, **kwargs)

