import io
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from PIL import Image
from django.core.cache import cache
from django.contrib.auth import get_user_model

from .models import IncidentReport, NationalAlert, PriceCeiling

NOTHROTTLE = {"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}}


@override_settings(MEDIA_ROOT="/tmp/fa_test_media")
class ApiTests(APITestCase):
    def setUp(self):
        cache.clear()      # remet les compteurs de limitation à zéro

    def test_create_report_anonymous_and_track(self):
        r = self.client.post("/api/reports/", {
            "category": "securite", "city": "Ouagadougou",
            "location_hint": "Secteur 30", "description": "Véhicule suspect"})
        self.assertEqual(r.status_code, 201, r.content)
        code = r.json()["tracking_code"]
        self.assertRegex(code, r"^FA-OUAGA-[A-Z2-9]{8}$")
        t = self.client.get(f"/api/reports/{code.lower()}/")
        self.assertEqual(t.status_code, 200)
        body = t.json()
        self.assertEqual(body["status"], 1)
        self.assertEqual(len(body["events"]), 1)
        for forbidden in ("ip", "phone", "latitude", "description"):
            self.assertNotIn(forbidden, body)

    def test_report_needs_place_and_content(self):
        r = self.client.post("/api/reports/", {"category": "route", "description": "x"})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/reports/", {"category": "route", "latitude": 12.3, "longitude": -1.5})
        self.assertEqual(r.status_code, 400)

    def _post(self, **extra):
        data = {"category": "route", "latitude": 12.3, "longitude": -1.5, "description": "x"}
        data.update(extra)
        return self.client.post("/api/reports/", data)

    def test_photo_exif_stripped_and_renamed(self):
        img = Image.new("RGB", (3000, 2000), "red")
        exif = Image.Exif()
        exif[0x010F] = "MarqueTelephone"        # Make
        buf = io.BytesIO()
        img.save(buf, "JPEG", exif=exif)
        up = SimpleUploadedFile("IMG_secret_nom.jpg", buf.getvalue(), content_type="image/jpeg")
        r = self._post(photo=up)
        self.assertEqual(r.status_code, 201, r.content)
        rep = IncidentReport.objects.get()
        self.assertNotIn("IMG_secret_nom", rep.photo.name)
        saved = Image.open(rep.photo.path)
        self.assertEqual(len(saved.getexif()), 0)           # plus aucune métadonnée
        self.assertLessEqual(max(saved.size), 1280)         # redimensionnée

    def test_fake_image_rejected(self):
        up = SimpleUploadedFile("a.jpg", b"<?php echo 1; ?>", content_type="image/jpeg")
        self.assertEqual(self._post(photo=up).status_code, 400)

    def test_fake_audio_rejected(self):
        up = SimpleUploadedFile("a.mp3", b"MZ\x90\x00not audio at all", content_type="audio/mpeg")
        self.assertEqual(self._post(audio=up).status_code, 400)

    def test_good_audio_accepted_and_renamed(self):
        up = SimpleUploadedFile("voix.ogg", b"OggS" + b"\x00" * 40, content_type="audio/ogg")
        self.assertEqual(self._post(audio=up).status_code, 201)
        self.assertNotIn("voix", IncidentReport.objects.get().audio.name)

    def test_bad_gps_rejected(self):
        self.assertEqual(self._post(latitude=999).status_code, 400)

    def test_media_requires_staff(self):
        self.assertEqual(self.client.get("/protected-media/reports/x.jpg").status_code, 302)  # -> login
        U = get_user_model()
        U.objects.create_user("agent", password="pw-Test-12345", is_staff=True)
        self.client.login(username="agent", password="pw-Test-12345")
        self.assertIn(self.client.get("/protected-media/../../etc/passwd").status_code, (400, 404))
        self.assertEqual(self.client.get("/protected-media/inexistant.jpg").status_code, 404)

    def test_rate_limit_on_report_creation(self):
        codes = [self._post().status_code for _ in range(12)]
        self.assertEqual(codes.count(201), 10)
        self.assertEqual(codes[-1], 429)

    def test_unknown_code_404(self):
        self.assertEqual(self.client.get("/api/reports/FA-BF-ZZZZZZ/").status_code, 404)

    def test_alerts_filtering(self):
        now = timezone.now()
        NationalAlert.objects.create(title="A", message="m", is_published=True)
        NationalAlert.objects.create(title="Brouillon", message="m", is_published=False)
        NationalAlert.objects.create(title="Expirée", message="m", is_published=True,
                                     expires_at=now - timedelta(hours=1))
        NationalAlert.objects.create(title="Centre", message="m", is_published=True, regions="Centre")
        titles = [a["title"] for a in self.client.get("/api/alerts/").json()]
        self.assertCountEqual(titles, ["A", "Centre"])
        titles = [a["title"] for a in self.client.get("/api/alerts/?region=Hauts-Bassins").json()]
        self.assertEqual(titles, ["A"])

    def test_prices(self):
        PriceCeiling.objects.create(product="Riz local", unit="sac 50 kg", max_price_fcfa=19500)
        self.assertEqual(self.client.get("/api/prices/").json()[0]["max_price_fcfa"], 19500)

    def test_codes_unique(self):
        codes = {IncidentReport.objects.create(category="autre", description="x", city="Kaya").tracking_code
                 for _ in range(50)}
        self.assertEqual(len(codes), 50)


class PwaTests(APITestCase):
    def test_pages_ok_with_security_headers_and_no_cookie(self):
        for url in ("/", "/signaler/", "/suivi/", "/urgences/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertIn("script-src 'self'", r["Content-Security-Policy"])
            self.assertNotIn("Set-Cookie", r.headers)          # aucune trace côté navigateur
            self.assertNotIn(b"<script>", r.content)             # pas de script inline (CSP)

    def test_manifest_and_service_worker(self):
        m = self.client.get("/manifest.webmanifest")
        self.assertEqual(m.json()["short_name"], "FasoAlerte")
        s = self.client.get("/sw.js")
        self.assertEqual(s["Service-Worker-Allowed"], "/")
        self.assertIn(b"fa-v4", s.content)


class FeedAndAlertPageTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_feed_only_published_and_filters(self):
        from .models import FeedItem
        FeedItem.objects.create(title="A", summary="s", source="X", is_published=True, category="route")
        FeedItem.objects.create(title="B", summary="s", source="X", is_published=True, category="verif", kind="rumor", fact_real="réel")
        FeedItem.objects.create(title="Brouillon", summary="s", source="X", is_published=False)
        titles = [i["title"] for i in self.client.get("/api/feed/").json()]
        self.assertCountEqual(titles, ["A", "B"])
        self.assertEqual([i["title"] for i in self.client.get("/api/feed/?category=route").json()], ["A"])
        self.assertEqual([i["title"] for i in self.client.get("/api/feed/?kind=rumor").json()], ["B"])

    def test_alert_detail_and_page(self):
        a = NationalAlert.objects.create(title="T", message="m", full_text="long", is_published=True, show_prices=True)
        d = self.client.get(f"/api/alerts/{a.id}/").json()
        self.assertEqual(d["full_text"], "long")
        self.assertEqual(d["audio"], {})
        draft = NationalAlert.objects.create(title="D", message="m", is_published=False)
        self.assertEqual(self.client.get(f"/api/alerts/{draft.id}/").status_code, 404)
        r = self.client.get(f"/alerte/{a.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("script-src 'self'", r["Content-Security-Policy"])

    def test_official_media_public_but_limited(self):
        import os
        root = "/tmp/fa_test_media/official/audio"
        os.makedirs(root, exist_ok=True)
        open(f"{root}/v.mp3", "wb").write(b"ID3xxxx")
        with override_settings(MEDIA_ROOT="/tmp/fa_test_media"):
            self.assertEqual(self.client.get("/official/audio/v.mp3").status_code, 200)     # public
            self.assertEqual(self.client.get("/official/audio/nope.mp3").status_code, 404)
            self.assertEqual(self.client.get("/official/../reports/x.jpg").status_code, 404)
            self.assertEqual(self.client.get("/official/audio/v.php").status_code, 404)     # extension refusée
            self.assertIn(self.client.get("/protected-media/official/audio/v.mp3").status_code, (302,))  # dossier citoyen: privé


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])   # tests plus rapides seulement
class ConsoleTests(APITestCase):
    PW = "Mot-de-passe-Test-123"

    def setUp(self):
        from django.core.management import call_command
        cache.clear()
        call_command("setup_roles", stdout=io.StringIO())
        U = get_user_model()
        from django.contrib.auth.models import Group
        self.admin = U.objects.create_user("chef", password=self.PW, is_staff=True)
        self.admin.groups.add(Group.objects.get(name="Administrateur"))
        self.officer = U.objects.create_user("officier", password=self.PW, is_staff=True)
        self.officer.groups.add(Group.objects.get(name="Officier de permanence"))
        self.trader = U.objects.create_user("commerce", password=self.PW, is_staff=True)
        self.trader.groups.add(Group.objects.get(name="Régulateur du commerce"))
        self.citizen = U.objects.create_user("simple", password=self.PW, is_staff=False)

    def test_login_required_and_non_staff_refused(self):
        r = self.client.get("/commandement/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/commandement/connexion/", r["Location"])
        self.client.login(username="simple", password=self.PW)
        self.assertEqual(self.client.get("/commandement/").status_code, 403)

    def test_no_open_redirect_and_audit_on_login(self):
        r = self.client.post("/commandement/connexion/?next=https://evil.example/", {"username": "chef", "password": self.PW})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/commandement/")
        from .models import AuditLog
        self.assertTrue(AuditLog.objects.filter(user_name="chef", action="CONNEXION").exists())

    def test_login_lockout_after_5_failures(self):
        for _ in range(5):
            self.client.post("/commandement/connexion/", {"username": "chef", "password": "faux"})
        r = self.client.post("/commandement/connexion/", {"username": "chef", "password": self.PW})
        self.assertEqual(r.status_code, 429)

    def test_roles_limit_actions(self):
        data = {"title": "T", "message": "m", "level": "info", "expire_hours": "24", "confirm_password": self.PW}
        self.client.login(username="officier", password=self.PW)
        self.assertEqual(self.client.post("/commandement/alertes/", data).status_code, 403)   # officier: pas d'alerte
        self.assertEqual(self.client.get("/commandement/prix/").status_code, 403)
        self.client.logout()
        self.client.login(username="commerce", password=self.PW)
        self.assertEqual(self.client.get("/commandement/prix/").status_code, 200)
        self.assertEqual(self.client.get("/commandement/alertes/").status_code, 403)
        self.assertEqual(self.client.get("/commandement/audit/").status_code, 403)

    def test_publish_alert_needs_password_and_is_audited(self):
        from .models import AuditLog
        self.client.login(username="chef", password=self.PW)
        bad = {"title": "T", "message": "m", "level": "max", "expire_hours": "24", "confirm_password": "faux"}
        self.assertEqual(self.client.post("/commandement/alertes/", bad).status_code, 200)
        self.assertEqual(NationalAlert.objects.count(), 0)
        ok = dict(bad, confirm_password=self.PW)
        self.assertEqual(self.client.post("/commandement/alertes/", ok).status_code, 302)
        a = NationalAlert.objects.get()
        self.assertTrue(a.is_published and a.expires_at)
        self.assertTrue(AuditLog.objects.filter(action="ALERTE PUBLIÉE").exists())
        self.assertEqual(len(self.client.get("/api/alerts/").json()), 1)       # visible côté citoyen
        self.client.post(f"/commandement/alertes/{a.id}/retirer/")
        self.assertEqual(len(self.client.get("/api/alerts/").json()), 0)

    def test_price_update_keeps_previous(self):
        p = PriceCeiling.objects.create(product="Riz", unit="sac", max_price_fcfa=20000)
        self.client.login(username="commerce", password=self.PW)
        self.client.post("/commandement/prix/", {f"price_{p.id}": "19500"})
        p.refresh_from_db()
        self.assertEqual((p.max_price_fcfa, p.previous_price_fcfa), (19500, 20000))
        r = self.client.post("/commandement/prix/", {f"price_{p.id}": "abc"})
        self.assertEqual(r.status_code, 200)                                     # refusé
        p.refresh_from_db(); self.assertEqual(p.max_price_fcfa, 19500)

    def test_report_handling_updates_citizen_tracking(self):
        rep = IncidentReport.objects.create(category="securite", description="x", city="Ouagadougou")
        self.client.login(username="officier", password=self.PW)
        r = self.client.post(f"/commandement/signalements/{rep.pk}/", {
            "urgency": "critique", "status": "3", "assigned_unit": "Patrouille FDS",
            "official_message": "Patrouille sur place.", "note": "Unité 4B engagée"})
        self.assertEqual(r.status_code, 302)
        t = self.client.get(f"/api/reports/{rep.tracking_code}/").json()
        self.assertEqual((t["status"], t["assigned_unit"]), (3, "Patrouille FDS"))
        self.assertEqual(t["official_message"], "Patrouille sur place.")
        self.assertEqual(t["events"][-1]["note"], "Unité 4B engagée")

    def test_audit_log_is_read_only_in_admin(self):
        from django.contrib.admin.sites import site
        from .models import AuditLog
        ma = site._registry[AuditLog]
        self.assertFalse(ma.has_delete_permission(None))
        self.assertFalse(ma.has_change_permission(None))

    def test_console_pages_render_with_csp(self):
        self.client.login(username="chef", password=self.PW)
        for u in ("/commandement/", "/commandement/alertes/", "/commandement/prix/", "/commandement/fil/", "/commandement/audit/"):
            r = self.client.get(u)
            self.assertEqual(r.status_code, 200, u)
            self.assertIn("script-src 'self'", r["Content-Security-Policy"])
            self.assertEqual(r["Cache-Control"], "no-store")
            self.assertEqual(r["Referrer-Policy"], "same-origin")   # sinon Origin: null et la connexion échoue
