# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, zipfile, shutil, json, time, uuid
logger = logging.getLogger(__name__)
from django.core.management import call_command
from django.conf import settings
from django.core.files.base import ContentFile
from dbbackup.storage import get_storage
from core.utils import utils_fichiers


class Zip:
    def __init__(self, nom_zip="", rep_base=""):
        self.zip_file = zipfile.ZipFile(nom_zip, "w", zipfile.ZIP_DEFLATED)
        self.rep_base = rep_base

    def Ajouter(self, nom_fichier, arcname=None):
        chemin_fichier = os.path.join(self.rep_base, nom_fichier)
        if os.path.isfile(chemin_fichier):
            self.Ecrire(chemin_fichier, arcname=arcname)
        else:
            self.Ajouter_repertoire(chemin_fichier)

    def Fermer(self):
        self.zip_file.close()

    def Ecrire(self, nom_fichier, arcname=None):
        if not arcname:
            arcname = nom_fichier.replace(self.rep_base, "")
        self.zip_file.write(nom_fichier, arcname)

    def Ajouter_repertoire(self, folder):
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                self.Ecrire(full_path)
            elif os.path.isdir(full_path):
                self.Ajouter_repertoire(full_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.Fermer()


class Desk:
    nom_fichier = "noethyswebdesk.7z"
    repertoire = "desk"
    rep_destination = None

    def Generate_rep_temp(self):
        # Créé le répertoire temp s'il n'existe pas
        rep_temp = utils_fichiers.GetTempRep()

        # Création du répertoire de travail
        rep_destination = settings.MEDIA_ROOT + "/temp/" + str(uuid.uuid4())
        if not os.path.isdir(rep_destination):
            os.makedirs(rep_destination)
        self.rep_destination = rep_destination

    def Nettoyer_rep_temp(self):
        try:
            shutil.rmtree(self.rep_destination)
        except:
            pass

    def Get_chemin(self, nom_fichier=""):
        return os.path.join(self.rep_destination, nom_fichier)

    def Get_chemin_fichier_7z(self):
        return os.path.join(self.rep_destination, self.nom_fichier)

    def Generer(self, mdp=None):
        """ Génère un fichier desk au format 7z """
        logger.debug("Génération du fichier desk...")
        self.Generate_rep_temp()

        # Vide le répertoire temp
        logger.debug("Vidage des fichiers temporaires...")
        self.Nettoyer_fichiers_temporaires()

        # Création du zip data
        logger.debug("Génération du zip data...")
        call_command("dumpdatautf8", format="json", indent=4, output=self.Get_chemin("data.json"), exclude=["core.Historique", "contenttypes"])
        with Zip(self.Get_chemin("data.zip"), settings.MEDIA_ROOT) as zip:
            zip.Ajouter(self.Get_chemin("data.json"), arcname="data.json")
        logger.debug("Génération du zip data terminé.")

        # Création du zip media
        logger.debug("Génération du zip media...")
        liste_repertoires = os.listdir(settings.MEDIA_ROOT)
        liste_exclusions = ("django-summernote", "photos", "pieces_jointes", "temp")
        with Zip(self.Get_chemin("media.zip"), settings.MEDIA_ROOT) as zip:
            for nom_rep in liste_repertoires:
                if nom_rep not in liste_exclusions:
                    zip.Ajouter(nom_rep)
        logger.debug("Génération du zip media terminé.")

        # Création du fichier des préférences
        logger.debug("Génération du fichier des préférences...")
        with open(self.Get_chemin("preferences.json"), "w") as fichier:
            data = {"URL_GESTION": settings.URL_GESTION}
            json.dump(data, fichier)
        logger.debug("Génération du fichier des préférences terminé.")

        # Création du 7z global
        logger.debug("Génération du 7zip...")
        import py7zr
        with py7zr.SevenZipFile(self.Get_chemin_fichier_7z(), "w", password=mdp or settings.SECRET_EXPORT_DESK) as archive:
            archive.write(self.Get_chemin("data.zip"), arcname="data.zip")
            archive.write(self.Get_chemin("media.zip"), arcname="media.zip")
            archive.write(self.Get_chemin("preferences.json"), arcname="preferences.json")
            archive.write(os.path.join(settings.BASE_DIR, "core/desk/run.py"), arcname="run.py")
            archive.write(os.path.join(settings.BASE_DIR, "core/desk/lisezmoi.txt"), arcname="lisezmoi.txt")
            archive.write(os.path.join(settings.BASE_DIR, "core/desk/lib/settings_modele.py"), arcname="lib/settings_modele.py")
            archive.write(os.path.join(settings.BASE_DIR, "core/desk/lib/requirements.txt"), arcname="lib/requirements.txt")
        logger.debug("Génération du 7zip terminé.")

        # Nettoyage
        time.sleep(2)
        logger.debug("Nettoyage des fichiers temporaires...")
        self.Nettoyer_fichiers_temporaires()

        logger.debug("Génération du fichier desk terminé.")

    def Nettoyer_fichiers_temporaires(self):
        for nom_fichier in ("data.json", "data.zip", "media.zip", "preferences.json"):
            nom_fichier = self.Get_chemin(nom_fichier)
            if os.path.isfile(nom_fichier):
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
        logger.debug("Lecture du fichier à envoyer vers le storage...")
        with open(self.Get_chemin_fichier_7z(), "rb") as f:
            contenu_fichier = f.read()

        # Envoi du fichier vers le storage
        logger.debug("Envoi du fichier vers le storage...")
        storage.storage.save(name=self.nom_fichier, content=ContentFile(contenu_fichier, name=self.nom_fichier))
        logger.debug("Envoi du fichier vers le storage terminé.")

    def Nettoyer_storage(self):
        """ Supprime le fichier desk sur le storage """
        try:
            storage = self.Get_storage()
            storage.storage.delete(name=self.nom_fichier)
        except:
            pass
