from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLES = {
    "Administrateur": "__all__",
    "Officier de permanence": ["view_incidentreport", "change_incidentreport", "add_statusevent", "view_nationalalert"],
    "Régulateur du commerce": ["view_incidentreport", "view_priceceiling", "change_priceceiling", "add_priceceiling"],
    "Communication (SIG)": ["add_nationalalert", "change_nationalalert", "view_nationalalert",
                            "add_feeditem", "change_feeditem", "view_feeditem"],
}


class Command(BaseCommand):
    help = "Crée les rôles du personnel (groupes) avec leurs permissions."

    def handle(self, *a, **k):
        core = Permission.objects.filter(content_type__app_label="core")
        for name, codes in ROLES.items():
            g, _ = Group.objects.get_or_create(name=name)
            g.permissions.set(core if codes == "__all__" else core.filter(codename__in=codes))
            self.stdout.write(f"Rôle prêt : {name}")
        self.stdout.write("Ajoutez un membre du personnel dans /admin/ : cocher « Statut équipe » + choisir un groupe.")
