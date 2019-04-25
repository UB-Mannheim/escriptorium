import bleach
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
        return Document.objects.for_user(self.request.user).select_related('owner').annotate(parts_updated_at=Max('parts__updated_at'))


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
        if 'metadata_form' not in kwargs:
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
        settings, created = DocumentProcessSettings.objects.get_or_create(document=self.object)
        context['settings_form'] = DocumentProcessForm(self.object, self.request.user,
                                                       instance=settings)
        context['import_form'] = ImportForm(self.object, self.request.user)
        return context


class DocumentTranscription(LoginRequiredMixin, DetailView):
    model = DocumentPart
    pk_url_kwarg = 'part_pk'
    template_name = "core/document_transcription.html"
    http_method_names = ('get',)
    
    def get_queryset(self):
        if not hasattr(self, 'document'):
            self.document = Document.objects.for_user(self.request.user).get(pk=self.kwargs.get('pk'))
        return DocumentPart.objects.filter(
            document=self.document,
            workflow_state=DocumentPart.WORKFLOW_STATE_TRANSCRIBING).prefetch_related(
                'lines', 'lines__transcriptions', 'lines__transcriptions__transcription')

    def get_object(self):
        if not 'part_pk' in self.kwargs:
            try:
                return self.get_queryset()[0]
            except IndexError:
                raise Http404
        else:
            return super().get_object()

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        # Note: a bit confusing but this view uses the same base template than UpdateDocument
        # so we need context['object'] = document
        context['object'] = self.document
        context['part'] = self.object
        
        # Note .next() and .previous() don't work because can't filter against it
        context['previous'] = self.get_queryset().filter(order__lt=self.object.order).order_by('-order').first()
        context['next'] = self.get_queryset().filter(order__gt=self.object.order).order_by('order').first()
        return context


class LineTranscriptionUpdateAjax(LoginRequiredMixin, View):
    http_method_names = ('post',)

    def post(self, request, *args, **kwargs):
        line = Line.objects.get(pk=request.POST['line'])
        transcription = Transcription.objects.get(pk=request.POST['transcription'])
        try:
            lt = line.transcriptions.get(transcription=transcription)
        except LineTranscription.DoesNotExist:
            lt = LineTranscription.objects.create(
                line=line,
                transcription=transcription,
                version_author=self.request.user.username,
                content=request.POST['content'])
        else:
            if request.POST.get('new_version'):
                try:
                    lt.new_version()
                    lt.save()
                except NoChangeException:
                    return HttpResponse(json.dumps({'status': 'error', 'msg': _('No changes detected.')}),
                                        content_type="application/json")
                else:
                    return HttpResponse(json.dumps({'status': 'ok', 'transcription': lt.versions[0]}),
                                        content_type="application/json")
            
            if lt.version_author != self.request.user.username:
                lt.new_version()
            if 'content' in request.POST:
                lt.content = request.POST['content']
            lt.save()
        line.document_part.calculate_progress()
        line.document_part.save()
        return HttpResponse(json.dumps({'status': 'ok', 'transcription': lt.pack()}),
                            content_type="application/json")


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
    http_method_names = ('post',)
    
    def get_document(self):
        return Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        try:
            document = self.get_document()
        except (Document.DoesNotExist, DocumentPart.DoesNotExist):
            return HttpResponse(json.dumps({'status': 'Not Found'}),
                                status=404, content_type="application/json")
        
        settings, created = DocumentProcessSettings.objects.get_or_create(document=document)
        form = DocumentProcessForm(document, self.request.user, 
                                   self.request.POST, self.request.FILES,
                                   instance=settings)
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


class DocumentExport(LoginRequiredMixin, DetailView):
    model = Document
    
    def get_object(self):
        return Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])
    
    def render_to_response(self, context, **kwargs):
        transcription = Transcription.objects.get(pk=self.kwargs['trans_pk'])
        lines = (LineTranscription.objects.filter(transcription=transcription)
                 .order_by('line__document_part__order', 'line__order')
                 .select_related('line', 'line__document_part'))
        response = render(self.request, 'core/export/simple.txt',
                          context={'lines': lines},
                          content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="%s.txt"' % slugify(self.object.name)
        return response


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
