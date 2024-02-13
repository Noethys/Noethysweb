# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from decimal import Decimal
from django.db.models import Q, Sum
from core.models import Facture, Ventilation, Prestation


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
    for facture in Facture.objects.filter(conditions_factures).exclude(etat="annulation"):
        solde_actuel = facture.total - dict_ventilations.get(facture.pk, Decimal(0))
        regle = dict_ventilations.get(facture.pk, Decimal(0))
        if solde_actuel != facture.solde_actuel or regle != facture.regle:
            facture.regle = regle
            facture.solde_actuel = facture.total - facture.regle
            facture.save()


def Maj_solde_actuel(liste_idprestation=[], liste_prestations=[]):
    """
    Met à jour les soldes actuels des factures associées aux prestations données
    IMPORTANT : Renseigner liste_idprestation OU liste_prestations
    """
    if liste_prestations:
        liste_idprestation = [prestation.ok for prestation in liste_prestations]
    factures = {prestation.facture: None for prestation in Prestation.objects.select_related("facture").filter(pk__in=liste_idprestation, facture__isnull=False)}
    for facture in factures.keys():
        facture.Maj_solde_actuel()


def Maj_total_factures(IDfamille=None, IDfacture=None):
    """ Vérifie les totaux mémorisés de toutes les factures OU des factures d'une famille uniquement """
    conditions = Q()
    if IDfamille:
        conditions &= Q(famille_id=IDfamille)
    if IDfacture:
        conditions &= Q(pk=IDfacture)
    factures = Facture.objects.filter(conditions).values("pk", "total", "regle", "solde", "solde_actuel").exclude(etat="annulation").annotate(total_calcul=Sum("prestation__montant"))
    for facture in factures:
        total_calcul = "%.02f" % (facture["total_calcul"] or 0)
        total = "%.02f" % (facture["total"] or 0)
        if total_calcul != total: # and facture["total_calcul"]
            facture = Facture.objects.get(pk=facture["pk"])
            facture.total = Decimal(total_calcul)
            facture.solde = facture.total - facture.regle
            facture.save()
            facture.Maj_solde_actuel()
