# FasoAlerte – Backend (étape 1)

Prototype Django + Django REST Framework. Données de démo fictives.

## Lancer dans VS Code (Windows, PowerShell)
```powershell
cd fasoalerte
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```
- Admin (équipe de commandement) : http://127.0.0.1:8000/admin/
- Tests : `python manage.py test`

## API
| Méthode | URL | Rôle |
|---|---|---|
| POST | /api/reports/ | Signalement anonyme (renvoie `tracking_code`) |
| GET | /api/reports/FA-OUAGA-XXXXXX/ | Suivi de dossier |
| GET | /api/alerts/?region=Centre | Alertes publiées |
| GET | /api/prices/ | Mercuriale |

## Anonymat
Aucun champ nom / téléphone / IP / email en base. Le seul lien citoyen ↔ dossier est le code de suivi.
En production : désactiver les logs d'accès du serveur web, HTTPS obligatoire, hébergement conforme CIL.
