# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, random, datetime
logger = logging.getLogger(__name__)
from django.conf import settings
from core.models import Famille, Utilisateur
from fiche_famille.utils import utils_internet


def CreationIdentifiant(IDfamille=None, IDutilisateur=None, nbreCaract=8):
    """ Création d'un identifiant aléatoire """
    numTmp = ""
    for x in range(0, nbreCaract-4):
        numTmp += random.choice("123456789")
    identifiant = numTmp + "0" * 5
    if IDfamille:
        identifiant = u"F%d" % (int(identifiant) + IDfamille)
    if IDutilisateur:
        identifiant = u"U%d" % (int(identifiant) + IDutilisateur)
    return identifiant

def CreationMDP(nbreCaract=10):
    """ Création d'un mot de passe aléatoire """
    mdp = "".join([random.choice("bcdfghjkmnprstvwxzBCDFGHJKLMNPRSTVWXZ123456789") for x in range(0, nbreCaract)])
    date_expiration = CreationDateExpirationMDP()
    return mdp, date_expiration

def CreationDateExpirationMDP():
    """ Génération de la date d'expiration d'un mdp """
    return datetime.datetime.now() + datetime.timedelta(seconds=settings.DUREE_VALIDITE_MDP) if settings.DUREE_VALIDITE_MDP else None

def ReinitTousMdp():
    for famille in Famille.objects.select_related("utilisateur").all():
        internet_mdp, date_expiration_mdp = utils_internet.CreationMDP()
        famille.internet_mdp = internet_mdp
        if not famille.utilisateur:
            utilisateur = Utilisateur(username=famille.internet_identifiant, categorie="famille", force_reset_password=True, date_expiration_mdp=date_expiration_mdp)
            utilisateur.save()
            utilisateur.set_password(internet_mdp)
            utilisateur.save()
            famille.utilisateur = utilisateur
        else:
            famille.utilisateur.set_password(internet_mdp)
            famille.utilisateur.force_reset_password = True
            famille.utilisateur.date_expiration_mdp = date_expiration_mdp
            famille.utilisateur.save()
        famille.save()

def Purge_mdp_expires():
    """ Efface tous les mdp expirés """
    utilisateurs = Utilisateur.objects.select_related("famille").filter(categorie="famille", date_expiration_mdp__lte=datetime.datetime.now() - datetime.timedelta(days=3))
    for utilisateur in utilisateurs:
        logger.debug("Purge du mot de passe expiré de %s." % utilisateur.username)
        utilisateur.set_password(None)
        utilisateur.save()
        utilisateur.famille.internet_mdp = None
        utilisateur.famille.save()

def Fix_dates_expiration_mdp():
    """ Applique une date d'expiration aux mots de passe existants """
    for famille in Famille.objects.select_related("utilisateur").filter(utilisateur__date_expiration_mdp__isnull=True):
        if "*****" not in famille.internet_mdp:
            logger.debug("Application d'une date d'expiration MDP pour %s" % famille.utilisateur.username)
            famille.utilisateur.date_expiration_mdp = CreationDateExpirationMDP()
            famille.utilisateur.save()
