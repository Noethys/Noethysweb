# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Update de l'application Noethysweb"

    def handle(self, *args, **kwargs):
        from outils.utils import utils_update
        resultat = utils_update.Update()
        print("resultat=", resultat)
