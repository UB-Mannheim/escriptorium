from django.contrib import admin

from core.models import Typology, Metadata, Document, DocumentMetadata, DocumentPart


class MetadataInline(admin.TabularInline):
    model = DocumentMetadata

class DocumentAdmin(admin.ModelAdmin):
    inlines = (MetadataInline,)

admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentPart)    
admin.site.register(Typology)
admin.site.register(Metadata)
