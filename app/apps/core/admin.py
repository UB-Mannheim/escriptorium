from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from solo.admin import SingletonModelAdmin

from core.models import (
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    BlockType,
    Document,
    DocumentMetadata,
    DocumentPart,
    DocumentPartType,
    DocumentTag,
    DocumentType,
    InstanceSettings,
    LineTranscription,
    LineType,
    Metadata,
    OcrModel,
    OcrModelDocument,
    OcrModelRight,
    Project,
    Script,
    TextualWitness,
    Transcription,
)


class MetadataInline(admin.TabularInline):
    model = DocumentMetadata


class TagInline(admin.TabularInline):
    model = DocumentTag


class DocumentTagInline(admin.TabularInline):
    model = Document.tags.through


class ProjectAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name']
    search_fields = ['name']
    inlines = (TagInline,)


class DocumentAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name', 'owner', 'project']
    search_fields = ['name', 'owner__username', 'project__name']
    inlines = (MetadataInline, DocumentTagInline)


class DocumentPartAdmin(admin.ModelAdmin):
    list_display = ['pk', 'title', 'document']
    actions = ['recover']

    def recover(self, request, queryset):
        for instance in queryset:
            instance.recover()


class TranscriptionAdmin(admin.ModelAdmin):
    list_display = ('name',)


class LineTranscriptionAdmin(admin.ModelAdmin):
    raw_id_fields = ('line',)


class ScriptAdmin(admin.ModelAdmin):
    list_display = ['name', 'text_direction']
    list_filter = ['text_direction']


class OcrModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'job', 'owner', 'script', 'training', 'parent', 'public']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['documents_link', 'rights_link', 'finetuned_models_link']
    raw_id_fields = ('parent', 'owner')
    list_select_related = ('owner', 'script', 'parent')

    fieldsets = (
        (None, {
            'fields': ('name', 'job', 'owner', 'script', 'training', 'parent', 'public', 'file', 'file_size')
        }),
        ('Related Records', {
            'fields': ('documents_link', 'rights_link', 'finetuned_models_link'),
            'description': 'View related documents and access rights'
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('owner', 'script', 'parent')

    def documents_link(self, obj):
        if obj and obj.pk:
            count = OcrModelDocument.objects.filter(ocr_model=obj).count()
            url = reverse('admin:core_ocrmodeldocument_changelist') + f'?ocr_model__id__exact={obj.pk}'
            return format_html('<a href="{}">{} documents</a>', url, count)
        return '-'
    documents_link.short_description = 'Training/Execution Documents'

    def rights_link(self, obj):
        if obj and obj.pk:
            count = OcrModelRight.objects.filter(ocr_model=obj).count()
            url = reverse('admin:core_ocrmodelright_changelist') + f'?ocr_model__id__exact={obj.pk}'
            return format_html('<a href="{}">{} access rights</a>', url, count)
        return '-'
    rights_link.short_description = 'User/Group Access Rights'

    def finetuned_models_link(self, obj):
        if obj and obj.pk:
            count = OcrModel.objects.filter(parent=obj).count()
            url = reverse('admin:core_ocrmodel_changelist') + f'?parent__id__exact={obj.pk}'
            return format_html('<a href="{}">{} fine-tuned models</a>', url, count)
        return '-'
    finetuned_models_link.short_description = 'Models Fine-tuned From This'


class OcrModelDocumentAdmin(admin.ModelAdmin):
    list_display = ['document', 'ocr_model', 'trained_on', 'executed_on', 'created_at']
    list_filter = ['trained_on', 'executed_on', 'created_at']
    search_fields = ['document__name', 'ocr_model__name']
    raw_id_fields = ['document', 'ocr_model']
    list_select_related = ['document', 'ocr_model']


class OcrModelRightAdmin(admin.ModelAdmin):
    list_display = ['ocr_model', 'user', 'group', 'created_at']
    list_filter = ['created_at']
    search_fields = ['ocr_model__name', 'user__username', 'group__name']
    raw_id_fields = ['ocr_model', 'user', 'group']
    list_select_related = ['ocr_model', 'user', 'group']


class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'project']


class InstanceSettingsAdmin(SingletonModelAdmin):
    list_display = ('page_batch_segmentation', 'page_batch_recognition')
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


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
admin.site.register(AnnotationType)
admin.site.register(AnnotationTaxonomy)
admin.site.register(AnnotationComponent)
admin.site.register(DocumentTag, DocumentTagAdmin)
admin.site.register(TextualWitness)
admin.site.register(Transcription)
admin.site.register(InstanceSettings)
