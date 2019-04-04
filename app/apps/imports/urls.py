from django.urls import path

from imports.views import *

urlpatterns = [
    path('documents/<int:pk>/import/', DocumentImport.as_view(), name='document-import'),
]
