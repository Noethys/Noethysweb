# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def GetVersion():
    """ Recherche du numéro de version """
    fichierVersion = open(os.path.join(BASE_DIR, "versions.txt"), "r", encoding="utf8", errors="ignore")
    txtVersion = fichierVersion.readlines()[0]
    fichierVersion.close()
    pos_debut_numVersion = txtVersion.find("n")
    pos_fin_numVersion = txtVersion.find("(")
    numVersion = txtVersion[pos_debut_numVersion+1:pos_fin_numVersion].strip()
    return numVersion

def GetVersionTuple(version=""):
    """ Renvoie un numéro de version au format tuple """
    return [int(caract) for caract in version.split(".")]
