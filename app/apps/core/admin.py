from django.contrib import admin

from core.models import Typology, Metadata, Document, DocumentMetadata


class MetadataInline(admin.TabularInline):
    model = DocumentMetadata

class DocumentAdmin(admin.ModelAdmin):
    inlines = (MetadataInline,)


admin.site.register(Typology)
admin.site.register(Metadata)
admin.site.register(Document, DocumentAdmin)
