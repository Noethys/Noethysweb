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


def GetAnomaliesVentilation(idfamille=None):
    """ Retourne les anomalies de ventilation """
    condition = Q()
    if idfamille:
        condition = Q(famille_id=idfamille)
    reglements = Reglement.objects.values('famille').filter(condition).annotate(total=Sum("montant"))
    prestations = {item["famille"]: item["total"] for item in Prestation.objects.values('famille').filter(condition).annotate(total=Sum("montant"))}
    ventilations = {item["famille"]: item["total"] for item in Ventilation.objects.values('famille').filter(condition).annotate(total=Sum("montant"))}

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


def Calculer_ventilation_auto(IDfamille=None, enregistrer=False):
    """ Calcule la ventilation automatique d'une famille.
    Si enregistrer=False, c'est une simple simulation : rien n'est écrit dans la base.
    Retourne un dict : possible (bool), affectations [(reglement, prestation, montant)], total, nbre_creations """
    resultat = {"possible": True, "affectations": [], "total": Decimal(0), "nbre_creations": 0}
    condition_famille = Q(famille_id=IDfamille)

    # Récupère la ventilation
    dictVentilations = {}
    dictVentilationsReglement = {}
    dictVentilationsPrestation = {}
    for ventilation in Ventilation.objects.filter(condition_famille):
        dictVentilations[ventilation.pk] = ventilation
        dictVentilationsReglement.setdefault(ventilation.reglement_id, []).append(ventilation.pk)
        dictVentilationsPrestation.setdefault(ventilation.prestation_id, []).append(ventilation.pk)

    def Get_montant_ventile(liste_idventilations=[]):
        return sum([dictVentilations[IDventilation].montant for IDventilation in liste_idventilations], Decimal(0))

    # Récupère les prestations
    prestations = list(Prestation.objects.select_related("activite").filter(condition_famille))

    # Vérifie qu'il n'y a pas de prestations négatives (ou ventilées au-delà de leur montant)
    for prestation in prestations:
        if prestation.montant - Get_montant_ventile(dictVentilationsPrestation.get(prestation.pk, [])) < Decimal(0):
            logger.debug("La ventilation automatique n'est pas compatible avec les prestations comportant un montant négatif.")
            resultat["possible"] = False
            return resultat

    # Vérification de la ventilation de chaque règlement
    cle_temporaire = 0
    for reglement in Reglement.objects.select_related("mode").filter(condition_famille):

        # Recherche s'il reste du crédit à ventiler dans ce règlement
        credit = reglement.montant - Get_montant_ventile(dictVentilationsReglement.get(reglement.pk, []))
        if credit <= Decimal(0):
            continue

        # Recherche s'il reste des prestations à ventiler pour cette famille
        for prestation in prestations:
            ResteAVentiler = prestation.montant - Get_montant_ventile(dictVentilationsPrestation.get(prestation.pk, []))
            montant = min(ResteAVentiler, credit)
            if montant <= Decimal(0):
                continue

            # Modification d'une ventilation existante entre ce règlement et cette prestation
            ventilation_existante = None
            for IDventilation in dictVentilationsPrestation.get(prestation.pk, []):
                if dictVentilations[IDventilation].reglement_id == reglement.pk:
                    ventilation_existante = dictVentilations[IDventilation]
                    break

            if ventilation_existante:
                ventilation_existante.montant += montant
                if enregistrer:
                    ventilation_existante.save()
            else:
                # Création d'une ventilation
                if enregistrer:
                    ventilation = Ventilation.objects.create(famille_id=IDfamille, reglement=reglement, prestation=prestation, montant=montant)
                    cle = ventilation.pk
                else:
                    cle_temporaire -= 1
                    cle = cle_temporaire
                    ventilation = Ventilation(famille_id=IDfamille, reglement=reglement, prestation=prestation, montant=montant)
                dictVentilations[cle] = ventilation
                dictVentilationsReglement.setdefault(reglement.pk, []).append(cle)
                dictVentilationsPrestation.setdefault(prestation.pk, []).append(cle)
                resultat["nbre_creations"] += 1

            resultat["affectations"].append((reglement, prestation, montant))
            resultat["total"] += montant
            credit -= montant
            if credit <= Decimal(0):
                break

    # Ajuster les soldes des factures de la famille
    if enregistrer:
        utils_factures.Maj_solde_actuel_factures(IDfamille=IDfamille)

    return resultat


def Ventilation_auto(IDfamille=None):
    """ Effectue la ventilation automatique. Retourne False si elle est impossible (prestation négative). """
    return Calculer_ventilation_auto(IDfamille=IDfamille, enregistrer=True)["possible"]


def Get_familles_ventilation_manuelle(liste_idfamilles=[]):
    """ Familles pour lesquelles la ventilation automatique est impossible :
    au moins une prestation dont le montant est inférieur au montant déjà ventilé (prestation négative notamment) """
    from django.db.models import F, DecimalField, Value
    from django.db.models.functions import Coalesce
    return set(Prestation.objects.filter(famille_id__in=liste_idfamilles)
               .annotate(ventile=Coalesce(Sum("ventilation__montant"), Value(Decimal(0)), output_field=DecimalField()))
               .filter(montant__lt=F("ventile")).values_list("famille_id", flat=True).distinct())
