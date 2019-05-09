from django.urls import path

from core.views import *

urlpatterns = [
    path('', Home.as_view(), name='home'),
    path('documents/', DocumentsList.as_view(), name='documents-list'),
    path('document/<int:pk>/', DocumentDetail.as_view(), name='document-detail'),
    path('document/create/', CreateDocument.as_view(), name='document-create'),
    path('document/<int:pk>/edit/', UpdateDocument.as_view(), name='document-update'),
    path('document/<int:pk>/parts/edit/', EditPart.as_view(), name='document-part-edit'),
    path('document/<int:pk>/part/<int:part_pk>/edit/', EditPart.as_view(), name='document-part-edit'),
    path('document/<int:pk>/images/', DocumentImages.as_view(), name='document-images'),
    path('document/<int:pk>/transcribe/', DocumentTranscription.as_view(), name='document-transcription'),
    path('document/<int:pk>/transcribe/<int:part_pk>/', DocumentTranscription.as_view(), name='document-transcription'),
    path('document/<int:pk>/transcribe/<int:part_pk>/line/', LineTranscriptionUpdateAjax.as_view(), name='document-line-transcription'),
    path('document/<int:pk>/publish/', PublishDocument.as_view(), name='document-publish'),
    path('document/<int:pk>/share/', ShareDocument.as_view(), name='document-share'),
    path('document/<int:pk>/process/', DocumentPartsProcessAjax.as_view(), name='document-parts-process'),
]
