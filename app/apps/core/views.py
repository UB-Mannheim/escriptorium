import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.urls import reverse
from django.views.generic import View, TemplateView, ListView, DetailView
from django.views.generic import CreateView, UpdateView, DeleteView, FormView

from easy_thumbnails.files import get_thumbnailer

from versioning.models import NoChangeException
from core.models import Document, DocumentPart
from core.forms import *
from imports.forms import ImportForm


class Home(TemplateView):
    template_name = 'core/home.html'


class DocumentsList(LoginRequiredMixin, ListView):
    model = Document
    paginate_by = 10
    
    def get_queryset(self):
        return (Document.objects
                .for_user(self.request.user)
                .select_related('owner', 'main_script')
                .annotate(parts_updated_at=Max('parts__updated_at')))


class DocumentMixin():
    def get_success_url(self):
        return reverse('document-update', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_metadata_formset(self, *args, instance=None):
        if instance:
            qs = Metadata.objects.filter(Q(public=True) | Q(documentmetadata__document=instance)).distinct()
        else:
            qs = Metadata.objects.filter(public=True)
        return MetadataFormSet(*args, instance=instance, form_kwargs={'choices': qs})


class CreateDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, CreateView):
    model = Document
    form_class = DocumentForm

    success_message = _("Document created successfully!")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_form'] = self.get_metadata_formset()
        return context
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        metadata_form = self.get_metadata_formset(self.request.POST)
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
        if 'metadata_form' not in kwargs:
            context['metadata_form'] = self.get_metadata_formset(instance=self.object)
        context['share_form'] = DocumentShareForm(instance=self.object, request=self.request)
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        metadata_form = self.get_metadata_formset(self.request.POST, instance=self.object)
        if form.is_valid() and metadata_form.is_valid():
            return self.form_valid(form, metadata_form)
        else:
            return self.form_invalid(form, metadata_form)
    
    def form_invalid(self, form, metadata_form):
        return self.render_to_response(self.get_context_data(
            form=form, metadata_form=metadata_form))
    
    def form_valid(self, form, metadata_form):
        with transaction.atomic():
            response = super().form_valid(form)
            # at this point the document is saved
            metadata_form.save()
        return response


class DocumentImages(LoginRequiredMixin, DetailView):
    model = Document
    template_name = "core/document_images.html"
    
    def get_queryset(self):
        # will raise a 404 instead of a 403 if user can't edit, but avoids a query
        return Document.objects.for_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upload_form'] = UploadImageForm(document=self.object)
        context['process_form'] = DocumentProcessForm(self.object, self.request.user)
        context['import_form'] = ImportForm(self.object, self.request.user)
        return context


class ShareDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, UpdateView):
    model = Document
    form_class = DocumentShareForm
    success_message = _("Document shared successfully!")
    http_method_names = ('post',)
    
    def get_redirect_url(self):
        return reverse('document-update', kwargs={'pk': self.object.pk})
    
    def get_queryset(self):
        return Document.objects.for_user(self.request.user).select_related('owner')
    
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


class DocumentPartsProcessAjax(LoginRequiredMixin, View):
    # TODO: move to api
    http_method_names = ('post',)
    
    def get_document(self):
        return Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        try:
            document = self.get_document()
        except (Document.DoesNotExist, DocumentPart.DoesNotExist):
            return HttpResponse(json.dumps({'status': 'Not Found'}),
                                status=404, content_type="application/json")
        
        form = DocumentProcessForm(document, self.request.user, 
                                   self.request.POST, self.request.FILES)
        if form.is_valid():
            try:
                form.process()
            except AlreadyProcessingException:
                return HttpResponse(json.dumps({'status': 'error', 'error': 'Already processing.'}),
                                    content_type="application/json", status=400)
            return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")
        else:
            return HttpResponse(json.dumps({'status': 'error', 'error': json.dumps(form.errors)}),
                                content_type="application/json", status=400)


class DocumentDetail(DetailView):
    model = Document


class EditPart(LoginRequiredMixin, DetailView):
    model = DocumentPart
    pk_url_kwarg = 'part_pk'
    template_name = "core/document_part_edit.html"
    http_method_names = ('get',)
    
    def get_queryset(self):
        return DocumentPart.objects.filter(
            document=self.kwargs.get('pk')).select_related('document')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        # Note: a bit confusing but this view uses the same base template than UpdateDocument
        # so we need context['object'] = document
        context['object'] = self.object.document
        context['document'] = self.object.document
        context['part'] = self.object
        return context
    
    def dispatch(self, *args, **kwargs):
        if not 'part_pk' in self.kwargs:
            try:
                first = self.get_queryset()[0]
                return HttpResponseRedirect(reverse('document-part-edit',
                                                    kwargs={'pk': first.document.pk,
                                                            'part_pk': first.pk}))
            except IndexError:
                raise Http404
        else:
            return super().dispatch(*args, **kwargs)


class ModelsList(LoginRequiredMixin, ListView):
    model = OcrModel
    template_name = "core/models_list.html"
    http_method_names = ('get',)
    
    def get_queryset(self):
        if 'document_pk' in self.kwargs:
            self.document = Document.objects.for_user(self.request.user).get(pk=self.kwargs.get('document_pk'))
            return OcrModel.objects.filter(document=self.document)
        else:
            self.document = None
            return OcrModel.objects.filter(owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.document:
            context['document'] = self.document
            context['object'] = self.document  # legacy
        return context
