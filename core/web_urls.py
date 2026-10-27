from django.urls import path
from . import web

urlpatterns = [
    path("", web.page("core/home.html"), name="home"),
    path("signaler/", web.page("core/report.html"), name="report"),
    path("suivi/", web.page("core/track.html"), name="track"),
    path("alerte/<int:pk>/", web.page_arg("core/alert.html"), name="alert"),
    path("urgences/", web.page("core/urgences.html"), name="urgences"),
    path("sw.js", web.service_worker),
    path("manifest.webmanifest", web.manifest),
]
