from django.contrib import admin

from core.models import *


class MetadataInline(admin.TabularInline):
    model = DocumentMetadata

class DocumentAdmin(admin.ModelAdmin):
    inlines = (MetadataInline,)

class DocumentPartAdmin(admin.ModelAdmin):
    list_display = ['pk', 'title', 'document',]
    actions = ['recover',]
    
    def recover(self, request, queryset):
        for instance in queryset:
            instance.recover()
    
class LineTranscriptionAdmin(admin.ModelAdmin):
    raw_id_fields = ('line',)
    
admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentProcessSettings)
admin.site.register(DocumentPart, DocumentPartAdmin)
admin.site.register(LineTranscription, LineTranscriptionAdmin)
admin.site.register(Typology)
admin.site.register(Metadata)
admin.site.register(OcrModel)
