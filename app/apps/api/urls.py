from django.urls import include, path
from rest_framework_nested import routers

from api.views import (
    AnnotationComponentViewSet,
    AnnotationTaxonomyViewSet,
    AnnotationTypeViewSet,
    BlockTypeViewSet,
    BlockViewSet,
    DocumentMetadataViewSet,
    DocumentPartTypeViewSet,
    DocumentTranscriptionViewSet,
    DocumentViewSet,
    ImageAnnotationViewSet,
    LineTranscriptionViewSet,
    LineTypeViewSet,
    LineViewSet,
    OcrModelViewSet,
    PartMetadataViewSet,
    PartViewSet,
    ProjectViewSet,
    RegenerableAuthToken,
    ScriptViewSet,
    TagViewSet,
    TextAnnotationViewSet,
    UserViewSet,
)

router = routers.DefaultRouter()
router.register(r'scripts', ScriptViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'documents', DocumentViewSet)
router.register(r'models', OcrModelViewSet)
router.register(r'users', UserViewSet)
router.register(r'types/block', BlockTypeViewSet)
router.register(r'types/line', LineTypeViewSet)
router.register(r'types/annotations', AnnotationTypeViewSet)
router.register(r'types/part', DocumentPartTypeViewSet)

projects_router = routers.NestedSimpleRouter(router, r'projects', lookup='project')
projects_router.register(r'tags', TagViewSet, basename='tag')

documents_router = routers.NestedSimpleRouter(router, r'documents', lookup='document')
documents_router.register(r'metadata', DocumentMetadataViewSet, basename='metadata')
documents_router.register(r'parts', PartViewSet, basename='part')
documents_router.register(r'transcriptions', DocumentTranscriptionViewSet, basename='transcription')
documents_router.register(r'taxonomies/annotations', AnnotationTaxonomyViewSet)
documents_router.register(r'taxonomies/components', AnnotationComponentViewSet)

parts_router = routers.NestedSimpleRouter(documents_router, r'parts', lookup='part')
parts_router.register(r'blocks', BlockViewSet)
parts_router.register(r'lines', LineViewSet)
parts_router.register(r'transcriptions', LineTranscriptionViewSet)
parts_router.register(r'annotations/image', ImageAnnotationViewSet)
parts_router.register(r'annotations/text', TextAnnotationViewSet)
parts_router.register(r'metadata', PartMetadataViewSet, basename='partmetadata')

app_name = 'api'
urlpatterns = [
    path('', include(router.urls)),
    path('', include(documents_router.urls)),
    path('', include(parts_router.urls)),
    path('', include(projects_router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('token-auth/', RegenerableAuthToken.as_view())
]
