from django.contrib import admin

from core.models import (Project,
                         Document,
                         DocumentPart,
                         Metadata,
                         DocumentMetadata,
                         DocumentTag,
                         LineTranscription,
                         OcrModel,
                         OcrModelDocument,
                         OcrModelRight,
                         Script,
                         DocumentType,
                         DocumentPartType,
                         BlockType,
                         LineType)


class MetadataInline(admin.TabularInline):
    model = DocumentMetadata


class OcrModelDocumentInline(admin.TabularInline):
    model = OcrModelDocument


class OcrModelRightInline(admin.TabularInline):
    model = OcrModelRight


class TagInline(admin.TabularInline):
    model = DocumentTag


class DocumentTagInline(admin.TabularInline):
    model = Document.tags.through


class ProjectAdmin(admin.ModelAdmin):
    inlines = (TagInline,)


class DocumentAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name', 'owner', 'project']
    inlines = (MetadataInline, OcrModelDocumentInline, DocumentTagInline)


class DocumentPartAdmin(admin.ModelAdmin):
    list_display = ['pk', 'title', 'document']
    actions = ['recover']

    def recover(self, request, queryset):
        for instance in queryset:
            instance.recover()


class LineTranscriptionAdmin(admin.ModelAdmin):
    raw_id_fields = ('line',)


class ScriptAdmin(admin.ModelAdmin):
    list_display = ['name', 'text_direction']
    list_filter = ['text_direction']


class OcrModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'job', 'owner', 'script', 'training', 'parent', 'public']
    inlines = (OcrModelDocumentInline, OcrModelRightInline)


class OcrModelDocumentAdmin(admin.ModelAdmin):
    list_display = ['document', 'ocr_model', 'trained_on', 'executed_on', 'created_at']


class OcrModelRightAdmin(admin.ModelAdmin):
    list_display = ['ocr_model', 'user', 'group', 'created_at']


class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'project']


admin.site.register(Project, ProjectAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentPart, DocumentPartAdmin)
admin.site.register(LineTranscription, LineTranscriptionAdmin)
admin.site.register(DocumentType)
admin.site.register(DocumentPartType)
admin.site.register(BlockType)
admin.site.register(LineType)
admin.site.register(Script, ScriptAdmin)
admin.site.register(Metadata)
admin.site.register(OcrModel, OcrModelAdmin)
admin.site.register(OcrModelDocument, OcrModelDocumentAdmin)
admin.site.register(OcrModelRight, OcrModelRightAdmin)
admin.site.register(DocumentTag, DocumentTagAdmin)
