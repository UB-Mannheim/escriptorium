import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchQuery, SearchVector, TrigramBase
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Page, Paginator
from django.db import transaction
from django.db.models import Max, Q, Count
from django.db.models.functions import Greatest
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.urls import reverse
from django.views.generic import View, TemplateView, ListView, DetailView
from django.views.generic import CreateView, UpdateView, DeleteView, FormView
from elasticsearch import exceptions, Elasticsearch
from PIL import Image, ImageDraw
from urllib.parse import unquote_plus

from core.models import (Line, Project, Document, DocumentPart, Metadata,
                         OcrModel, OcrModelRight, AlreadyProcessingException, LineTranscription)

from core.forms import (SearchForm,
                        ProjectForm,
                        DocumentForm,
                        DocumentSearchForm,
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
from core.search import ES_HOST
from imports.forms import ImportForm, ExportForm


logger = logging.getLogger(__name__)


class Home(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['VERSION_DATE'] = settings.VERSION_DATE
        context['KRAKEN_VERSION'] = settings.KRAKEN_VERSION
        return context


class ESPaginator(Paginator):

    def __init__(self, *args, **kwargs):
        self._count = kwargs.pop('total')
        super(ESPaginator, self).__init__(*args, **kwargs)

    @cached_property
    def count(self):
        return self._count

    def page(self, number):
        number = self.validate_number(number)
        return Page(self.object_list, number, self)


class Search(LoginRequiredMixin, FormView, TemplateView):
    template_name = 'core/search.html'
    form_class = SearchForm
    paginate_by = 100

    def get_context_data(self, **kwargs):
        context = super(Search, self).get_context_data(**kwargs)
        context['display_right_warning'] = False

        try:
            page = int(self.request.GET.get('page', '1'))
        except ValueError:
            page = 1

        # Search
        search = self.request.GET.get('query', '')

        user_projects = list(Project.objects.for_user_read(self.request.user).values_list('id', flat=True))
        try:
            project = int(self.request.GET.get('project', ''))

            if project in user_projects:
                projects = [project]
            else:
                projects = user_projects
                context['display_right_warning'] = True
        except ValueError:
            projects = user_projects

        es_client = Elasticsearch(hosts=[ES_HOST])
        body = {
            'from': (page-1) * self.paginate_by,
            'size': self.paginate_by,
            'sort' : ['_score'],
            'query': {
                'bool': {
                    'must': [
                        { 'term': { 'have_access': self.request.user.id } },
                        { 'terms': { 'project_id': projects } },
                        {
                            'match': {
                                'transcription': {
                                    'query': unquote_plus(search),
                                    'fuzziness': 'AUTO'
                                }
                            }
                        }
                    ]
                }
            },
            'highlight': {
                'pre_tags' : ['<strong class="text-success">'],
                'post_tags' : ['</strong>'],
                'fields': {
                    'transcription': {}
                }
            }
        }

        try:
            es_results = es_client.search(index=settings.ELASTICSEARCH_COMMON_INDEX, body=body)
        except exceptions.ConnectionError as e:
            context['es_error'] = str(e)
            return context

        template_results = [self.convert_hit_to_template(hit) for hit in es_results['hits']['hits']]
        results = [result.values() for result in template_results]

        # Pagination
        paginator = ESPaginator(results, self.paginate_by, total=int(es_results['hits']['total']['value']))

        if page > paginator.num_pages:
            page = paginator.num_pages

        context['page_obj'] = paginator.page(page)
        context['is_paginated'] = paginator.num_pages > 1

        return context

    def convert_hit_to_template(self, hit):
        hit_source = hit['_source']
        return {
            'content': hit.get('highlight', {}).get('transcription', [])[0],
            'part': DocumentPart.objects.get(pk=hit['_id']),
            'document': Document.objects.get(pk=hit_source['document_id']),
            'project': Project.objects.get(pk=hit_source['project_id']),
            'score': hit['_score'],
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['search'] = self.request.GET.get('query')
        kwargs['project'] = self.request.GET.get('project')
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('search')


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


class DocumentsList(LoginRequiredMixin, ListView):
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
        return (Document.objects
                .for_user(self.request.user)
                .filter(project=self.project)
                )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
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
        context['upload_form'] = UploadImageForm(document=self.object)

        # process forms
        context['binarize_form'] = BinarizeForm(self.object, self.request.user)
        context['segment_form'] = SegmentForm(self.object, self.request.user)
        context['transcribe_form'] = TranscribeForm(self.object, self.request.user)
        context['segtrain_form'] = SegTrainForm(self.object, self.request.user)
        context['rectrain_form'] = RecTrainForm(self.object, self.request.user)

        context['import_form'] = ImportForm(self.object, self.request.user)
        context['export_form'] = ExportForm(self.object, self.request.user)
        return context


class TrigramWordSimilarity(TrigramBase):
    function = 'WORD_SIMILARITY'


class DocumentSearch(LoginRequiredMixin, FormView, ListView):
    model = Document
    form_class = DocumentSearchForm
    template_name = "core/document_search.html"

    def get_queryset(self):
        # Prevent from entering string values, eg: paginate_by=twenty
        try:
            paginate_by = int(self.request.GET.get('paginate_by', 100))
        except ValueError:
            paginate_by = 100

        # Force to paginate between 20 (min) and 250 (max) entries
        self.paginate_by = min(max(paginate_by, 20), 250)

        search = self.request.GET.get('query')
        search_type = self.request.GET.get('search_type', 'plain')
        trigram_mode = self.request.GET.get('trigram_mode', False)
        trigram_threshold = self.request.GET.get('trigram_threshold', 0.3)

        if not search:
            return LineTranscription.objects.none()

        # Using SearchVector
        if not trigram_mode:
            return LineTranscription.objects.select_related(
                'line', 'line__document_part', 'transcription'
            ).annotate(
                search=SearchVector('content', 'transcription__name', 'line__document_part__name')
            ).filter(
                line__document_part__document=self.kwargs.get('pk'),
                search=SearchQuery(search, search_type=search_type)
            )

        # Using Trigram Similarity
        return LineTranscription.objects.select_related(
            'line', 'line__document_part', 'transcription'
        ).annotate(
            similarity=Greatest(
                TrigramWordSimilarity('content', search),
                TrigramWordSimilarity('transcription__name', search),
                TrigramWordSimilarity('line__document_part__name', search)
            )
        ).filter(
            line__document_part__document=self.kwargs.get('pk'),
            similarity__gt=trigram_threshold
        ).order_by('-similarity')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['search'] = self.request.GET.get('query')
        kwargs['search_type'] = self.request.GET.get('search_type', 'plain')
        kwargs['trigram_mode'] = self.request.GET.get('trigram_mode', False)
        kwargs['trigram_threshold'] = self.request.GET.get('trigram_threshold', 0.3)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['pagination_values'] = [20, 50, 100, 250]
        return context

    def get_success_url(self):
        return reverse('document-search', kwargs={'pk': self.kwargs.get('pk')})


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


class RetrieveLineCrop(LoginRequiredMixin, View):
    model = Line
    pk_url_kwarg = 'line_pk'
    http_method_names = ('get',)

    def get(self, request, **kwargs):
        line = Line.objects.get(document_part__document=self.kwargs.get('pk'), pk=self.kwargs.get('line_pk'))
        full_image = Image.open(line.document_part.image)

        # Converting image if necessary
        if full_image.mode != "RGB":
            full_image = full_image.convert("RGB")

        # Croping the mask bounding box
        bbox = line.get_box()
        crop = full_image.crop([bbox[0] - 15, bbox[1] - 15, bbox[2] + 15, bbox[3] + 15])

        # Drawing the mask on the cropped image
        canvas = ImageDraw.Draw(crop, "RGBA")
        canvas.polygon([(x - bbox[0] + 15, y - bbox[1] + 15) for x,y in (line.mask or line.baseline)], outline="red", fill="#ff000022")

        response = HttpResponse(content_type="image/jpeg")
        crop.save(response, "JPEG")
        patch_cache_control(response, max_age=10*60)
        return response
