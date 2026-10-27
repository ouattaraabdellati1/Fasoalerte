from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.views import official_media, protected_media

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/", include("core.urls")),
    path("protected-media/<path:path>", protected_media),   # réservé au personnel connecté
    path("official/<path:path>", official_media),            # audio/images officiels (publics)
    path(getattr(settings, "COMMAND_URL", "commandement/"), include("core.console_urls")),   # console du personnel
    path("", include("core.web_urls")),                     # pages de l'appli citoyenne (PWA)
]
