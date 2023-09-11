# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, uuid, datetime, copy
logger = logging.getLogger(__name__)
from django.core.cache import cache
from django.conf import settings
from core.utils import utils_dates
from core.models import Organisateur


def Get_motscles_defaut(request=None):
    organisateur = cache.get('organisateur', None)
    if not organisateur:
        organisateur = cache.get_or_set('organisateur', Organisateur.objects.filter(pk=1).first())

    dict_valeurs = {
        "{ORGANISATEUR_NOM}": organisateur.nom,
        "{ORGANISATEUR_RUE}": organisateur.rue,
        "{ORGANISATEUR_CP}": organisateur.cp,
        "{ORGANISATEUR_VILLE}": organisateur.ville,
        "{ORGANISATEUR_TEL}": organisateur.tel,
        "{ORGANISATEUR_FAX}": organisateur.fax,
        "{ORGANISATEUR_MAIL}": organisateur.mail,
        "{ORGANISATEUR_SITE}": organisateur.site,
        "{ORGANISATEUR_AGREMENT}": organisateur.num_agrement,
        "{ORGANISATEUR_SIRET}": organisateur.num_siret,
        "{ORGANISATEUR_APE}": organisateur.code_ape,
        "{UTILISATEUR_NOM_COMPLET}": request.user.get_full_name() if request else "",
        "{UTILISATEUR_NOM}": request.user.last_name if request else "",
        "{UTILISATEUR_PRENOM}": request.user.first_name if request else "",
        "{DATE_LONGUE}": utils_dates.DateComplete(datetime.date.today()),
        "{DATE_COURTE}": utils_dates.ConvertDateToFR(datetime.date.today()),
    }
    return dict_valeurs


class Fusionner():
    def __init__(self, titre="", modele_document=None, valeurs={}, generation_auto=True, request=None):
        self.titre = titre
        self.valeurs = valeurs
        self.modele_document = modele_document
        self.request = request
        self.url_nouveau_fichier = None
        self.erreurs = []
        if generation_auto:
            self.Generation_document()

    def Generation_document(self):
        # Récupération du chemin du document word modèle
        chemin_modele_document = settings.BASE_DIR + self.modele_document.fichier.url

        # Création du répertoire et du nom du fichier
        nom_fichier = "%s.docx" % self.titre
        rep_temp = os.path.join("temp", str(uuid.uuid4()))
        rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
        if not os.path.isdir(rep_destination):
            os.makedirs(rep_destination)
        root_nouveau_fichier = os.path.join(rep_destination, nom_fichier)
        self.url_nouveau_fichier = os.path.join(settings.MEDIA_URL, rep_temp, nom_fichier)

        # Préparation des valeurs
        if not isinstance(self.valeurs, list):
            self.valeurs = [self.valeurs]
        for index, dict_valeurs in enumerate(self.valeurs):
            dict_valeurs = copy.deepcopy(dict_valeurs)
            dict_valeurs.update(Get_motscles_defaut(request=self.request))
            self.valeurs[index] = dict_valeurs

        # Fusion du document
        from mailmerge import MailMerge
        with MailMerge(chemin_modele_document, remove_empty_tables=False, auto_update_fields_on_open="no") as document:
            document.merge_templates(self.valeurs, separator="page_break")
            document.write(root_nouveau_fichier)

    def Get_nom_fichier(self):
        """ Renvoie le chemin du nouveau fichier """
        return self.url_nouveau_fichier

    def Get_erreurs_html(self):
        return ", ".join(self.erreurs)
