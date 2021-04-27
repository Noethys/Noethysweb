#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.apps import AppConfig


class Core(AppConfig):
    name = 'core'
    # Pour personnaliser l'affichage dans admin
    verbose_name = "Utilisateurs"


class CustomAuth(AppConfig):
    name = 'django.contrib.auth'
    # Pour personnaliser l'affichage dans admin
    verbose_name = "Groupes d'utilisateurs"