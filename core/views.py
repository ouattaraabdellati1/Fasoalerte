from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils._os import safe_join
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response

from .models import IncidentReport, NationalAlert, PriceCeiling, StatusEvent
from .serializers import (NationalAlertSerializer, PriceCeilingSerializer,
                          ReportCreateSerializer, ReportTrackSerializer)


class ReportCreateView(generics.CreateAPIView):
    """POST /api/reports/ – signalement 100 % anonyme (aucune authentification)."""
    serializer_class = ReportCreateSerializer
    authentication_classes = []          # pas de session, pas de cookie
    throttle_scope = "report_create"

    def perform_create(self, serializer):
        report = serializer.save()
        StatusEvent.objects.create(report=report, status=IncidentReport.Status.TRANSMIS,
                                   note="Jeton d'anonymat généré avec succès.")


class ReportTrackView(generics.RetrieveAPIView):
    """GET /api/reports/<code>/ – suivi d'un dossier avec son code."""
    serializer_class = ReportTrackSerializer
    queryset = IncidentReport.objects.all()
    lookup_field = "tracking_code"
    authentication_classes = []
    throttle_scope = "report_track"

    def get_object(self):
        self.kwargs["tracking_code"] = self.kwargs["tracking_code"].upper()
        return super().get_object()


class AlertListView(generics.ListAPIView):
    """GET /api/alerts/?region=Centre – alertes publiées et non expirées."""
    serializer_class = NationalAlertSerializer
    authentication_classes = []
    pagination_class = None
    throttle_scope = "public_read"

    def get_queryset(self):
        now = timezone.now()
        qs = NationalAlert.objects.filter(is_published=True, published_at__lte=now) \
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        region = self.request.query_params.get("region")
        if region:
            qs = qs.filter(Q(regions="") | Q(regions__icontains=region))
        return qs


class PriceListView(generics.ListAPIView):
    """GET /api/prices/ – mercuriale officielle."""
    serializer_class = PriceCeilingSerializer
    queryset = PriceCeiling.objects.order_by("product")
    authentication_classes = []
    pagination_class = None
    throttle_scope = "public_read"


@staff_member_required
def protected_media(request, path):
    """Photos/audios des citoyens : visibles uniquement par le personnel connecté."""
    try:
        full = safe_join(settings.MEDIA_ROOT, path)    # bloque ../../ (path traversal)
        return FileResponse(open(full, "rb"))
    except (ValueError, FileNotFoundError, IsADirectoryError, PermissionError):
        raise Http404
