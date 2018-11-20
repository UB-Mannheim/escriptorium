from django.urls import path

from core.views import Home


urlpatterns = [
    path('', Home.as_view(), name='home'),
]
