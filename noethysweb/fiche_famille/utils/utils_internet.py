# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, random
logger = logging.getLogger(__name__)
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
    return mdp

def ReinitTousMdp():
    for famille in Famille.objects.select_related("utilisateur").all():
        internet_mdp = utils_internet.CreationMDP()
        famille.internet_mdp = internet_mdp
        if not famille.utilisateur:
            utilisateur = Utilisateur(username=famille.internet_identifiant, categorie="famille", force_reset_password=True)
            utilisateur.save()
            utilisateur.set_password(internet_mdp)
            utilisateur.save()
            famille.utilisateur = utilisateur
        famille.save()
