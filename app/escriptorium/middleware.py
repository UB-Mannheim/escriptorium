from django.conf import settings
from django.shortcuts import render
from django.urls import resolve
from rest_framework.authtoken.models import Token


class ForceScriptNamePathMiddleware:
    """
    Make request.path carry FORCE_SCRIPT_NAME under ASGI.

    WSGIRequest builds request.path from SCRIPT_NAME + PATH_INFO, but
    ASGIRequest only honours scope["root_path"] and ignores
    FORCE_SCRIPT_NAME, so absolute URLs derived from request.path
    (DRF pagination links, HttpResponseRedirect(request.get_full_path()))
    miss the subpath prefix when running under daphne.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        script_name = getattr(settings, 'FORCE_SCRIPT_NAME', '') or ''
        if script_name and not request.path.startswith(script_name):
            request.path = script_name + request.path
        return self.get_response(request)


class AccountExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # allow access to the logout view even if the account is expired
        current_url = resolve(request.path_info).url_name
        if current_url == 'logout':
            return self.get_response(request)

        # check if the user is authenticated via session or token
        token_key = request.META.get('HTTP_AUTHORIZATION')
        token = None

        # if a token is provided fetch the associated user
        if token_key:
            try:
                token_key = token_key.split('Token ')[1]
                token = Token.objects.get(key=token_key)
                request.user = token.user
            except (Token.DoesNotExist, IndexError):
                pass  # token is invalid or doesn't exist

        # skip check for unlogged users
        if not request.user.is_authenticated:
            return self.get_response(request)

        # check if the user's account has expired
        user = request.user
        if user.is_account_expired():
            try:
                if token:
                    token.delete()

            except Token.DoesNotExist:
                pass
            return render(request, 'users/account_expired.html', status=403)

        return self.get_response(request)
