from django.urls import path

from core.views import *


urlpatterns = [
    path('', Home.as_view(), name='home'),
    path('documents/', DocumentsList.as_view(), name='documents-list'),
    path('document/<int:pk>/', DocumentDetail.as_view(), name='document-detail'),
    path('document/create/', CreateDocument.as_view(), name='document-create'),
    path('document/<int:pk>/update/', UpdateDocument.as_view(), name='document-update'),
    path('document/<int:pk>/publish/', PublishDocument.as_view(), name='document-publish'),
    path('document/<int:pk>/share/', ShareDocument.as_view(), name='document-share'),
    path('document/<int:pk>/update/upload-image/', UploadImageAjax.as_view(), name='document-upload-image'),
    path('document/<int:pk>/process/', DocumentPartsProcessAjax.as_view(), name='document-parts-process'),
    path('document/<int:pk>/part/<int:part_pk>/', DocumentPartAjax.as_view(), name='document-part'),
    path('document/<int:pk>/part/<int:part_pk>/delete/', DeleteDocumentPartAjax.as_view(), name='document-part-delete'),
]
