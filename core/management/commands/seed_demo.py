from django.core.management.base import BaseCommand
from core.models import NationalAlert, PriceCeiling


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
        self.stdout.write("Données de démo créées.")
