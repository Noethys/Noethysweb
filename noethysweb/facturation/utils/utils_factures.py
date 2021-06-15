# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Facture, Ventilation
from django.db.models import Q, Sum
from decimal import Decimal


def Maj_solde_actuel_factures(IDfamille=None):
    """ Met à jour les soldes actuels de toutes les factures OU des factures d'une famille uniquement """
    # Importation des ventilations
    conditions_ventilations = Q(prestation__facture__isnull=False)
    if IDfamille:
        conditions_ventilations &= Q(famille_id=IDfamille)
    ventilations = Ventilation.objects.values('prestation__facture').filter(conditions_ventilations).annotate(total=Sum("montant"))
    dict_ventilations = {ventilation['prestation__facture']: ventilation['total'] for ventilation in ventilations}
    # Importation des factures
    conditions_factures = Q(famille_id=IDfamille) if IDfamille else Q()
    for facture in Facture.objects.filter(conditions_factures):
        solde_actuel = facture.total - dict_ventilations.get(facture.pk, Decimal(0))
        if solde_actuel != facture.solde_actuel:
            facture.solde_actuel = solde_actuel
            facture.save()

