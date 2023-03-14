from django.urls import path

from imports.views import DocumentOntologyExport

urlpatterns = [
    path('document/<int:pk>/ontology/export/', DocumentOntologyExport.as_view(), name='document-ontology-export'),
]
