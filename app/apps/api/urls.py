from django.urls import include, path
from rest_framework_nested import routers
from rest_framework.authtoken import views

from api.views import (DocumentViewSet,
                       UserViewSet,
                       PartViewSet,
                       DocumentTranscriptionViewSet,
                       BlockViewSet,
                       LineViewSet,
                       BlockTypeViewSet,
                       LineTypeViewSet,
                       LineTranscriptionViewSet)

router = routers.DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'user', UserViewSet)
router.register(r'types/block', BlockTypeViewSet)
router.register(r'types/line', LineTypeViewSet)
documents_router = routers.NestedSimpleRouter(router, r'documents', lookup='document')
documents_router.register(r'parts', PartViewSet, basename='part')
documents_router.register(r'transcriptions', DocumentTranscriptionViewSet, basename='transcription')
parts_router = routers.NestedSimpleRouter(documents_router, r'parts', lookup='part')
parts_router.register(r'blocks', BlockViewSet)
parts_router.register(r'lines', LineViewSet)
parts_router.register(r'transcriptions', LineTranscriptionViewSet)

app_name = 'api'
urlpatterns = [
    path('', include(router.urls)),
    path('', include(documents_router.urls)),
    path('', include(parts_router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('token-auth/', views.obtain_auth_token)
]
