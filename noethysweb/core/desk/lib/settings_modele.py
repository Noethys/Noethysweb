#  Copyright (c) 2019-2024 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Secret Key
SECRET_KEY = "{SECRET_KEY}"

# Debug Mode
DEBUG = True
MODE_DEMO = False

# URLS
URL_GESTION = "{URL_GESTION}"
URL_BUREAU = "bureau/"

# Hosts
ALLOWED_HOSTS = []

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
