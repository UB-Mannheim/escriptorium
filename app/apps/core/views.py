import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponse
from django.utils.translation import gettext as _
from django.urls import reverse
from django.views.generic import View, TemplateView, ListView, DetailView
from django.views.generic import CreateView, UpdateView, DeleteView, FormView

from celery import chain

from core.models import Document, DocumentPart
from core.forms import *
from core.tasks import generate_part_thumbnail, segment, binarize


class Home(TemplateView):
    template_name = 'core/home.html'


class DocumentsList(LoginRequiredMixin, ListView):
    model = Document
    paginate_by = 20

    def get_queryset(self):
        return Document.objects.for_user(self.request.user).select_related('owner')


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
        context['upload_form'] = UploadImageForm()
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
    form_class = UploadImageForm
    http_method_names = ('post',)
    
    def get_document(self):
        return Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])
    
    def form_invalid(self, form):
        return HttpResponse(json.dumps({'status': 'error', 'errors': form.errors}),
                            content_type="application/json", status=400)
    
    def post(self, request, *args, **kwargs):
        try:
            self.document = self.get_document()
        except Document.DoesNotExist:
            return HttpResponse(json.dumps({'status': 'Not Found'}),
                                status=404, content_type="application/json")
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        part = form.save(commit=False)
        part.document = self.document
        try:
            part.name = part.image.file.name.split('.')[0]
        except IndexError:
            part.name = part.image.file.name
        part.save()

        if form.cleaned_data['auto_process']:
            # generate the thumbnail asynchronously because we don't want to generate 200 at once
            generate_part_thumbnail.delay(part.pk)
            chain(binarize.si(part.pk, user_pk=self.request.user.pk),
                  segment.si(part.pk, user_pk=self.request.user.pk,
                             text_direction=form.cleaned_data['text_direction'])).delay()
        
        return HttpResponse(json.dumps({
            'status': 'ok',
            'part': {
                'pk': part.pk,
                'name': part.name,
                'thumbnailUrl': part.image.url,
                'sourceImg': {'url': part.image.url,
                              'width': part.image.width,
                              'height': part.image.height},
                'bwImgUrl': None,
                'updateUrl': reverse('document-part-update',
                                     kwargs={'pk': self.document.pk, 'part_pk': part.pk}),
                'deleteUrl': reverse('document-part-delete',
                                     kwargs={'pk': self.document.pk, 'part_pk': part.pk}),
                'partUrl': reverse('document-part',
                                   kwargs={'pk': self.document.pk, 'part_pk': part.pk}),

                'workflow': 0
            }
        }), content_type="application/json")


class DocumentPartAjax(LoginRequiredMixin, UpdateView):
    model = DocumentPart
    form_class = DocumentPartUpdateForm
    http_method_names = ('get', 'post',)
    pk_url_kwarg = 'part_pk'
    
    def form_invalid(self, form):
        return HttpResponse(json.dumps({'status': 'error', 'errors': form.errors}),
                            content_type="application/json", status=400)
    
    def form_valid(self, form):
        form.save()
        return HttpResponse(json.dumps({'status': 'ok'}),
                            content_type="application/json")
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return HttpResponse(json.dumps({
            'pk': self.object.pk,
            'bwImgUrl': getattr(self.object.bw_image, 'url'),
            'lines': [{'pk': line.pk, 'box': line.box}
                      for line in self.object.lines.all()]
        }), content_type="application/json")


class DeleteDocumentPartAjax(LoginRequiredMixin, DeleteView):
    model = DocumentPart
    pk_url_kwarg = 'part_pk'
    http_method_names = ('post',)

    def get_object(self):
        Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])
        return super().get_object()
    
    def delete(self, request, *args, **kwargs):
        try:
            object = self.get_object()
        except Document.DoesNotExist:
            return HttpResponse(json.dumps({'status': 'Not Found'}),
                                status=404, content_type="application/json")
        object.delete()
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")


class DocumentPartsProcessAjax(LoginRequiredMixin, View):
    # TODO: form ?
    http_method_names = ('post',)
    
    def get_document(self):
        return Document.objects.for_user(self.request.user).get(pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        try:
            document = self.get_document()
        except (Document.DoesNotExist, DocumentPart.DoesNotExist):
            return HttpResponse(json.dumps({'status': 'Not Found'}),
                                status=404, content_type="application/json")

        pks = self.request.POST.getlist('parts[]')
        process = self.request.POST['process']
        if process == 'binarize':
            for pk in pks:
                binarize.delay(pk, user_pk=self.request.user.pk)
        elif process == 'segment':
            parts = DocumentPart.objects.filter(pk__in=pks)
            text_direction = self.request.POST.get('text_direction')
            for part in parts:
                if part.workflow_state < part.WORKFLOW_STATE_BINARIZED:
                    chain(binarize.si(part.pk, user_pk=self.request.user.pk),
                          segment.si(part.pk, user_pk=self.request.user.pk,
                                     text_direction=text_direction)).delay()
                else:
                    segment.delay(part.pk, user_pk=self.request.user.pk,
                                  text_direction=text_direction)
        elif process == 'transcribe':
            pass
        else:
            self.request.user.notify("Ewww", level="danger")
            raise ValueError
        
        return HttpResponse(json.dumps({'status': 'ok'}), content_type="application/json")


class DocumentDetail(DetailView):
    model = Document
