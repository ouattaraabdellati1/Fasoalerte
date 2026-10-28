# Mettre FasoAlerte en ligne sur PythonAnywhere (gratuit, HTTPS)

Résultat : une adresse stable `https://TONNOM.pythonanywhere.com`, ouvrable sur ton iPhone, avec GPS, micro, photo et installation sur l'écran d'accueil.
Les noms de boutons de PythonAnywhere peuvent légèrement changer : si un libellé diffère, cherche le plus proche.

## Étape A : sur ton PC (une fois)

1. Dézippe `fasoalerte_v5_hebergement.zip` dans ton dossier `faso alerte` (remplace `config/settings.py` et `.gitignore`).
2. Vérifie que tout marche encore : `python manage.py test` puis `python manage.py runserver`.
3. Envoie sur GitHub, une commande à la fois :
```powershell
git add .
```
```powershell
git commit -m "Preparation hebergement PythonAnywhere"
```
```powershell
git push
```

## Étape B : créer le compte

1. Va sur **pythonanywhere.com** > **Pricing & signup** > **Create a Beginner account** (gratuit).
2. Choisis ton **nom d'utilisateur** avec soin : c'est l'adresse de ton site (`TONNOM.pythonanywhere.com`). Un nom professionnel est préférable pour la bourse.
3. Confirme ton e-mail.

Dans la suite, remplace partout **TONNOM** par ton nom d'utilisateur.

## Étape C : récupérer le code

1. Onglet **Consoles** > **Bash** (ouvre un terminal dans le navigateur).
2. Télécharge ton projet :
```bash
git clone https://github.com/ouattaraabdellati1/fasoalerte.git
```
3. Crée l'environnement Python. Choisis la **version la plus récente** proposée (3.12 ou plus). Exemple avec 3.12 :
```bash
mkvirtualenv venv --python=python3.12
```
(Si la commande dit que cette version n'existe pas, essaie `python3.13`, ou `python3.11`.)
4. Installe les paquets :
```bash
cd ~/fasoalerte
pip install -r requirements.txt
```
5. Prépare la base et les fichiers :
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py setup_roles
python manage.py createsuperuser
```
Pour `createsuperuser`, choisis un **mot de passe long et unique** (rien ne s'affiche quand tu tapes).
6. (Optionnel, pour la démonstration) charge les données d'exemple : `python manage.py seed_demo`

## Étape D : créer l'application web

1. Onglet **Web** > **Add a new web app**.
2. **Next**, puis choisis **Manual configuration** (surtout pas « Django »), puis la **même version de Python** qu'à l'étape C. **Next**.
3. Sur la page de configuration, remplis :
   - **Source code** : `/home/TONNOM/fasoalerte`
   - **Virtualenv** : `/home/TONNOM/.virtualenvs/venv`

## Étape E : le fichier WSGI

1. Sur la page **Web**, clique sur le lien **WSGI configuration file** (`/var/www/TONNOM_pythonanywhere_com_wsgi.py`).
2. **Supprime tout** son contenu et colle ceci (adapte les 3 lignes marquées `# A CHANGER`) :
```python
import os
import sys

path = "/home/TONNOM/fasoalerte"                      # A CHANGER (TONNOM)
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "0"
os.environ["DJANGO_SECRET_KEY"] = "COLLE-ICI-UNE-LONGUE-CLE-ALEATOIRE"   # A CHANGER
os.environ["DJANGO_ALLOWED_HOSTS"] = "TONNOM.pythonanywhere.com"          # A CHANGER (TONNOM)
os.environ["DJANGO_ADMIN_URL"] = "gestion-choisis-un-mot-secret/"         # A CHANGER

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
3. Pour fabriquer la clé secrète, dans la console Bash :
```bash
python -c "import secrets; print(secrets.token_urlsafe(60))"
```
Copie le résultat à la place de `COLLE-ICI-UNE-LONGUE-CLE-ALEATOIRE`. **Ne publie jamais cette clé** (elle reste dans ce fichier, pas sur GitHub).
4. **Save** (en haut à droite).

## Étape F : fichiers statiques

Sur la page **Web**, section **Static files**, ajoute une ligne :
- **URL** : `/static/`
- **Directory** : `/home/TONNOM/fasoalerte/staticfiles`

## Étape G : lancer

1. Page **Web** > gros bouton vert **Reload TONNOM.pythonanywhere.com**.
2. Ouvre `https://TONNOM.pythonanywhere.com/` : tu dois voir l'accueil.
3. Console du personnel : `https://TONNOM.pythonanywhere.com/commandement/`.
4. Admin des comptes : `https://TONNOM.pythonanywhere.com/` + le mot secret choisi (ex. `gestion-choisis-un-mot-secret/`). L'ancienne adresse `/admin/` ne marche plus, c'est voulu.

## Étape H : sur ton iPhone

1. Safari > ouvre `https://TONNOM.pythonanywhere.com/`.
2. **Partager** > **Sur l'écran d'accueil**.
3. Teste : GPS, photo, note vocale, signalement, suivi, mode avion.

## Mettre à jour plus tard

Quand tu modifies le code sur ton PC et que tu fais `git push`, dans la console Bash de PythonAnywhere :
```bash
cd ~/fasoalerte
git pull
workon venv
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```
puis **Reload** sur la page Web.

## En cas de problème

| Symptôme | Piste |
|---|---|
| Page « Something went wrong » | Page **Web** > **Error log** : la dernière ligne indique la cause. |
| Erreur `DJANGO_SECRET_KEY` ou `DJANGO_ALLOWED_HOSTS` | Une ligne `os.environ[...]` manque ou est mal écrite dans le fichier WSGI. |
| `DisallowedHost` / erreur 400 | `DJANGO_ALLOWED_HOSTS` ne correspond pas exactement à `TONNOM.pythonanywhere.com`. |
| Page sans style, sans icônes | L'étape F (Static files) manque, ou `collectstatic` n'a pas été lancé. Puis **Reload**. |
| Redirection infinie vers HTTPS | Ajoute `os.environ["DJANGO_SSL_REDIRECT"] = "0"` dans le fichier WSGI, puis **Reload**. |
| Ancienne version affichée | `git pull`, `collectstatic`, **Reload**, puis ferme et rouvre l'appli sur l'iPhone. |
| Erreur CSRF sur la console | Vérifie que tu es bien en `https://` avec la bonne adresse. |

## Sécurité : à retenir

- C'est une **démonstration**. N'y mets pas de vraies données de citoyens.
- Mot de passe administrateur long et unique. Adresse admin secrète.
- Ne partage jamais le fichier WSGI (il contient la clé secrète).
- Le plan gratuit a des limites (calcul, disque, renouvellement périodique) : vérifie-les sur le site de PythonAnywhere.
- Pour un usage réel : serveur dédié, PostgreSQL, double authentification, sauvegardes chiffrées et audit de sécurité.
