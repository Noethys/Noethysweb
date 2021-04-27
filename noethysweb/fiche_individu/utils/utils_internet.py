# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
import random


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
