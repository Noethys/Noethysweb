#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# URLS
URL_GESTION = "administrateur/"
URL_BUREAU = "utilisateur/"
URL_PORTAIL = ""
PORTAIL_ACTIF = True

MODE_DEMO = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'fdjsqfq543Z4645RFsdfSs564Z5-z(YZdqswFSDf'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1"]

X_FRAME_OPTIONS = 'SAMEORIGIN'
LOGIN_REDIRECT_URL = "accueil"
# LOGIN_URL = "connexion"
# LOGOUT_REDIRECT_URL = "connexion"

# AXES
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 24
AXES_LOCKOUT_URL = '/locked'

# CAPTCHA
CAPTCHA_FONT_SIZE = 30
CAPTCHA_IMAGE_SIZE = (90, 40)
CAPTCHA_LETTER_ROTATION = (-55, 55)
CAPTCHA_CHALLENGE_FUNCT = "core.utils.utils_captcha.random_digit_challenge"

# UPLOAD PHOTOS
UPLOAD_FORM_PARALLEL_UPLOAD = False
UPLOAD_FORM_MAX_FILE_SIZE_MB = 10
UPLOAD_FORM_ALLOWED_FILE_TYPES = ".jpg .jpeg .png .gif .bmp .tif .tiff .pic .doc .docx .odt .dot .xls .xlsx .pdf .dwg .dxf .txt .mp4"
MY_UPLOAD_FORM_ACCEPT = "image/*"
MY_UPLOAD_FORM_MAX_IMAGE_SIZE = 1920

# DIVERS
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
AUTH_USER_MODEL = 'core.Utilisateur'
DUREE_VALIDITE_MDP = 60*60*48
CORRECTEUR_JOURS_RETROACTION = 30

# CONFIGURATION ACCUEIL
CONFIG_ACCUEIL_DEFAUT = [
    [[8, "notes"], [4, "messages"]],
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    # 'django.contrib.auth',
    'core.apps.CustomAuth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps
    'core.apps.Core',
    'parametrage.apps.Parametrage',
    'fiche_famille.apps.FicheFamille',
    'fiche_individu.apps.FicheIndividu',
    'individus.apps.Individus',
    'locations.apps.Locations',
    'cotisations.apps.Cotisations',
    'consommations.apps.Consommations',
    'facturation.apps.Facturation',
    'outils.apps.Outils',
    'reglements.apps.Reglements',
    'comptabilite.apps.Comptabilite',
    'collaborateurs.apps.Collaborateurs',
    'aide.apps.Aide',
    'portail.apps.Portail',

    # Autres librairies
    'datatableview',
    'crispy_forms',
    'debug_toolbar',
    'django_select2',
    'django_summernote',
    'anymail',
    'formtools',
    'axes',
    'captcha',
    'django_extensions',
    'upload_form',
    'dbbackup',
    'django_crontab',
    'django_cleanup.apps.CleanupConfig',
]

# import crispy_forms
# if int(crispy_forms.__version__.split(".")[0]) >= 2:
#     INSTALLED_APPS.append("crispy_bootstrap4")

# Liste des plugins
PLUGINS = []

# Ajouté pour permettre l'affichage de la debugtoolbar
INTERNAL_IPS = [
    '127.0.0.1',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',
    'axes.middleware.AxesMiddleware',
    'noethysweb.middleware.CustomMiddleware',
]

ROOT_URLCONF = 'noethysweb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'noethysweb.wsgi.application'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = False
DATE_FORMAT = "d/m/Y"
TELEPHONE_FORMAT_FR = True
LANGUAGES = (
    ("en", "English"),
    ("fr", "Français"),
)
LOCALE_PATHS = (
    os.path.join(BASE_DIR, "locale"),
)

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Summernote
SUMMERNOTE_THEME = 'bs4'

# Django-resize
DJANGORESIZED_DEFAULT_SIZE = [500, 500]
DJANGORESIZED_DEFAULT_QUALITY = 95
DJANGORESIZED_DEFAULT_KEEP_META = True
DJANGORESIZED_DEFAULT_FORMAT_EXTENSIONS = {'JPEG': ".jpg", 'PNG': ".png"}
DJANGORESIZED_DEFAULT_NORMALIZE_ROTATION = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'complet': {
            'format': '[{levelname} {asctime} {module}]  {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'complet',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'complet',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'backupCount': 10,
            'maxBytes': 20971520, # 20*1024*1024 bytes (20MB)
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'mail_admins'],
        'level': 'DEBUG',
    },
}

CSP_DEFAULT_SRC = (
    "'self'",
    "https://api-adresse.data.gouv.fr/",
)

CSP_IMG_SRC = (
    "'self'",
    "data:",
    "https://*.openstreetmap.org",
    "https://api-adresse.data.gouv.fr/",
)

CSP_FONT_SRC = (
    "'self'",
    "data:",
    "https://fonts.gstatic.com",
)

CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "https://fonts.googleapis.com",
    "https://cdnjs.cloudflare.com",
)

CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "https://ajax.googleapis.com",
    "https://cdnjs.cloudflare.com",
)

CSP_FRAME_SRC = (
    "'self'",
    "https://www.youtube.com",
)

CSP_FRAME_ANCESTORS = (
    "'self'",
)

# Chargement des settings de production
try:
    from .settings_production import *
except:
    print("Settings en production non trouvés : Utilisation des settings par défaut.")

# Intégration des plugins
for nom_plugin in PLUGINS:
    INSTALLED_APPS.append("plugins.%s.apps.%s" % (nom_plugin, nom_plugin))
