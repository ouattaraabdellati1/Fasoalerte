import secrets
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

# Alphabet sans caractères ambigus (0/O, 1/I) pour dicter le code par téléphone/SMS
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

CITY_CODES = {
    "ouagadougou": "OUAGA",
    "bobo-dioulasso": "BOBO",
    "koudougou": "KDG",
    "kaya": "KAYA",
    "fada": "FADA",
}


def make_tracking_code(city: str = "") -> str:
    prefix = CITY_CODES.get(city.strip().lower(), "BF")
    return f"FA-{prefix}-" + "".join(secrets.choice(_ALPHABET) for _ in range(8))


AUDIO_EXT = FileExtensionValidator(["mp3", "m4a", "ogg", "wav", "aac"])


class IncidentReport(models.Model):
    class Category(models.TextChoices):
        SECURITE = "securite", "Sécurité"
        ROUTE = "route", "Route / Accident"
        DISPARITION = "disparition", "Disparition"
        FRAUDE_PRIX = "fraude_prix", "Fraude & Prix"
        AUTRE = "autre", "Autre urgence citoyenne"

    class Urgency(models.TextChoices):
        MODERE = "modere", "Modéré"
        ELEVE = "eleve", "Élevé"
        CRITIQUE = "critique", "Critique"

    class Status(models.IntegerChoices):
        TRANSMIS = 1, "Signalement transmis et chiffré"
        RECU = 2, "Réception centre de commandement"
        EN_COURS = 3, "Vérification et affectation patrouille"
        CLOTURE = 4, "Clôture du dossier"

    # Jeton public anonyme : seul lien entre le citoyen et son dossier.
    tracking_code = models.CharField(max_length=24, unique=True, editable=False)
    category = models.CharField(max_length=20, choices=Category.choices)
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.MODERE)
    status = models.PositiveSmallIntegerField(choices=Status.choices, default=Status.TRANSMIS)

    city = models.CharField(max_length=80, blank=True)
    location_hint = models.CharField(max_length=255, blank=True, help_text="Repère physique")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="reports/photos/", blank=True)
    audio = models.FileField(upload_to="reports/audio/", blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    assigned_unit = models.CharField(max_length=80, blank=True, help_text="Ex : Patrouille FDS, Pompiers BNSP")
    official_message = models.TextField(blank=True, help_text="Message public affiché au citoyen")
    # Volontairement AUCUN champ IP / nom / téléphone / email.

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            for _ in range(10):
                code = make_tracking_code(self.city)
                if not IncidentReport.objects.filter(tracking_code=code).exists():
                    self.tracking_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.tracking_code} ({self.get_category_display()})"


class StatusEvent(models.Model):
    """Ligne de la timeline « Évolution de l'intervention »."""
    report = models.ForeignKey(IncidentReport, related_name="events", on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=IncidentReport.Status.choices)
    note = models.CharField(max_length=255, blank=True)
    at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["at"]


class NationalAlert(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Information"
        IMPORTANT = "important", "Important"
        MAX = "max", "Maximum (sonore)"

    title = models.CharField(max_length=60)
    message = models.CharField(max_length=320)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    regions = models.CharField(max_length=255, blank=True, help_text="Vide = national. Sinon, régions séparées par des virgules")
    source = models.CharField(max_length=120, blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    full_text = models.TextField(blank=True, help_text="Consignes complètes (page de l'alerte)")
    show_prices = models.BooleanField(default=False, help_text="Afficher la mercuriale sur la page de l'alerte")
    # Diffusion vocale officielle (fichiers publics, ajoutés par le personnel)
    audio_moore = models.FileField(upload_to="official/audio/", blank=True, validators=[AUDIO_EXT])
    audio_dioula = models.FileField(upload_to="official/audio/", blank=True, validators=[AUDIO_EXT])
    audio_fulfulde = models.FileField(upload_to="official/audio/", blank=True, validators=[AUDIO_EXT])
    audio_francais = models.FileField(upload_to="official/audio/", blank=True, validators=[AUDIO_EXT])

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class FeedItem(models.Model):
    """Carte du « Fil National Certifié » : information officielle ou démenti de rumeur."""

    class Kind(models.TextChoices):
        INFO = "info", "Information officielle"
        RUMOR = "rumor", "Rumeur démentie"

    class Category(models.TextChoices):
        SECURITE = "securite", "Sécurité Civile"
        ROUTE = "route", "Trafic & Routes"
        VERIF = "verif", "Vérification"
        AUTRE = "autre", "Autre"

    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.INFO)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.SECURITE)
    title = models.CharField(max_length=140)
    summary = models.TextField(max_length=600)
    source = models.CharField(max_length=120, help_text="Ex : FDS / Police, Ministère de la Fonction Publique")
    region_label = models.CharField(max_length=60, blank=True, help_text="Ex : Centre • Ouaga")
    rumor_label = models.CharField(max_length=40, blank=True, help_text="Ex : FAUX DOCUMENT (rumeurs)")
    fact_real = models.TextField(max_length=600, blank=True, help_text="« Le fait réel » (rumeurs)")
    image = models.ImageField(upload_to="official/images/", blank=True)
    attested = models.BooleanField(default=True, help_text="Information attestée par l'autorité")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class PriceCeiling(models.Model):
    product = models.CharField(max_length=80, unique=True)
    unit = models.CharField(max_length=60, help_text="Ex : sac 50 kg, bidon 5 L")
    max_price_fcfa = models.PositiveIntegerField()
    previous_price_fcfa = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product} – {self.max_price_fcfa} F"


class AuditLog(models.Model):
    """Journal d'audit du personnel (qui a fait quoi). Jamais d'information sur les citoyens."""
    user_name = models.CharField(max_length=150)
    action = models.CharField(max_length=40)
    detail = models.CharField(max_length=255, blank=True)
    at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-at"]

    def __str__(self):
        return f"{self.at:%d/%m %H:%M} {self.user_name} {self.action}"
