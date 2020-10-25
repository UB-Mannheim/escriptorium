from django.urls import path, include

from users.views import SendInvitation, AcceptInvitation, Profile, ContactUsView, CreateGroup, InviteToTeam,RemoveFromTeam
from django.contrib.auth.decorators import permission_required

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('profile/', Profile.as_view(), name='user_profile'),
    path('contact/', ContactUsView.as_view(), name='contactus'),
    path('teams/', CreateGroup.as_view(), name='teams'),
    path('teams/<int:pk>', InviteToTeam.as_view(), name='team-invite'),
    path('teams/<int:pk>/remove', RemoveFromTeam.as_view(), name='team-remove-user'),
    path('invite/',
         permission_required('users.can_invite', raise_exception=True)(SendInvitation.as_view()),
         name='send-invitation'),
    path('accept/<token>/', AcceptInvitation.as_view(), name='accept-invitation'),
]
