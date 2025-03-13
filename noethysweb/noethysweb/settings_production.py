#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

#########################################################################################
#              FICHIER DE CONFIGURATION A MODIFIER SELON LES BESOINS
#
# Valeurs à personnaliser impérativement avant une mise en ligne :
# SECRET_KEY, ALLOWED_HOSTS, URL_GESTION, DATABASES
#
#########################################################################################

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from noethysweb.noethysweb.settings import STATIC_ROOT
STATIC_ROOT = os.path.join(BASE_DIR,'staticfiles')

#########################################################################################
# CLE SECRETE : Saisissez une clé aléatoire complexe de votre choix (50 caract. minimum)
#########################################################################################

SECRET_KEY = 'gip_recia'

#########################################################################################
# MODE DEMO : Pour désactiver des fonctionnalités
#########################################################################################

MODE_DEMO = False

#########################################################################################
# MODE DEBUG : Conserver False en production impérativement
#########################################################################################

DEBUG = False

#########################################################################################
# URLS : à personnaliser selon les souhaits
# Il est fortement conseillé de définir une URL aléatoire pour le URL_GESTION
# Et de définir une URL un peu plus complexe pour le URL_BUREAU
#########################################################################################

URL_GESTION = "administrateur/"
URL_BUREAU = "utilisateur/"
URL_PORTAIL = ""
PORTAIL_ACTIF = True

#########################################################################################
# HOSTS : Saisissez les hosts autorisés (IP ou urls du serveur).
# Obligatoire pour fonctionner sur un serveur.
# Exemple : ALLOWED_HOSTS = ["127.0.0.1", "www.monsite.com"]
#########################################################################################

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

#########################################################################################
# BASE DE DONNEES : Modifier si besoin (en cas d'utilisation de MySQL par exemple)
# Le moteur par défaut SQLITE est à utiliser uniquement pour des tests en local.
# Exemple : https://docs.djangoproject.com/fr/4.0/ref/databases/#connection-management
#########################################################################################

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'noethysweb',
        'USER': 'noethysweb',
        'PASSWORD': 'noethysweb',
        'HOST': 'localhost',  # ou l'adresse IP de votre serveur MariaDB
        'PORT': '3306',       # le port par défaut de MariaDB
    }
}
#########################################################################################
# SAUVEGARDES : Permet de générer et envoyer des sauvegardes chiffrées des données
# vers un répertoire du serveur ou vers Dropbox.
# Pour plus d'infos, consulter https://django-dbbackup.readthedocs.io/en/master/
#########################################################################################

# ID de la clé GPG pour le chiffrement de la sauvegarde
DBBACKUP_GPG_RECIPIENT = "D7FC7207637A035E76C58D26C77F465B04290FAA"

# Pour un stockage de la sauvegarde sur le disque dur (Renseigner ci-dessous un répertoire existant)
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {"location": "/home/faouzia-takaya/Documents/sauvegardes/"}
DBBACKUP_CONNECTORS = {"default": {"dump_suffix": "--hex-blob"}}
DBBACKUP_CLEANUP_KEEP = 10
DBBACKUP_CLEANUP_KEEP_MEDIA = 10

# Pour un stockage de la sauvegarde sur Dropbox (Renseigner ci-dessous le token de Dropbox)
# 1. Connectez-vous à Dropbox et accédez à Developper Apps : https://www.dropbox.com/developers/apps
# 2. Cliquez sur le bouton 'Create app' et saisissez un nom de votre choix. Ex : "Mes sauvegardes".
# 3. Une fois l'appli créée, cochez les permissions files.metadata et files.content.
# 4. Générez le token et copiez-le ci-dessous.
# DBBACKUP_STORAGE = "storages.backends.dropbox.DropBoxStorage"
# DBBACKUP_STORAGE_OPTIONS = {"oauth2_access_token": "XXXX", "app_key": "XXXX", "app_secret": "XXXX", "oauth2_refresh_token": "XXXX"}

#########################################################################################
# STOCKAGE DE DOCUMENTS
# Indiquer le type de stockage souhaité pour chaque information :
# Pour un stockage sur le disque dur (par défaut) : django.core.files.storage.FileSystemStorage
# Pour un stockage sur Dropbox : storages.backends.dropbox.DropBoxStorage
#########################################################################################

STORAGE_PROBLEME = "django.core.files.storage.FileSystemStorage"
STORAGE_PIECE = "django.core.files.storage.FileSystemStorage"
STORAGE_QUOTIENT = "django.core.files.storage.FileSystemStorage"
STORAGE_ASSURANCE = "django.core.files.storage.FileSystemStorage"
STORAGE_PHOTO = "django.core.files.storage.FileSystemStorage"
STORAGE_PIECE_COLLABORATEUR = "django.core.files.storage.FileSystemStorage"

# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Si l'un des champs ci-dessus utilise Dropbox, renseignez le token Dropbox ci-dessous :
# DROPBOX_OAUTH2_TOKEN = "XXXXXXXXXXXXXXX"
# DROPBOX_OAUTH2_REFRESH_TOKEN = "XXXXXXXXXXXXXXX"
# DROPBOX_APP_KEY = "XXXXXXXXXXXXXXX"
# DROPBOX_APP_SECRET = "XXXXXXXXXXXXXXX"

#########################################################################################
# CRONTAB (tâches planifiées)
# Décommentez les lignes ci-dessous pour activer les tâches automatisées
# et modifiez si besoin les horaires de déclenchement et le path python :
#########################################################################################

CRONTAB_PYTHON_EXECUTABLE = "/usr/bin/python3.9"
CRONTAB_COMMAND_SUFFIX = '2>&1'
CRONJOBS = [
    ("* * * * *", "noethysweb.cron.Test_cron", ">> " + os.path.join(BASE_DIR, "debug_cron.log")) ,# Pour des tests
    ("00 23 * * *", "noethysweb.cron.Sauvegarder_db", ">> " + os.path.join(BASE_DIR, "debug_cron.log")), # Pour sauvegarder la base de données
    ("25 23 * * *", "noethysweb.cron.Vider_rep_temp", ">> " + os.path.join(BASE_DIR, "debug_cron.log")), # Pour purger le répertoire temp
    ("30 23 * * *", "noethysweb.cron.Sauvegarder_media", ">> " + os.path.join(BASE_DIR, "debug_cron.log")), # Pour sauvegarde le répertoire media
    ("45 23 * * *", "noethysweb.cron.Traiter_attentes", ">> " + os.path.join(BASE_DIR, "debug_cron.log")), # Pour traiter les réservations en attente
    ("50 23 * * *", "noethysweb.cron.Corriger_anomalies", ">> " + os.path.join(BASE_DIR, "debug_cron.log")), # Pour corriger les anomalies
    ("00 03 * * *", "noethysweb.cron.Generer_taches", ">> " + os.path.join(BASE_DIR, "debug_cron.log")), # Pour générer les tâches récurrentes
]

#########################################################################################
# SECURITE : Les paramètres par défaut conviendront généralement.
#########################################################################################

CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_SSL_REDIRECT = False
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 15768000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_AGE = 60*60*12 # 12 heures
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
