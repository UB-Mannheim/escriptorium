"""escriptorium URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('imports.urls')),
    path('', include('users.urls')),
    path('', include('reporting.urls')),
    path('api/', include('api.urls', namespace='api')),
    path('captcha/', include('captcha.urls')),
    path('', include('django_prometheus.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
]

if settings.DEBUG:
    try:
        import debug_toolbar
    except ImportError:
        pass
    else:
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls)), ]

    # simulates a 500 to test error logging
    from django.views.defaults import server_error
    urlpatterns += [path('500/', server_error),
                    path('404/', TemplateView.as_view(template_name='404.html'))]

    # Serve static files in development
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
