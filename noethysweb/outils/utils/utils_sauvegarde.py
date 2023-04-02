# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
import os, zipfile, shutil, re, io, traceback
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError
from django.core.serializers.base import DeserializationError
from django.db import IntegrityError
from django.core.management import call_command
from core.utils import utils_cryptage_fichier, utils_fichiers
from fiche_famille.utils import utils_internet


def Nettoyer(rep_destination):
    try:
        shutil.rmtree(rep_destination)
    except:
        pass

def Restauration(form=None, nom_fichier=None, mdp=None, conserve_mdp_internet=False):
    # Créé le répertoire temp s'il n'existe pas
    rep_temp = utils_fichiers.GetTempRep()

    # Création du répertoire de travail
    rep_destination = settings.MEDIA_ROOT + "/temp/restauration"
    if not os.path.isdir(rep_destination):
        os.makedirs(rep_destination)

    # Enregistre le fichier dans le répertoire de travail
    fichier_destination = os.path.join(rep_destination, "crypte.nweb")

    # Importation depuis le form
    if form:
        with open(fichier_destination, 'wb') as destination:
            for chunk in form.cleaned_data.get("fichier").chunks():
                destination.write(chunk)

    # Importation depuis le nom de fichier donné
    if nom_fichier:
        shutil.copy(nom_fichier, fichier_destination)

    # Décryptage de la sauvegarde
    fichier_decrypte = os.path.join(rep_destination, "decrypte.nweb")
    if form:
        mdp = form.cleaned_data["mdp"]
    if mdp:
        utils_cryptage_fichier.DecrypterFichier(fichier_destination, fichier_decrypte, mdp)
    else:
        shutil.copy(fichier_destination, fichier_decrypte)

    # Vérifie que le fichier décrypté est bien un zip
    if not zipfile.is_zipfile(fichier_decrypte):
        Nettoyer(rep_destination)
        return "Une erreur a été rencontrée durant le décryptage. Vérifiez votre mot de passe."

    # Dézippe le fichier zip
    with zipfile.ZipFile(fichier_decrypte, 'r') as zip:
        zip.extractall(path=rep_destination)

    # Installe le fichier core.json
    try:
        resultat = Load_fixtures(nom_fichier=os.path.join(rep_destination, "core.json"))
        logger.debug("resultat de la restauration : %s" % resultat)
    except (IntegrityError, ObjectDoesNotExist, DeserializationError, CommandError) as e:
        logger.error("Une erreur est survenue durant la restauration: %s." % str(e))
        print(traceback.print_exc())
        # Nettoyer(rep_destination)
        return "Une erreur est survenue durant la restauration: %s." % str(e)

    # Déplace les répertoires media
    from distutils.dir_util import copy_tree
    rep_tmp_media = os.path.join(rep_destination, "media")
    if os.path.isdir(rep_tmp_media):
        for rep in os.listdir(rep_tmp_media):
            copy_tree(os.path.join(rep_tmp_media, rep), os.path.join(settings.MEDIA_ROOT, rep))

    # Nettoyage du répertoire de travail
    Nettoyer(rep_destination)

    # MAJ des infos
    from core.utils import utils_db
    utils_db.Maj_infos()

    # RAZ des mots de passe internet
    if not conserve_mdp_internet:
        utils_internet.ReinitTousMdp()

    return None


def Load_fixtures(nom_fichier=""):
    # Fermeture de toutes les connexions à la base
    from django import db
    db.connections.close_all()

    # Restauration
    stream = io.StringIO()
    error_stream = io.StringIO()
    call_command('loaddata', nom_fichier, **{
        # 'stdout': stdout,
        # 'stderr': stdout,
        # 'ignore': True,
        # 'database': DEFAULT_DB_ALIAS,
        'verbosity': 3})
    stream.seek(0)
    result = stream.read()
    return True #int(re.match(r'Installed\s([0-9]+)\s.*', result).groups()[0])
