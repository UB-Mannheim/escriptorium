import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponse
from django.utils.translation import gettext as _
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic import CreateView, UpdateView, ListView, DetailView

from sorl.thumbnail import get_thumbnail

from core.models import Document, DocumentPart
from core.forms import DocumentForm, DocumentShareForm, MetadataFormSet, DocumentPartUpdateForm


class Home(TemplateView):
    template_name = 'core/home.html'


class DocumentsList(LoginRequiredMixin, ListView):
    model = Document
    paginate_by = 20

    def get_queryset(self):
        return Document.objects.for_user(self.request.user)


class DocumentMixin():
    def get_success_url(self):
        return reverse('document-update', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class CreateDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, CreateView):
    model = Document
    form_class = DocumentForm

    success_message = _("Document created successfully!")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_form'] = MetadataFormSet()
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        metadata_form = MetadataFormSet(self.request.POST)
        if form.is_valid() and metadata_form.is_valid():
            return self.form_valid(form, metadata_form)
        else:
            return self.form_invalid(form)
    
    def form_valid(self, form, metadata_form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        # form.save() has been called, we have an object
        metadata_form.instance = self.object
        metadata_form.save()
        return response


class UpdateDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    success_message = _("Document saved successfully!")

    def get_queryset(self):
        # will raise a 404 instead of a 403 if user can't edit, but avoids a query
        return Document.objects.for_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_publish'] = self.object.owner == self.request.user
        context['metadata_form'] = MetadataFormSet(instance=self.object)
        context['share_form'] = DocumentShareForm(instance=self.object, request=self.request)
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        metadata_form = MetadataFormSet(self.request.POST, instance=self.object)
        if form.is_valid() and metadata_form.is_valid():
            return self.form_valid(form, metadata_form)
        else:
            return self.form_invalid(form)
        
    def form_valid(self, form, metadata_form):
        with transaction.atomic():
            response = super().form_valid(form)
            # at this point the document is saved
            metadata_form.save()
        return response


class ShareDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, UpdateView):
    model = Document
    form_class = DocumentShareForm
    success_message = _("Document shared successfully!")
    http_method_names = ('post',)
        
    def form_valid(self, form):
        if form.instance.workflow_state == Document.WORKFLOW_STATE_DRAFT:
            form.instance.workflow_state = Document.WORKFLOW_STATE_SHARED
        return super().form_valid(form)


class PublishDocument(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    fields = ['workflow_state',]
    http_method_names = ('post',)
    
    def get_queryset(self):
        # will raise a 404 instead of a 403 if user can't edit, but avoids a query
        return Document.objects.for_user(self.request.user)
    
    def get_success_message(self, form_data):
        if self.object.is_archived:
            return _("Document archived successfully!")
        else:
            return _("Document published successfully!")
    
    def get_success_url(self):
        if self.object.is_archived:
            return reverse('documents-list')
        else:
            return reverse('document-update', kwargs={'pk': self.object.pk})


class UploadImageAjax(LoginRequiredMixin, CreateView):
    model = DocumentPart
    fields = ('image',)
    http_method_names = ('post',)
    
    def get_document(self):
        try:
            return Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])
        except Document.DoesNotExist:
            raise Http404
    
    def form_invalid(self, form):
        return HttpResponse(json.dumps({'status': 'error',
                                        'error': form.errors['image']}),
                            content_type="application/json", status=400)
    
    def post(self, request, *args, **kwargs):
        self.document = self.get_document()
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        part = form.save(commit=False)
        part.document = self.document
        try:
            part.name = part.image.file.name.split('.')[0]
        except IndexError:
            part.name = part.image.file.name
        part.save()
        im = get_thumbnail(part.image, '183x294', crop='center', quality=95)
        return HttpResponse(json.dumps({
            'status': 'ok',
            'pk': part.pk,
            'name': part.name,
            'updateUrl': reverse('document-part-update',
                                  kwargs={'pk': self.document.pk, 'part_pk': part.pk}),
            'imgUrl': im.url
        }), content_type="application/json")


class UpdateDocumentPart(LoginRequiredMixin, UpdateView):
    model = DocumentPart
    form_class = DocumentPartUpdateForm
    http_method_names = ('post',)
    pk_url_kwarg = 'part_pk'
    
    def form_invalid(self, form):
        return HttpResponse(json.dumps({'status': 'error', 'errors': form.errors}),
                            content_type="application/json", status=400)
    
    def form_valid(self, form):
        form.save()
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")


class DocumentDetail(DetailView):
    model = Document
