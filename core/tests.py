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
        self.assertIn(b"fa-v1", s.content)
