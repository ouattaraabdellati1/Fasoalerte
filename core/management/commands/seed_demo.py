from django.core.management.base import BaseCommand
from core.models import FeedItem, NationalAlert, PriceCeiling


class Command(BaseCommand):
    help = "Données de DÉMONSTRATION (fictives) pour le prototype."

    def handle(self, *a, **k):
        for p, u, m, old in [("Riz local", "sac 50 kg", 19500, 22500), ("Maïs blanc", "plat Yorba", 650, 800),
                             ("Huile raffinée", "bidon 5 L", 5250, 5500), ("Sucre SN SOSUCO", "paquet 1 kg", 750, None),
                             ("Baguette", "200 g", 150, None)]:
            PriceCeiling.objects.update_or_create(product=p, defaults=dict(unit=u, max_price_fcfa=m, previous_price_fcfa=old))
        NationalAlert.objects.get_or_create(title="[DÉMO] Axe RN1 Ouaga-Bobo", defaults=dict(
            message="Message de démonstration – donnée fictive.", level="important", is_published=True,
            source="Prototype"))
        NationalAlert.objects.filter(title__startswith="[DÉMO]").update(
            level="max", full_text="Consignes de démonstration : restez à l'écoute des communiqués officiels. "
            "Évitez les déplacements non essentiels sur l'axe concerné. Gardez vos pièces d'identité.",
            show_prices=True, message="Consignes de sécurité et restriction nocturne temporaire sur le corridor. "
            "Restez à l'écoute des communiqués officiels.")
        for d in [
            dict(kind="info", category="securite", title="Renforcement des patrouilles et contrôle de zone",
                 summary="Opérations conjointes de sécurisation dans les quartiers périphériques. Munissez-vous de vos pièces d'identité en cours de validité.",
                 source="FDS / Police", region_label="Centre • Ouaga"),
            dict(kind="rumor", category="verif", title="Faux avis de recrutement WhatsApp : vigilance",
                 summary="Un message viral promet une intégration directe dans la fonction publique contre frais de dossier Mobile Money. C'est une escroquerie.",
                 rumor_label="FAUX DOCUMENT", source="Ministère de la Fonction Publique",
                 fact_real="Tous les concours d'État sont publiés exclusivement sur la plateforme officielle du ministère."),
            dict(kind="info", category="verif", title="Circulaire ministérielle sur l'approvisionnement en vivres",
                 summary="Le déblocage de 40 000 tonnes de vivres par la SONAGESS pour les ménages vulnérables est effectif et encadré par les comités locaux.",
                 source="Service d'Information du Gouvernement"),
            dict(kind="info", category="route", title="Travaux d'urgence sur le pont de Nobéré (Axe RN5)",
                 summary="Passage alterné pour les véhicules lourds. Ralentissement estimé à 35 minutes. Respectez les signaux de guidage.",
                 source="Ministère des Infrastructures", region_label="RN5 • Manga"),
        ]:
            FeedItem.objects.get_or_create(title="[DÉMO] " + d["title"], defaults=dict(d, title="[DÉMO] " + d["title"], is_published=True))
        self.stdout.write("Données de démo créées.")
