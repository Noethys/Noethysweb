# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from decimal import Decimal
from django.db.models import Q, Sum
from core.models import Prestation, Reglement, Ventilation
from facturation.utils import utils_factures


def xDecimal(valeur=0.0):
    """ Arrondit un Decimal """
    if not isinstance(valeur, Decimal):
        valeur = Decimal(u"%.2f" % valeur)
    valeur = valeur.quantize(Decimal('0.01'))
    return valeur


def GetAnomaliesVentilation():
    """ Retourne les anomalies de ventilation """
    reglements = Reglement.objects.values('famille').filter().annotate(total=Sum("montant"))
    prestations = {item["famille"]: item["total"] for item in Prestation.objects.values('famille').filter().annotate(total=Sum("montant"))}
    ventilations = {item["famille"]: item["total"] for item in Ventilation.objects.values('famille').filter().annotate(total=Sum("montant"))}

    dict_anomalies = {}
    for item in reglements:
        IDfamille = item["famille"]
        total_reglements = xDecimal(item["total"])
        total_prestations = xDecimal(prestations.get(IDfamille, Decimal(0)))
        total_ventilations = xDecimal(ventilations.get(IDfamille, Decimal(0)))
        solde = total_reglements - total_prestations
        total_a_ventiler = min(total_reglements, total_prestations)
        reste_a_ventiler = total_a_ventiler - total_ventilations

        if reste_a_ventiler > Decimal(0.0):
            dict_anomalies[IDfamille] = {
                "total_reglements": total_reglements, "total_prestations": total_prestations, "total_ventilations": total_ventilations,
                "solde": solde, "total_a_ventiler": total_a_ventiler, "reste_a_ventiler": reste_a_ventiler
            }
    return dict_anomalies


def Ventilation_auto(IDfamille=None):
    """ Effectue la ventilation automatique """
    condition_famille = Q(famille_id=IDfamille)

    # Récupère la ventilation
    ventilations = Ventilation.objects.filter(condition_famille)

    dictVentilations = {}
    dictVentilationsReglement = {}
    dictVentilationsPrestation = {}
    for ventilation in ventilations:
        dictVentilations[ventilation.pk] = ventilation

        if ventilation.reglement_id not in dictVentilationsReglement:
            dictVentilationsReglement[ventilation.reglement_id] = []
        dictVentilationsReglement[ventilation.reglement_id].append(ventilation.pk)

        if ventilation.prestation_id not in dictVentilationsPrestation:
            dictVentilationsPrestation[ventilation.prestation_id] = []
        dictVentilationsPrestation[ventilation.prestation_id].append(ventilation.pk)

    # Récupère les prestations
    prestations = Prestation.objects.filter(condition_famille)

    # Vérifie qu'il n'y a pas de prestations négatives
    for prestation in prestations:

        montantVentilation = Decimal(0.0)
        for IDventilation in dictVentilationsPrestation.get(prestation.pk, []):
            montantVentilation += dictVentilations[IDventilation].montant

        ResteAVentiler = prestation.montant - montantVentilation
        if ResteAVentiler < Decimal(0.0):
            print("La ventilation automatique n'est pas compatible avec les prestations comportant un montant négatif ! Vous devez donc effectuer une ventilation manuelle.")
            return False

    # Récupère les règlements
    reglements = Reglement.objects.filter(condition_famille)

    # Vérification de la ventilation de chaque règlement
    for reglement in reglements:

        # Recherche s'il reste du crédit à ventiler dans ce règlement
        montantVentilation = Decimal(0.0)
        for IDventilation in dictVentilationsReglement.get(reglement.pk, []):
            montantVentilation += dictVentilations[IDventilation].montant

        credit = reglement.montant - montantVentilation

        if credit > Decimal(0.0):

            # Recherche s'il reste des prestations à ventiler pour cette famille
            for prestation in prestations:

                montantVentilation = Decimal(0.0)
                for IDventilation in dictVentilationsPrestation.get(prestation.pk, []):
                    montantVentilation += dictVentilations[IDventilation].montant

                ResteAVentiler = prestation.montant - montantVentilation
                if ResteAVentiler > Decimal(0.0):

                    # Calcul du montant qui peut être ventilé
                    montant = ResteAVentiler
                    if credit < montant:
                        montant = credit

                    if montant > Decimal(0.0):

                        # Modification d'une ventilation existante
                        ventilationTrouvee = False
                        for IDventilation in dictVentilationsPrestation.get(prestation.pk, []):
                            if dictVentilations[IDventilation].reglement == reglement:
                                nouveauMontant = montant + montantVentilation

                                # Mémorisation du nouveau montant
                                dictVentilations[IDventilation].montant = nouveauMontant
                                dictVentilations[IDventilation].save()
                                ResteAVentiler -= montant
                                credit -= montant
                                ventilationTrouvee = True

                        # Création d'une ventilation
                        if not ventilationTrouvee:
                            ventilation = Ventilation.objects.create(famille_id=IDfamille, reglement=reglement, prestation=prestation, montant=montant)

                            # Mémorisation de la nouvelle ventilation
                            dictVentilations[ventilation.pk] = ventilation
                            if reglement.pk not in dictVentilationsReglement:
                                dictVentilationsReglement[reglement.pk] = []
                            dictVentilationsReglement[reglement.pk].append(ventilation.pk)
                            if prestation.pk not in dictVentilationsPrestation:
                                dictVentilationsPrestation[prestation.pk] = []
                            dictVentilationsPrestation[prestation.pk].append(ventilation.pk)
                            ResteAVentiler -= montant
                            credit -= montant

    # Ajuster les soldes des factures de la famille
    utils_factures.Maj_solde_actuel_factures(IDfamille=IDfamille)

    return True
