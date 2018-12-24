from django.contrib import admin

from core.models import *


class MetadataInline(admin.TabularInline):
    model = DocumentMetadata

class DocumentAdmin(admin.ModelAdmin):
    inlines = (MetadataInline,)

admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentProcessSettings)
admin.site.register(DocumentPart)
# admin.site.register(LineTranscription)
admin.site.register(Typology)
admin.site.register(Metadata)
