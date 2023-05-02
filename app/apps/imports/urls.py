from django.urls import path

from core.views import DocumentOntology
from imports.views import DocumentOntologyExport

urlpatterns = [
    path('document/<int:pk>/ontology/export/', DocumentOntologyExport.as_view(), name='document-ontology-export'),
    path('document/<int:pk>/ontology/import/', DocumentOntology.as_view(), name='document-ontology-import'),
]
