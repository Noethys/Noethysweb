# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from core.models import Rattachement, Lien


def Creation_auto_liens(famille=None):
    """ Création des liens en fonction du champ 'situation familiale' des enfants """
    """ Si famille == None : traitement de toutes les familles """
    conditions = Q(famille=famille) if famille else Q()

    # Mémorisation des familles
    dict_rattachements = {}
    for rattachement in Rattachement.objects.select_related("famille", "individu").filter(conditions):
        dict_rattachements.setdefault(rattachement.famille, {1: [], 2: [], 3: []})
        dict_rattachements[rattachement.famille][rattachement.categorie].append(rattachement.individu)

    for famille, dict_membres in dict_rattachements.items():
        # S'il y a des enfants dans cette famille
        if dict_membres[2]:

            # Création des liens parents/enfants
            for parent in dict_membres[1]:
                for enfant in dict_membres[2]:
                    Lien.objects.create(famille=famille, idtype_lien=1, individu_sujet=parent, individu_objet=enfant)
                    Lien.objects.create(famille=famille, idtype_lien=2, individu_sujet=enfant, individu_objet=parent)

            # Création des liens frères/soeurs
            for enfant1 in dict_membres[2]:
                for enfant2 in dict_membres[2]:
                    if enfant1 != enfant2:
                        Lien.objects.create(famille=famille, idtype_lien=3, individu_sujet=enfant1, individu_objet=enfant2)

            # Création des liens entre adultes (si situation familiale connue)
            if len(dict_membres[1]) > 1:
                idtype_lien = None
                for enfant in dict_membres[2]:
                    if enfant.situation_familiale == 2: idtype_lien = 10
                    if enfant.situation_familiale == 3: idtype_lien = 16
                    if enfant.situation_familiale == 4: idtype_lien = 12
                    if enfant.situation_familiale == 5: idtype_lien = 11
                    if enfant.situation_familiale == 6: idtype_lien = 17
                    if enfant.situation_familiale == 7: idtype_lien = 15
                if idtype_lien:
                    for parent1 in dict_membres[1]:
                        for parent2 in dict_membres[1]:
                            if parent1 != parent2:
                                Lien.objects.create(famille=famille, idtype_lien=idtype_lien, individu_sujet=parent1, individu_objet=parent2)
