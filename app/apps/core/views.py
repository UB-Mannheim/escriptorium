from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import TemplateView
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.utils.translation import gettext as _
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.db.models import Q

from core.models import Document
from core.forms import DocumentForm


class Home(TemplateView):
    template_name = 'core/home.html'


class DocumentsList(LoginRequiredMixin, ListView):
    model = Document
    paginate_by = 20

    def get_queryset(self):
         #| Q(shared_with_groups__in=self.request.user.groups.all())
        return Document.objects.filter(
            Q(access=Document.ACCESS_PUBLIC) |
            Q(owner=self.request.user)
        ).exclude(workflow_state=Document.WORKFLOW_STATE_ARCHIVED)
       
    

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_publish'] = self.object.owner == self.request.user
        return context


class PublishDocument(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    fields = ['workflow_state',]

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
