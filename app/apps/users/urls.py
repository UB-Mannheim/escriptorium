from django.urls import path, include

from users.views import SendInvitation, AcceptInvitation


urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('invite/', SendInvitation.as_view(), name='send-invitation'),
    path('accept/<token>/', AcceptInvitation.as_view(), name='accept-invitation'),
]
