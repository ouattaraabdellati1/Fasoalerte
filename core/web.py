"""Pages de la PWA citoyenne (HTML) + manifest + service worker."""
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

# Politique de sécurité : seul NOTRE site peut charger des scripts/styles.
# Même si quelqu'un réussissait à injecter du HTML, le navigateur refuserait de l'exécuter.
CSP = ("default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
       "style-src 'self'; script-src 'self'; connect-src 'self'; manifest-src 'self'; "
       "worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


def page(template):
    @require_GET
    def view(request):
        r = render(request, template)
        r["Content-Security-Policy"] = CSP
        r["Referrer-Policy"] = "no-referrer"
        r["Permissions-Policy"] = "geolocation=(self), microphone=(self), camera=()"
        return r
    return view


def page_arg(template):
    """Même chose que page(), pour les adresses qui contiennent un numéro."""
    inner = page(template)

    def view(request, **kwargs):
        return inner(request)
    return view


@require_GET
def service_worker(request):
    js = (Path(__file__).parent / "pwa" / "sw.js").read_text(encoding="utf-8")
    r = HttpResponse(js, content_type="application/javascript")
    r["Service-Worker-Allowed"] = "/"
    r["Cache-Control"] = "no-cache"
    return r


@require_GET
def manifest(request):
    data = {
        "name": "FasoAlerte", "short_name": "FasoAlerte", "lang": "fr",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#f4f6fb", "theme_color": "#0b4a2c",
        "icons": [
            {"src": "/static/core/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/core/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")
