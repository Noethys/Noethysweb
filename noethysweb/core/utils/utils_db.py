# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import connection



def bulk_delete(listeID=[], nom_table="ouvertures", nom_id="IDouverture"):
    """ Pour une suppression rapide """
    if listeID:
        if len(listeID) == 1:
            condition = "(%d)" % listeID[0]
        else:
            condition = str(tuple(listeID))
        cursor = connection.cursor()
        cursor.execute("DELETE FROM %s WHERE %s IN %s" % (nom_table, nom_id, condition))


def Maj_infos():
    """ Met à jour des infos dans la DB """
    from individus.utils import utils_individus

    # MAJ des noms et des adresses des familles
    utils_individus.Maj_infos_toutes_familles()

    # Met à jour les adresses de tous les individus
    utils_individus.Maj_infos_tous_individus()