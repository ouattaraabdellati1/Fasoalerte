"""Console de commandement : réservée au personnel connecté, avec rôles et journal d'audit."""
from datetime import timedelta
from functools import wraps
from urllib.parse import quote

from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import (AuditLog, FeedItem, IncidentReport, NationalAlert, PriceCeiling, StatusEvent)
from .uploads import clean_photo
from .web import CSP

MAX_FILE = 5 * 1024 * 1024
UNITS = ["", "Patrouille FDS", "Brigade Contrôle", "Pompiers BNSP", "SAMU", "Protection civile"]


def audit(request, action, detail=""):
    AuditLog.objects.create(user_name=request.user.get_username(), action=action, detail=detail[:255])


def respond(request, template, ctx=None, status=200):
    r = render(request, template, ctx or {}, status=status)
    r["Content-Security-Policy"] = CSP
    r["Cache-Control"] = "no-store"          # rien de sensible dans le cache du navigateur
    r["Referrer-Policy"] = "same-origin"      # (pas "no-referrer" : Django refuserait les formulaires, Origin: null)
    return r


def console_required(perm=None):
    def deco(view):
        @wraps(view)
        def wrapper(request, *a, **k):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('console-login')}?next={quote(request.get_full_path())}")
            if not request.user.is_staff or (perm and not request.user.has_perm(perm)):
                return respond(request, "core/console/denied.html", status=403)
            return view(request, *a, **k)
        return wrapper
    return deco


# ------------------------------------------------------------------ connexion
def login_view(request):
    ip = request.META.get("REMOTE_ADDR", "")
    key = f"console-fail:{ip}"      # compteur en mémoire seulement (jamais en base)
    if cache.get(key, 0) >= 5:
        return respond(request, "core/console/login.html",
                       {"form": AuthenticationForm(), "locked": True}, status=429)
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            login(request, form.get_user())
            cache.delete(key)
            audit(request, "CONNEXION")
            nxt = request.GET.get("next", "")
            if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
                return redirect(nxt)
            return redirect("console-home")
        cache.set(key, cache.get(key, 0) + 1, 15 * 60)
        AuditLog.objects.create(user_name=(request.POST.get("username") or "?")[:150], action="CONNEXION REFUSÉE")
    return respond(request, "core/console/login.html", {"form": form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        audit(request, "DÉCONNEXION")
    logout(request)
    return redirect("console-login")


# ------------------------------------------------------------------ tableau de bord
@console_required()
def home(request):
    now = timezone.localtime()
    month = IncidentReport.objects.none()
    open_qs = IncidentReport.objects.exclude(status=IncidentReport.Status.CLOTURE)
    qs = open_qs
    st = request.GET.get("statut", "ouverts")
    if st == "clos":
        qs = IncidentReport.objects.filter(status=IncidentReport.Status.CLOTURE)
    elif st == "tous":
        qs = IncidentReport.objects.all()
    cat = request.GET.get("categorie", "")
    if cat in IncidentReport.Category.values:
        qs = qs.filter(category=cat)
    urg_rank = {"critique": 0, "eleve": 1, "modere": 2}
    rows = sorted(qs[:300], key=lambda r: (urg_rank.get(r.urgency, 3), -r.created_at.timestamp()))[:50]
    ctx = {
        "kpi_open": open_qs.count(),
        "kpi_critical": open_qs.filter(urgency="critique").count(),
        "kpi_alerts": NationalAlert.objects.filter(is_published=True, published_at__year=now.year,
                                                   published_at__month=now.month).count(),
        "kpi_prices": PriceCeiling.objects.count(),
        "by_cat": open_qs.values("category").annotate(n=Count("id")),
        "rows": rows, "statut": st, "categorie": cat,
        "categories": IncidentReport.Category.choices,
        "active": "home",
    }
    return respond(request, "core/console/home.html", ctx)


# ------------------------------------------------------------------ signalements
class ReportForm(forms.Form):
    urgency = forms.ChoiceField(choices=IncidentReport.Urgency.choices, label="Niveau d'urgence")
    status = forms.TypedChoiceField(choices=IncidentReport.Status.choices, coerce=int, label="Étape")
    assigned_unit = forms.ChoiceField(choices=[(u, u or "— Aucune —") for u in UNITS], required=False, label="Unité affectée")
    official_message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, max_length=500,
                                       label="Message officiel visible par le citoyen")
    note = forms.CharField(max_length=255, required=False, label="Note du journal de l'intervention")


@console_required("core.view_incidentreport")
def report_detail(request, pk):
    rep = get_object_or_404(IncidentReport, pk=pk)
    initial = {"urgency": rep.urgency, "status": rep.status, "assigned_unit": rep.assigned_unit,
               "official_message": rep.official_message}
    form = ReportForm(request.POST or None, initial=initial)
    can_edit = request.user.has_perm("core.change_incidentreport")
    if request.method == "POST":
        if not can_edit:
            return respond(request, "core/console/denied.html", status=403)
        if form.is_valid():
            d = form.cleaned_data
            changed = []
            if d["status"] != rep.status:
                StatusEvent.objects.create(report=rep, status=d["status"], note=d["note"])
                changed.append(f"étape {rep.status}→{d['status']}")
            elif d["note"]:
                StatusEvent.objects.create(report=rep, status=rep.status, note=d["note"])
            if d["urgency"] != rep.urgency:
                changed.append(f"urgence {rep.urgency}→{d['urgency']}")
            rep.urgency, rep.status = d["urgency"], d["status"]
            rep.assigned_unit, rep.official_message = d["assigned_unit"], d["official_message"]
            rep.save()
            audit(request, "SIGNALEMENT MODIFIÉ", f"{rep.tracking_code} " + ", ".join(changed))
            return redirect("console-report", pk=rep.pk)
    return respond(request, "core/console/report.html",
                   {"rep": rep, "form": form, "events": rep.events.all(), "can_edit": can_edit, "active": "home"})


# ------------------------------------------------------------------ alertes
class AlertForm(forms.ModelForm):
    expire_hours = forms.ChoiceField(label="Durée d'affichage", choices=[
        ("6", "6 heures"), ("24", "24 heures"), ("72", "3 jours"), ("0", "Jusqu'à retrait manuel")], initial="24")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
                                       label="Confirmation : votre mot de passe")

    class Meta:
        model = NationalAlert
        fields = ["title", "message", "full_text", "level", "regions", "source", "show_prices",
                  "audio_moore", "audio_dioula", "audio_fulfulde", "audio_francais"]
        labels = {"title": "Titre officiel (60 car. max)", "message": "Consigne claire (320 car. max)",
                  "full_text": "Consignes complètes (facultatif)", "level": "Niveau d'urgence",
                  "regions": "Régions ciblées (vide = national)", "source": "Source",
                  "show_prices": "Afficher la mercuriale dans l'alerte",
                  "audio_moore": "Audio mooré", "audio_dioula": "Audio dioula",
                  "audio_fulfulde": "Audio fulfuldé", "audio_francais": "Audio français"}
        widgets = {"message": forms.Textarea(attrs={"rows": 3, "data-count": "320"}),
                   "title": forms.TextInput(attrs={"data-count": "60"}),
                   "full_text": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *a, user=None, **k):
        super().__init__(*a, **k)
        self.user = user

    def clean(self):
        d = super().clean()
        for f in ("audio_moore", "audio_dioula", "audio_fulfulde", "audio_francais"):
            up = d.get(f)
            if up and hasattr(up, "size") and up.size > MAX_FILE:
                self.add_error(f, "Fichier trop lourd (5 Mo max).")
        pw = d.get("confirm_password")
        if pw is not None and not (self.user and self.user.check_password(pw)):
            self.add_error("confirm_password", "Mot de passe incorrect : alerte NON publiée.")
        return d


@console_required("core.view_nationalalert")
def alerts(request):
    form = AlertForm(user=request.user)
    if request.method == "POST":
        if not request.user.has_perm("core.add_nationalalert"):
            return respond(request, "core/console/denied.html", status=403)
        form = AlertForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            a = form.save(commit=False)
            hrs = int(form.cleaned_data["expire_hours"])
            a.is_published, a.published_at = True, timezone.now()
            a.expires_at = timezone.now() + timedelta(hours=hrs) if hrs else None
            a.save()
            audit(request, "ALERTE PUBLIÉE", f"#{a.id} [{a.level}] {a.title}")
            return redirect("console-alerts")
        audit(request, "ALERTE REFUSÉE", "formulaire invalide ou confirmation incorrecte")
    now = timezone.now()
    return respond(request, "core/console/alerts.html", {
        "form": form, "active": "alerts",
        "alerts": NationalAlert.objects.all()[:20], "now": now,
        "can_add": request.user.has_perm("core.add_nationalalert"),
        "can_change": request.user.has_perm("core.change_nationalalert")})


@require_POST
@console_required("core.change_nationalalert")
def alert_retract(request, pk):
    a = get_object_or_404(NationalAlert, pk=pk)
    a.is_published = False
    a.save(update_fields=["is_published"])
    audit(request, "ALERTE RETIRÉE", f"#{a.id} {a.title}")
    return redirect("console-alerts")


# ------------------------------------------------------------------ prix
@console_required("core.view_priceceiling")
def prices(request):
    errors = []
    can = request.user.has_perm("core.change_priceceiling")
    if request.method == "POST":
        if not can:
            return respond(request, "core/console/denied.html", status=403)
        changes = []
        for p in PriceCeiling.objects.all():
            raw = request.POST.get(f"price_{p.id}", "").strip()
            if not raw:
                continue
            if not raw.isdigit() or not (0 < int(raw) <= 10_000_000):
                errors.append(f"Prix invalide pour {p.product}.")
                continue
            if int(raw) != p.max_price_fcfa:
                changes.append(f"{p.product} {p.max_price_fcfa}→{raw}")
                p.previous_price_fcfa, p.max_price_fcfa = p.max_price_fcfa, int(raw)
                p.save()
        name, unit, newp = (request.POST.get("new_product", "").strip(), request.POST.get("new_unit", "").strip(),
                            request.POST.get("new_price", "").strip())
        if name or unit or newp:
            if name and unit and newp.isdigit() and 0 < int(newp) <= 10_000_000 and request.user.has_perm("core.add_priceceiling"):
                if PriceCeiling.objects.filter(product=name).exists():
                    errors.append("Ce produit existe déjà.")
                else:
                    PriceCeiling.objects.create(product=name[:80], unit=unit[:60], max_price_fcfa=int(newp))
                    changes.append(f"NOUVEAU {name} {newp}")
            else:
                errors.append("Nouveau produit incomplet ou invalide.")
        if changes:
            audit(request, "MERCURIALE MODIFIÉE", "; ".join(changes))
        if not errors:
            return redirect("console-prices")
    return respond(request, "core/console/prices.html", {
        "items": PriceCeiling.objects.order_by("product"), "errors": errors, "can": can, "active": "prices"})


# ------------------------------------------------------------------ fil national
class FeedForm(forms.ModelForm):
    class Meta:
        model = FeedItem
        fields = ["kind", "category", "title", "summary", "source", "region_label",
                  "rumor_label", "fact_real", "image", "attested"]
        labels = {"kind": "Type", "category": "Catégorie", "title": "Titre", "summary": "Texte",
                  "source": "Source officielle", "region_label": "Région (ex : Centre • Ouaga)",
                  "rumor_label": "Étiquette rumeur (ex : FAUX DOCUMENT)", "fact_real": "« Le fait réel » (rumeurs)",
                  "image": "Image (facultatif)", "attested": "Information attestée"}
        widgets = {"summary": forms.Textarea(attrs={"rows": 3}), "fact_real": forms.Textarea(attrs={"rows": 2})}

    def clean_image(self):
        img = self.cleaned_data.get("image")
        if img and hasattr(img, "size"):
            if img.size > MAX_FILE:
                raise ValidationError("Image trop lourde (5 Mo max).")
            try:
                return clean_photo(img)          # vérifie l'image, efface l'EXIF, ré-encode
            except Exception:
                raise ValidationError("Image invalide (JPEG, PNG ou WEBP).")
        return img


@console_required("core.view_feeditem")
def feed(request):
    form = FeedForm()
    can = request.user.has_perm("core.add_feeditem")
    if request.method == "POST":
        if not can:
            return respond(request, "core/console/denied.html", status=403)
        form = FeedForm(request.POST, request.FILES)
        if form.is_valid():
            it = form.save(commit=False)
            it.is_published, it.published_at = True, timezone.now()
            it.save()
            audit(request, "FIL : PUBLICATION", f"#{it.id} {it.title}")
            return redirect("console-feed")
    return respond(request, "core/console/feed.html", {
        "form": form, "items": FeedItem.objects.all()[:30], "can": can,
        "can_change": request.user.has_perm("core.change_feeditem"), "active": "feed"})


@require_POST
@console_required("core.change_feeditem")
def feed_toggle(request, pk):
    it = get_object_or_404(FeedItem, pk=pk)
    it.is_published = not it.is_published
    it.save(update_fields=["is_published"])
    audit(request, "FIL : " + ("PUBLIÉ" if it.is_published else "RETIRÉ"), f"#{it.id} {it.title}")
    return redirect("console-feed")


# ------------------------------------------------------------------ journal d'audit
@console_required("core.view_auditlog")
def audit_view(request):
    return respond(request, "core/console/audit.html", {"logs": AuditLog.objects.all()[:200], "active": "audit"})
