# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test de traitement des reservations en attente"

    def handle(self, *args, **kwargs):
        from consommations.utils import utils_traitement_attentes
        utils_traitement_attentes.Traiter_attentes(request=None, test=True)
