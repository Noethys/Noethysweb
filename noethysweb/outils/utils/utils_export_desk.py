# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, zipfile, shutil, json, time
logger = logging.getLogger(__name__)
from django.core.management import call_command
from django.conf import settings
from django.core.files.base import ContentFile
from dbbackup.storage import get_storage
from core.utils import utils_fichiers


class Desk:
    nom_fichier = "noethyswebdesk.7z"
    repertoire = "desk"

    def Get_rep_temp(self):
        # Créé le répertoire temp s'il n'existe pas
        rep_temp = utils_fichiers.GetTempRep()

        # Création du répertoire de travail
        rep_destination = settings.MEDIA_ROOT + "/temp/desk"
        if not os.path.isdir(rep_destination):
            os.makedirs(rep_destination)
        return rep_destination

    def Nettoyer_rep_temp(self):
        try:
            shutil.rmtree(self.Get_rep_temp())
        except:
            pass

    def Get_chemin_fichier_7z(self):
        rep_destination = self.Get_rep_temp()
        return os.path.join(rep_destination, self.nom_fichier)

    def Generer(self, mdp=None):
        """ Génère un fichier desk au format 7z """
        # Vide le répertoire temp
        call_command("reset_rep_temp")

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

        # Création du 7z global
        import py7zr
        with py7zr.SevenZipFile(self.Get_chemin_fichier_7z(), "w", password=mdp or settings.SECRET_EXPORT_DESK) as archive:
            archive.write("data.zip")
            archive.write("media.zip")
            archive.write("preferences.json")
            archive.write("core/desk/run.py", arcname="run.py")
            archive.write("core/desk/lisezmoi.txt", arcname="lisezmoi.txt")
            archive.write("core/desk/lib/settings_modele.py", arcname="lib/settings_modele.py")
            archive.write("core/desk/lib/requirements.txt", arcname="lib/requirements.txt")

        # Nettoyage
        time.sleep(2)
        for nom_fichier in ("data.json", "data.zip", "media.zip", "preferences.json"):
            os.remove(nom_fichier)

    def Get_storage(self):
        """ Ouverture du storage """
        options = settings.DBBACKUP_STORAGE_OPTIONS
        options["root_path"] += "/" + self.repertoire
        return get_storage(options=options)

    def Envoyer_storage(self):
        """ Envoi du fichier desk sur le storage """
        storage = self.Get_storage()

        # Lecture du contenu du fichier
        with open(self.Get_chemin_fichier_7z(), "rb") as f:
            contenu_fichier = f.read()

        # Envoi du fichier vers le storage
        storage.storage.save(name=self.nom_fichier, content=ContentFile(contenu_fichier, name=self.nom_fichier))

    def Nettoyer_storage(self):
        """ Supprime le fichier desk sur le storage """
        try:
            storage = self.Get_storage()
            storage.storage.delete(name=self.nom_fichier)
        except:
            pass
