from rest_framework import serializers
from .uploads import clean_audio, clean_photo
from .models import IncidentReport, NationalAlert, PriceCeiling, StatusEvent


class ReportCreateSerializer(serializers.ModelSerializer):
    """Entrée : uniquement ce que le citoyen saisit. Sortie : le code de suivi."""

    class Meta:
        model = IncidentReport
        fields = ["category", "city", "location_hint", "latitude", "longitude",
                  "description", "photo", "audio", "tracking_code"]
        read_only_fields = ["tracking_code"]

    description = serializers.CharField(required=False, allow_blank=True, max_length=3000)
    location_hint = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_photo(self, f):
        if f and f.size > 2 * 1024 * 1024:       # brut ; après nettoyage elle fait ~100 Ko
            raise serializers.ValidationError("Photo trop lourde (max 2 Mo avant compression).")
        return clean_photo(f) if f else f

    def validate_audio(self, f):
        if f and f.size > 1024 * 1024:
            raise serializers.ValidationError("Note vocale trop longue (max 1 Mo).")
        return clean_audio(f) if f else f

    def validate_latitude(self, v):
        if v is not None and not -90 <= v <= 90:
            raise serializers.ValidationError("Latitude invalide.")
        return v

    def validate_longitude(self, v):
        if v is not None and not -180 <= v <= 180:
            raise serializers.ValidationError("Longitude invalide.")
        return v

    def validate(self, data):
        has_place = data.get("latitude") is not None or data.get("location_hint")
        if not has_place:
            raise serializers.ValidationError("Indiquez le lieu (GPS ou repère physique).")
        if not (data.get("description") or data.get("audio")):
            raise serializers.ValidationError("Ajoutez une description écrite ou vocale.")
        return data


class StatusEventSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = StatusEvent
        fields = ["status", "label", "note", "at"]


class ReportTrackSerializer(serializers.ModelSerializer):
    """Sortie publique du suivi : aucune donnée sensible renvoyée."""
    category_label = serializers.CharField(source="get_category_display")
    status_label = serializers.CharField(source="get_status_display")
    events = StatusEventSerializer(many=True)

    class Meta:
        model = IncidentReport
        fields = ["tracking_code", "category_label", "city", "created_at", "status",
                  "status_label", "assigned_unit", "official_message", "events"]


class NationalAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = NationalAlert
        fields = ["id", "title", "message", "level", "regions", "source", "published_at", "expires_at"]


class PriceCeilingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceCeiling
        fields = ["product", "unit", "max_price_fcfa", "previous_price_fcfa", "updated_at"]
