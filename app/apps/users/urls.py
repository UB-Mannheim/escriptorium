from django.urls import path, include

from users.views import SendInvitation, AcceptInvitation
from django.contrib.auth.decorators import permission_required

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('invite/', permission_required('users.can_invite')(SendInvitation.as_view()), name='send-invitation'),
    path('accept/<token>/', AcceptInvitation.as_view(), name='accept-invitation'),
]
