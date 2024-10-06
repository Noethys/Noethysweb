# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Export vers Noethysweb Desk"

    def handle(self, *args, **kwargs):
        import os, zipfile, shutil, json
        from django.conf import settings

        # Création du zip data
        call_command("dumpdatautf8", format="json", indent=4, output="data.json", exclude=["core.Historique", "contenttypes"])
        with zipfile.ZipFile("data.zip", "w", zipfile.ZIP_DEFLATED) as myzip:
            myzip.write("data.json")

        # Création du zip media
        shutil.make_archive(settings.MEDIA_ROOT, format="zip", root_dir=settings.MEDIA_ROOT)

        # Création du fichier des préférences
        with open("preferences.json", "w") as fichier:
            data = {"URL_GESTION": settings.URL_GESTION}
            json.dump(data, fichier)

        # Création du zip global
        with zipfile.ZipFile("noethyswebdesk.zip", "w", zipfile.ZIP_DEFLATED) as myzip:
            myzip.write("data.zip")
            myzip.write("media.zip")
            myzip.write("preferences.json")
            myzip.write("core/desk/run.py", arcname="run.py")
            myzip.write("core/desk/lisezmoi.txt", arcname="lisezmoi.txt")
            myzip.write("core/desk/lib/settings_modele.py", arcname="lib/settings_modele.py")
            myzip.write("core/desk/lib/requirements.txt", arcname="lib/requirements.txt")

        # Nettoyage
        for nom_fichier in ("data.json", "data.zip", "media.zip", "preferences.json"):
            os.remove(nom_fichier)

        self.stdout.write(self.style.SUCCESS("Export terminé"))
