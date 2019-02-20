from django.contrib import admin

from core.models import *


class MetadataInline(admin.TabularInline):
    model = DocumentMetadata

class DocumentAdmin(admin.ModelAdmin):
    inlines = (MetadataInline,)

class LineTranscriptionAdmin(admin.ModelAdmin):
    raw_id_fields = ('line',)
    
admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentProcessSettings)
admin.site.register(DocumentPart)
admin.site.register(LineTranscription, LineTranscriptionAdmin)
admin.site.register(Typology)
admin.site.register(Metadata)
admin.site.register(OcrModel)
