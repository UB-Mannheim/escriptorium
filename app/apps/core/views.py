import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.urls import reverse
from django.views.generic import View, TemplateView, ListView, DetailView
from django.views.generic import CreateView, UpdateView, DeleteView

from core.models import (Project, Document, DocumentPart, Metadata,
                         OcrModel, OcrModelRight, AlreadyProcessingException)

from core.forms import (ProjectForm,
                        DocumentForm,
                        MetadataFormSet,
                        ProjectShareForm,
                        DocumentShareForm,

                        BinarizeForm,
                        SegmentForm,
                        TranscribeForm,
                        SegTrainForm,
                        RecTrainForm,

                        UploadImageForm,
                        ModelUploadForm,
                        ModelRightsForm)
from imports.forms import ImportForm, ExportForm
from reporting.models import TaskReport
from users.models import User


logger = logging.getLogger(__name__)


class Home(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['VERSION_DATE'] = settings.VERSION_DATE
        context['KRAKEN_VERSION'] = settings.KRAKEN_VERSION
        return context


class PerPageMixin():
    MAX_PAGINATE_BY = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['select_per_page'] = True
        return context

    def get_paginate_by(self, queryset):
        try:
            _paginate_by = int(self.request.GET.get("paginate_by", self.paginate_by))
        except ValueError:
            _paginate_by = self.paginate_by
        return _paginate_by if _paginate_by <= self.MAX_PAGINATE_BY else self.paginate_by


class ProjectList(LoginRequiredMixin, ListView):
    model = Project
    paginate_by = 10

    def get_queryset(self):
        return (Project.objects
                .for_user_read(self.request.user)
                .annotate(documents_count=Count('documents'))
                .select_related('owner'))


class CreateProject(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Project
    form_class = ProjectForm
    success_message = _("Project created successfully!")

    def get_success_url(self):
        return reverse('projects-list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        return response


class DocumentsList(LoginRequiredMixin, PerPageMixin, ListView):
    model = Document
    paginate_by = 10

    def get_queryset(self):
        self.project = (Project.objects
                        .get(slug=self.kwargs['slug']))
        try:
            Project.objects.for_user_read(self.request.user).get(pk=self.project.pk)
        except Project.DoesNotExist:
            raise PermissionDenied

        # Note: using subqueries for last edited part and first part (thumbnail)
        # to lower the amount of queries will make the sql time sky rocket!
        qs = (Document.objects
              .for_user(self.request.user)
              .filter(project=self.project)
              .prefetch_related('tags', 'parts', 'shared_with_groups', 'shared_with_users')
              )
        for tag in self.request.GET.getlist('tags'):
            qs = qs.filter(tags__name=tag)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['document_tags'] = list(self.project.document_tags.values())
        if self.project.owner == self.request.user:
            context['share_form'] = ProjectShareForm(instance=self.project,
                                                     request=self.request)

            context['can_create_document'] = True
        else:
            # can only create a new document if the whole project as been shared
            # not if some specific documents
            try:
                context['can_create_document'] = (Project.objects
                                                  .for_user_write(self.request.user)
                                                  .get(slug=self.kwargs['slug']))
            except Project.DoesNotExist:
                context['can_create_document'] = False

        context['filters'] = self.request.GET.getlist('tags')

        return context


class DocumentMixin():
    def get_success_url(self):
        return reverse('document-update', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_metadata_formset(self, *args, instance=None):
        if instance:
            qs = (Metadata.objects.filter(Q(public=True)
                                          | Q(documentmetadata__document=instance))
                  .distinct())
        else:
            qs = Metadata.objects.filter(public=True)
        return MetadataFormSet(*args, instance=instance, form_kwargs={'choices': qs})

    def get_object(self):
        obj = super().get_object()
        try:
            # we fetched the object already, now we check that the user has perms to edit it
            Document.objects.for_user(self.request.user).get(pk=obj.pk)
        except Document.DoesNotExist:
            raise PermissionDenied
        return obj


class CreateDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, CreateView):
    model = Document
    form_class = DocumentForm

    success_message = _("Document created successfully!")

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.initial = {'project': self.project}
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_form'] = self.get_metadata_formset()
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            self.project = (Project.objects
                            .for_user_write(self.request.user)
                            .get(slug=self.request.resolver_match.kwargs['slug']))
        except Project.DoesNotExist:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = None
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_publish'] = self.object.owner == self.request.user
        if 'metadata_form' not in kwargs:
            context['metadata_form'] = self.get_metadata_formset(instance=self.object)

        if self.object.owner == self.request.user:
            context['share_form'] = DocumentShareForm(instance=self.object,
                                                      request=self.request)

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


class DocumentImages(LoginRequiredMixin, DocumentMixin, DetailView):
    model = Document
    template_name = "core/document_images.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_disk_storage_left'] = settings.DISABLE_QUOTAS or self.request.user.has_free_disk_storage()
        context['has_cpu_minutes_left'] = settings.DISABLE_QUOTAS or self.request.user.has_free_cpu_minutes()
        context['has_gpu_minutes_left'] = settings.DISABLE_QUOTAS or self.request.user.has_free_gpu_minutes()

        context['upload_form'] = UploadImageForm(document=self.object, user=self.request.user)

        # process forms
        context['binarize_form'] = BinarizeForm(self.object, self.request.user)
        context['segment_form'] = SegmentForm(self.object, self.request.user)
        context['transcribe_form'] = TranscribeForm(self.object, self.request.user)
        context['segtrain_form'] = SegTrainForm(self.object, self.request.user)
        context['rectrain_form'] = RecTrainForm(self.object, self.request.user)

        context['import_form'] = ImportForm(self.object, self.request.user)
        context['export_form'] = ExportForm(self.object, self.request.user)
        return context


class ShareDocument(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    form_class = DocumentShareForm
    success_message = _("Document shared successfully!")
    http_method_names = ('post',)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        return reverse('document-update', kwargs={'pk': self.object.pk})

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)


class DeleteDocumentUserShare(LoginRequiredMixin, View):
    http_method_names = ('post',)

    def post(self, *args, **kwargs):
        try:
            document = Document.objects.get(pk=self.request.POST['document'])
        except KeyError:
            raise HttpResponseBadRequest

        document.shared_with_users.remove(self.request.user)
        return HttpResponseRedirect(self.get_success_url(document))

    def get_success_url(self, document):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        else:
            return reverse('documents-list', kwargs={'slug': document.project.slug})


class ShareProject(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Project
    form_class = ProjectShareForm
    success_message = _("Project shared successfully!")
    http_method_names = ('post',)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        return reverse('documents-list', kwargs={'slug': self.object.slug})

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


class DeleteProjectUserShare(LoginRequiredMixin, View):
    http_method_names = ('post',)

    def post(self, *args, **kwargs):
        try:
            project = Project.objects.get(pk=self.request.POST['project'])
        except KeyError:
            raise HttpResponseBadRequest

        project.shared_with_users.remove(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        else:
            return reverse('projects-list')


class PublishDocument(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    fields = ['workflow_state']
    http_method_names = ('post',)

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def get_success_message(self, form_data):
        if self.object.is_archived:
            return _("Document archived successfully!")
        else:
            return _("Document published successfully!")

    def get_success_url(self):
        if self.object.is_archived:
            return reverse('documents-list', kwargs={'slug': self.object.project.slug})
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
        except Document.DoesNotExist:
            return HttpResponse(json.dumps({'status': 'Not Found'}),
                                status=404, content_type="application/json")

        task = self.request.POST.get('task')
        if task == 'binarize':
            form_class = BinarizeForm
        elif task == 'segment':
            form_class = SegmentForm
        elif task == 'transcribe':
            form_class = TranscribeForm
        elif task == 'segtrain':
            form_class = SegTrainForm
        elif task == 'train':
            form_class = RecTrainForm

        form = form_class(document,
                          self.request.user,
                          self.request.POST,
                          self.request.FILES)

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

    def get_object(self):
        obj = super().get_object()
        try:
            # we fetched the object already, now we check that the user has perms to edit it
            Document.objects.for_user(self.request.user).get(pk=obj.document.pk)
        except Document.DoesNotExist:
            raise PermissionDenied
        return obj

    def get_queryset(self):
        return DocumentPart.objects.filter(
            document=self.kwargs.get('pk')).select_related('document')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


class DocumentModels(LoginRequiredMixin, ListView):
    model = OcrModel
    template_name = "core/models_list/document_models.html"
    http_method_names = ('get',)
    paginate_by = 20

    def get_queryset(self):
        try:
            self.document = Document.objects.for_user(self.request.user).get(pk=self.kwargs.get('document_pk'))
        except Document.DoesNotExist:
            raise PermissionDenied
        return self.document.ocr_models.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document
        context['object'] = self.document  # legacy
        return context


class UserModels(LoginRequiredMixin, ListView):
    model = OcrModel
    template_name = "core/models_list/main.html"
    http_method_names = ('get',)
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        models = OcrModel.objects.exclude(file="").filter(
            Q(public=True) |
            Q(owner=user) |
            Q(ocr_model_rights__user=user) |
            Q(ocr_model_rights__group__user=user)
        ).distinct()

        script_filter = self.request.GET.get('script_filter', '')
        if script_filter:
            models = models.filter(script__name=script_filter)

        return models

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['script_filter'] = self.request.GET.get('script_filter', '')
        return context


class ModelUpload(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = OcrModel
    form_class = ModelUploadForm
    success_message = _("Model uploaded successfully!")

    def get_success_url(self):
        return reverse('user-models')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_disk_storage_left'] = settings.DISABLE_QUOTAS or self.request.user.has_free_disk_storage()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs


class ModelDelete(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = OcrModel
    success_message = _("Model deleted successfully!")

    def get_queryset(self):
        return OcrModel.objects.filter(owner=self.request.user)

    def get_success_url(self):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        else:
            return reverse('user-models')


class ModelCancelTraining(LoginRequiredMixin, SuccessMessageMixin, DetailView):
    model = OcrModel
    http_method_names = ('post',)

    def get_success_url(self):
        if 'next' in self.request.GET:
            return self.request.GET.get('next')
        else:
            return reverse('user-models')

    def post(self, request, *args, **kwargs):
        model = self.get_object()
        try:
            model.cancel_training()
        except Exception as e:
            logger.exception(e)
            return HttpResponse({'status': 'failed'}, status=400,
                                content_type="application/json")
        else:
            return HttpResponseRedirect(self.get_success_url())


class ModelRights(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = OcrModelRight
    template_name = "core/models_list/rights/main.html"
    success_message = _("Right added successfully!")
    form_class = ModelRightsForm

    def get_context_data(self, **kwargs):
        model = get_object_or_404(OcrModel, pk=self.kwargs['pk'])

        if self.request.user != model.owner or model.public:
            raise PermissionDenied

        kwargs['object_list'] = model.ocr_model_rights.all()
        kwargs['model_name'] = model.name

        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'ocr_model_id': self.kwargs['pk']})
        return kwargs

    def form_valid(self, form):
        form.instance.ocr_model = OcrModel.objects.get(pk=self.kwargs['pk'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('model-rights', kwargs={'pk': self.kwargs['pk']})


class ModelRightDelete(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = OcrModelRight
    template_name = 'core/models_list/rights/delete.html'
    success_message = _("Right deleted successfully!")

    def get_context_data(self, **kwargs):
        model = get_object_or_404(OcrModel, pk=self.kwargs['modelPk'])

        if self.request.user != model.owner or model.public:
            raise PermissionDenied

        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse('model-rights', kwargs={'pk': self.kwargs['modelPk']})


class DocumentsTasksList(LoginRequiredMixin, TemplateView):
    template_name = 'core/documents_tasks_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['task_states'] = {state: label for state, label in TaskReport.WORKFLOW_STATE_CHOICES}
        context['users'] = {
            user.id: user.username for user in User.objects.all()
        } if self.request.user and self.request.user.is_staff else {}

        return context
