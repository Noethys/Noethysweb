# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
from django.db.models import Sum, Q
from core.models import Prestation, Reglement, Facture


def Get_solde_famille(idfamille=None, date_situation=None, factures=False):
    if factures:
        # Renvoie le solde total des factures impayées de la famille
        total_soldes_factures = Facture.objects.values('famille_id').filter(famille_id=idfamille, etat=None).aggregate(total=Sum("solde_actuel"))
        return total_soldes_factures["total"] if total_soldes_factures["total"] else decimal.Decimal(0)
    else:
        # Renvoie l'impayé global de la famille
        conditions_prestations = Q(famille_id=idfamille)
        if date_situation:
            conditions_prestations &= Q(date__lt=date_situation)
        total_prestations = Prestation.objects.values('famille_id').filter(conditions_prestations).aggregate(total=Sum("montant"))
        total_reglements = Reglement.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
        total_du = total_prestations["total"] if total_prestations["total"] else decimal.Decimal(0)
        total_regle = total_reglements["total"] if total_reglements["total"] else decimal.Decimal(0)
        return total_du - total_regle
