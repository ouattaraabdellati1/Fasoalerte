from django.urls import path
from . import console as c

urlpatterns = [
    path("", c.home, name="console-home"),
    path("connexion/", c.login_view, name="console-login"),
    path("deconnexion/", c.logout_view, name="console-logout"),
    path("signalements/<int:pk>/", c.report_detail, name="console-report"),
    path("alertes/", c.alerts, name="console-alerts"),
    path("alertes/<int:pk>/retirer/", c.alert_retract, name="console-alert-retract"),
    path("prix/", c.prices, name="console-prices"),
    path("fil/", c.feed, name="console-feed"),
    path("fil/<int:pk>/basculer/", c.feed_toggle, name="console-feed-toggle"),
    path("audit/", c.audit_view, name="console-audit"),
]
