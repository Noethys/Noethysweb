#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

#########################################################################################
#              Fichier de configuration à modifier selon les besoins
#########################################################################################

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ----------------- Secret Key : Saisissez une clé aléatoire de votre choix --------------

SECRET_KEY = 'cle_secrete_a_modifier_imperativement'

# ------------------------------------ Mode démo -----------------------------------------

MODE_DEMO = False

# ------------------------------------ Debug Mode ----------------------------------------

DEBUG = False

# -------------------------------------- URLS --------------------------------------------

URL_GESTION = "administrateur/"
URL_BUREAU = "utilisateur/"
URL_PORTAIL = ""
PORTAIL_ACTIF = True

# ------------------ Hosts : Saisissez les hosts autorisés (IP ou urls) ------------------

ALLOWED_HOSTS = []

# ------- Database : Modifier si besoin (en cas d'utilisation de MySQL par exemple) -------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# ------------------------------------ Sauvegardes --------------------------------------

# Pour plus d'infos, consulter https://django-dbbackup.readthedocs.io/en/master/

# ID de la clé GPG pour le chiffrement de la sauvegarde
# DBBACKUP_GPG_RECIPIENT = "XXXXXXXXX"

# Pour un stockage de la sauvegarde sur le disque dur (Renseigner ci-dessous un répertoire existant)
# DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
# DBBACKUP_STORAGE_OPTIONS = {"location": "C:/Users/XXXXXX/Desktop/sauvegardes/"}
# DBBACKUP_CONNECTORS = {"default": {"dump_suffix": "--hex-blob"}}

# Pour un stockage de la sauvegarde sur Dropbox (Renseigner ci-dessous le token de Dropbox)
# 1. Connectez-vous à Dropbox et accédez à Developper Apps : https://www.dropbox.com/developers/apps
# 2. Cliquez sur le bouton 'Create app' et saisissez un nom de votre choix. Ex : "Mes sauvegardes".
# 3. Une fois l'appli créée, cochez les permissions files.metadata et files.content.
# 4. Générez le token et copiez-le ci-dessous.
# DBBACKUP_STORAGE = "storages.backends.dropbox.DropBoxStorage"
# DBBACKUP_STORAGE_OPTIONS = {"oauth2_access_token": "Token Dropbox à coller ici"}

# ------------------------------- Stockage de documents ----------------------------------

# Indiquer le type de stockage souhaité pour chaque information :
# Pour un stockage sur le disque dur (par défaut) : django.core.files.storage.FileSystemStorage
# Pour un stockage sur Dropbox : storages.backends.dropbox.DropBoxStorage

# STORAGE_PROBLEME = "django.core.files.storage.FileSystemStorage"
# STORAGE_PIECE = "django.core.files.storage.FileSystemStorage"
# STORAGE_QUOTIENT = "django.core.files.storage.FileSystemStorage"
# STORAGE_ASSURANCE = "django.core.files.storage.FileSystemStorage"
# STORAGE_PHOTO = "django.core.files.storage.FileSystemStorage"

# Si l'un des champs ci-dessus utilise Dropbox, renseignez le token Dropbox ci-dessous :
# DROPBOX_OAUTH2_TOKEN = "XXXXXXXXXXXXXXX"


# ------------------------------------- Crontab ---------------------------------------

# Décommentez les lignes ci-dessous pour activer les tâches automatisées
# et modifiez si besoin les horaires de déclenchement et le path python :

# CRONTAB_PYTHON_EXECUTABLE = "/usr/bin/python3.9"
# CRONTAB_COMMAND_SUFFIX = '2>&1'
# CRONJOBS = [
#     # ("* * * * *", "noethysweb.cron.Test_cron", ">> " + os.path.join(BASE_DIR, "debug_cron.log"))
#     ("00 23 * * *", "noethysweb.cron.Sauvegarder_db", ">> " + os.path.join(BASE_DIR, "debug_cron.log")),
#     ("30 23 * * *", "noethysweb.cron.Sauvegarder_media", ">> " + os.path.join(BASE_DIR, "debug_cron.log")),
# ]

# ------------------------------------ Sécurité ----------------------------------------

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 15768000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_AGE = 60*60*12 # 12 heures
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
