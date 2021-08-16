#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

#  Fichier de configuration à modifier selon les besoins

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Secret Key : Saisissez une clé aléatoire de votre choix
SECRET_KEY = 'cle_secrete_a_modifier_imperativement'

# Mode démo
MODE_DEMO = False

# Debug Mode
DEBUG = False

# URLS
URL_GESTION = "administrateur/"
URL_BUREAU = "utilisateur/"
URL_PORTAIL = ""
PORTAIL_ACTIF = True

# Hosts : Saisissez les hosts autorisés (IP ou urls)
ALLOWED_HOSTS = []

# Database : Modifier si besoin (en cas d'utilisation de MySQL par exemple)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Sécurité
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
