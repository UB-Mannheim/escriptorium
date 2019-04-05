import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import CreateView

from core.models import Document
from imports.forms import ImportForm
from imports.parsers import ParseError


class DocumentImport(LoginRequiredMixin, CreateView):
    http_method_names = ('post',)
    
    def get_document(self):
        return Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])
    
    def error(self, msg):
        return HttpResponse(json.dumps({'status': 'error', 'error': msg}),
                            content_type="application/json", status=400)
    
    def post(self, request, *args, **kwargs):
        try:
            document = self.get_document()
        except Document.DoesNotExist:
            return HttpResponse(json.dumps({'status': 'Not Found'}),
                                status=404, content_type="application/json")
        
        form = ImportForm(document, self.request.user, 
                          self.request.POST, self.request.FILES)
        if form.is_valid():
            form.save()  # create the import
            try:
                form.process()
            except ParseError:
                self.error("Incorrectly formated file, couldn't parse it.")
            return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")
        else:
            return self.error(json.dumps(form.errors))
