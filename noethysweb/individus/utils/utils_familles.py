# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
from django.db.models import Sum
from core.models import Prestation, Reglement


def Get_solde_famille(idfamille=None):
    total_prestations = Prestation.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
    total_reglements = Reglement.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
    total_du = total_prestations["total"] if total_prestations["total"] else decimal.Decimal(0)
    total_regle = total_reglements["total"] if total_reglements["total"] else decimal.Decimal(0)
    return total_du - total_regle
