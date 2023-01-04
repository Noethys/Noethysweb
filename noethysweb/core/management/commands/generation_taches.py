# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génération des tâches récurrentes"

    def handle(self, *args, **kwargs):
        from core.utils import utils_generation_taches
        utils_generation_taches.Generer_taches()
