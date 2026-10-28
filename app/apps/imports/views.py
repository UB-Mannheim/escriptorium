from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.generic import View

from core.models import Document
from core.ontology import dump_yaml, export_ontology_config


class DocumentOntologyExport(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            document = Document.objects.for_user(self.request.user).get(pk=self.kwargs["pk"])
        except Document.DoesNotExist:
            raise PermissionDenied

        serialized_ontology_str = dump_yaml(export_ontology_config(document))
        response = HttpResponse(serialized_ontology_str, content_type="application/yaml")
        response["Content-Disposition"] = "attachment; filename=ontology_export.yml"
        return response
