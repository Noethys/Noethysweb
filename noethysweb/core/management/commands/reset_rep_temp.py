# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, shutil, datetime
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Vide le repertoire temporaire"

    def handle(self, *args, **kwargs):
        rep = os.path.join(settings.MEDIA_ROOT, "temp")
        for nom_fichier in os.listdir(rep):
            nom_fichier_complet = os.path.join(rep, nom_fichier)
            try:
                if os.path.isdir(nom_fichier_complet):
                    shutil.rmtree(nom_fichier_complet)
                else:
                    os.remove(nom_fichier_complet)
            except Exception as err:
                pass
        self.stdout.write(self.style.SUCCESS("[%s] Répertoire temp vidé." % datetime.datetime.now()))
