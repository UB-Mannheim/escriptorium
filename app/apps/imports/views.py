import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.generic import View

from core.models import Document
from imports.serializers import OntologyExportSerializer


class DocumentOntologyExport(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            document = Document.objects.for_user(self.request.user).get(pk=self.kwargs["pk"])
        except Document.DoesNotExist:
            raise PermissionDenied

        serialized_ontology_str = json.dumps(OntologyExportSerializer(document).data, indent=4)
        response = HttpResponse(serialized_ontology_str, content_type="application/json")
        response["Content-Disposition"] = "attachment; filename=ontology_export.json"
        return response
