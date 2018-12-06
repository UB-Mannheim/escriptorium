from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponseForbidden
from django.utils.translation import gettext as _
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic import CreateView, UpdateView, ListView, DetailView

from core.models import Document
from core.forms import DocumentForm, DocumentShareForm, MetadataFormSet


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
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class UpdateDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    success_message = _("Document saved successfully!")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_publish'] = self.object.owner == self.request.user
        if self.request.method == 'POST':
            context['metadata_form'] = MetadataFormSet(self.request.POST, instance=self.object)
        else:
            context['metadata_form'] = MetadataFormSet(instance=self.object)

        print(context['metadata_form'].forms[0].fields)
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
            # print(metadata_form.deleted_forms)
            metadata_form.save()
        return response


class ShareDocument(LoginRequiredMixin, SuccessMessageMixin, DocumentMixin, UpdateView):
    model = Document
    form_class = DocumentShareForm
    success_message = _("Document shared successfully!")
    
    def get(self, request, *args, **kwargs):
        # TODO: should be 405 method not allowed
        raise HttpResponseForbidden
    
    def form_valid(self, form):
        if form.instance.workflow_state == Document.WORKFLOW_STATE_DRAFT:
            form.instance.workflow_state = Document.WORKFLOW_STATE_SHARED
        return super().form_valid(form)


class PublishDocument(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    fields = ['workflow_state',]
    
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
    
    def get(self, request, *args, **kwargs):
        # TODO: should be 405 method not allowed
        raise HttpResponseForbidden

    # TODO: only owner


class DocumentDetail(DetailView):
    model = Document
