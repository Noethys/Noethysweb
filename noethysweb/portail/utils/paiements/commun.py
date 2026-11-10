# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Paiement en ligne : fonctions communes à tous les systèmes de paiement """

import logging, decimal, datetime, copy, json
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.db.models import Sum, Q
from core.models import Facture, Prestation, Ventilation, PortailPeriode, Reglement, Payeur, ModeReglement, CompteBancaire, PortailRenseignement, Mandat
from core.utils import utils_portail, utils_dates, utils_texte, utils_preferences

ETATS_PAIEMENTS = {1: "RECEIVED", 2: "ACCEPTED", 3: "PAID", 4: "DENIED", 5: "CANCELLED", 6: "WAITING", 7: "EXPIRED", 99: "ERROR"}

PREFIXES_VENTILATION = {"facture": "F", "periode": "P", "cotisation": "C"}


def Montant_en_centimes(montant):
    """ Convertit un montant décimal en nombre entier de centimes """
    return int((decimal.Decimal(montant) * 100).quantize(decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP))


def Centimes_en_montant(centimes):
    """ Convertit un nombre entier de centimes en montant décimal à 2 décimales """
    return (decimal.Decimal(int(centimes)) / 100).quantize(decimal.Decimal("0.01"))


def Erreur(texte=""):
    """ Réponse d'erreur renvoyée au navigateur """
    return JsonResponse({"erreur": texte}, status=401)


class Demande():
    """ Demande de paiement validée, transmise au système de paiement """
    def __init__(self, famille=None, montant=None, paiement_echelonne=0, dict_ventilation={}, liste_factures=[]):
        self.famille = famille
        self.montant = montant
        self.paiement_echelonne = paiement_echelonne
        self.dict_ventilation = dict_ventilation
        self.liste_factures = liste_factures
        # Format mémorisé dans Paiement.ventilation : "F12#25.50,P3#10.00,C45#15.00"
        self.ventilation_str = ",".join(["%s%d#%s" % (PREFIXES_VENTILATION[type_impaye], ID, solde)
                                         for type_impaye in ("facture", "periode", "cotisation") for ID, solde in dict_ventilation[type_impaye].items()])


def Get_soldes_prestations(famille=None, prestations=[]):
    """ Renvoie {IDprestation: solde restant dû} calculé à partir des ventilations enregistrées """
    ventilations = Ventilation.objects.values("prestation").filter(famille=famille, prestation__in=prestations).annotate(total=Sum("montant"))
    dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
    return {prestation.pk: prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0)) for prestation in prestations}


def Valider_demande(request=None, parametres_portail={}):
    """ Contrôle la demande de paiement envoyée par le navigateur (données non dignes de confiance).
        Renvoie (Demande, None) si elle est valide, sinon (None, JsonResponse d'erreur). """
    famille = request.user.famille
    erreur_parametres = Erreur(_("Les paramètres du paiement sont invalides."))

    # Récupération des paramètres
    try:
        liste_impayes = [texte for texte in request.POST.get("liste_impayes", "").split(",") if texte]
        montant_reglement = decimal.Decimal(request.POST.get("montant_reglement", "0")).quantize(decimal.Decimal("0.01"))
        paiement_echelonne = int(request.POST.get("paiement_echelonne", 0) or 0)
    except (decimal.InvalidOperation, ValueError, TypeError):
        return None, erreur_parametres
    if not montant_reglement.is_finite():
        return None, erreur_parametres

    # Vérifie que le montant est supérieur à zéro
    if montant_reglement <= 0:
        return None, Erreur(_("Le montant doit être supérieur à zéro !"))

    # Vérifie que le montant est supérieur au montant minimal fixé
    montant_minimal = decimal.Decimal(str(parametres_portail.get("paiement_ligne_montant_minimal") or 0))
    if montant_reglement < montant_minimal:
        return None, Erreur(_("Le paiement en ligne nécessite un montant minimal de %.2f %s !") % (montant_minimal, utils_preferences.Get_symbole_monnaie()))

    # Vérifie que la famille a une adresse mail
    if not famille.mail:
        return None, Erreur(_("Aucune adresse mail n'a été renseignée sur votre dossier. Le paiement en ligne est impossible sans cette information."))

    # Analyse des éléments sélectionnés
    dict_ventilation = {"facture": {}, "periode": {}, "cotisation": {}}
    try:
        for texte in liste_impayes:
            type_impaye, ID, solde = texte.split("##")
            dict_ventilation[type_impaye][int(ID)] = decimal.Decimal(solde).quantize(decimal.Decimal("0.01"))
            if not dict_ventilation[type_impaye][int(ID)].is_finite():
                return None, erreur_parametres
    except (KeyError, ValueError, decimal.InvalidOperation):
        return None, erreur_parametres
    if not any(dict_ventilation.values()):
        return None, Erreur(_("Aucun élément à régler n'a été sélectionné."))

    # Règles du portail (jusqu'ici contrôlées uniquement par le navigateur)
    if not parametres_portail.get("paiement_ligne_multi_factures") and sum(len(dict_type) for dict_type in dict_ventilation.values()) > 1:
        return None, Erreur(_("Vous ne pouvez régler qu'un seul élément à la fois."))
    if parametres_portail.get("paiement_ligne_off_si_prelevement") and Mandat.objects.filter(famille=famille, actif=True).exists():
        return None, Erreur(_("Le paiement en ligne n'est pas disponible car vous bénéficiez du prélèvement automatique."))

    # Le montant doit correspondre à la somme des éléments sélectionnés
    soldes = [solde for dict_type in dict_ventilation.values() for solde in dict_type.values()]
    if any(solde <= 0 for solde in soldes) or montant_reglement != sum(soldes):
        return None, erreur_parametres

    # Factures : uniquement celles de la famille connectée, non annulées et dans les délais
    liste_factures = Facture.objects.select_related("regie", "prefixe").filter(pk__in=dict_ventilation["facture"].keys(), famille=famille).exclude(etat="annulation").order_by("date_debut")
    if len(liste_factures) != len(dict_ventilation["facture"]):
        logger.warning("Paiement en ligne (%s): facture(s) n'appartenant pas à la famille : %s", famille, list(dict_ventilation["facture"].keys()))
        return None, erreur_parametres
    for facture in liste_factures:
        if dict_ventilation["facture"][facture.pk] > facture.solde_actuel or (facture.date_limite_paiement and datetime.date.today() > facture.date_limite_paiement):
            return None, Erreur(_("La facture n°%s ne peut plus être réglée en ligne.") % facture.numero)

    # Cotisations : appartenance à la famille et montants inférieurs au solde réel
    if dict_ventilation["cotisation"]:
        prestations = Prestation.objects.filter(pk__in=dict_ventilation["cotisation"].keys(), famille=famille, cotisation__isnull=False, cotisation__unite_cotisation__prefacturation=True, facture__isnull=True)
        if len(prestations) != len(dict_ventilation["cotisation"]):
            return None, erreur_parametres
        soldes_prestations = Get_soldes_prestations(famille=famille, prestations=prestations)
        if any(dict_ventilation["cotisation"][prestation.pk] > soldes_prestations[prestation.pk] for prestation in prestations):
            return None, erreur_parametres

    # Périodes de préfacturation : accessibles à la famille et montants inférieurs au solde réel
    if dict_ventilation["periode"]:
        periodes = PortailPeriode.objects.filter(pk__in=dict_ventilation["periode"].keys(), prefacturation=True)
        if len(periodes) != len(dict_ventilation["periode"]) or not all(periode.Is_famille_authorized(famille=famille) for periode in periodes):
            return None, erreur_parametres
        for periode in periodes:
            prestations = Prestation.objects.filter(famille=famille, facture__isnull=True, activite_id=periode.activite_id, date__range=(periode.date_debut, periode.date_fin))
            solde_periode = sum(solde for solde in Get_soldes_prestations(famille=famille, prestations=prestations).values() if solde > 0)
            if dict_ventilation["periode"][periode.pk] > solde_periode:
                return None, erreur_parametres

    return Demande(famille=famille, montant=montant_reglement, paiement_echelonne=paiement_echelonne,
                   dict_ventilation=dict_ventilation, liste_factures=liste_factures), None


def Analyser_ventilation(ventilation_str=""):
    """ Convertit "F12#25.50,P3#10.00" en {"facture": {12: Decimal("25.50")}, "periode": {3: Decimal("10.00")}, "cotisation": {}} """
    types = {prefixe: type_impaye for type_impaye, prefixe in PREFIXES_VENTILATION.items()}
    dict_ventilation = {"facture": {}, "periode": {}, "cotisation": {}}
    for texte in (ventilation_str or "").split(","):
        if texte and texte[0] in types:
            ID, montant = texte[1:].split("#")
            dict_ventilation[types[texte[0]]][int(ID)] = decimal.Decimal(montant)
    return dict_ventilation


def Get_factures_ventilation(paiement=None):
    """ Renvoie la liste des IDfacture contenus dans la ventilation d'un paiement """
    return list(Analyser_ventilation(paiement.ventilation)["facture"].keys())


def Get_compte_portail(parametres_portail={}):
    """ Compte bancaire associé aux paiements en ligne dans les paramètres du portail """
    return CompteBancaire.objects.get(pk=int(parametres_portail.get("paiement_ligne_compte_bancaire")))


def Get_idtransaction_court(paiement=None):
    """ Identifiant de transaction sans le préfixe éventuel (ex : Payzen "20261110_123456" -> "123456") """
    return paiement.idtransaction.split("_")[1] if "_" in paiement.idtransaction else paiement.idtransaction


def Enregistrement_reglement(paiement=None, compte=None, num_piece="", liste_echeances=None):
    """ Création des règlements et ventilations d'un paiement en ligne.
        compte : compte bancaire du règlement (fourni par le système de paiement)
        num_piece : numéro de pièce du règlement
        liste_echeances : [(montant, date), ...] pour un paiement en plusieurs fois (Payzen) """
    IDtransaction = Get_idtransaction_court(paiement)
    parametres_portail = utils_portail.Get_dict_parametres()
    liste_paiements = liste_echeances or [(paiement.montant, datetime.date.today())]

    # Analyse de la ventilation
    dict_paiements = Analyser_ventilation(paiement.ventilation)
    periodes = PortailPeriode.objects.filter(pk__in=dict_paiements["periode"].keys())
    factures = Facture.objects.filter(pk__in=dict_paiements["facture"].keys(), famille=paiement.famille)

    # Recherche payeur
    dernier_reglement = Reglement.objects.filter(famille=paiement.famille).last()
    if dernier_reglement:
        payeur = dernier_reglement.payeur
    else:
        payeur = Payeur.objects.create(famille=paiement.famille, nom=paiement.famille.nom)

    # Importation des prestations à payer
    conditions = Q(facture__in=factures)
    for periode in periodes:
        conditions |= Q(date__range=(periode.date_debut, periode.date_fin), activite_id=periode.activite_id)
    if dict_paiements["cotisation"].keys():
        conditions |= Q(pk__in=dict_paiements["cotisation"].keys())
    prestations = Prestation.objects.filter(Q(famille=paiement.famille), conditions).distinct().order_by("date")

    # Calcul du solde de chaque prestation
    soldes = Get_soldes_prestations(famille=paiement.famille, prestations=prestations)
    for prestation in prestations:
        prestation.solde = soldes[prestation.pk]

    # Création du règlement
    mode = ModeReglement.objects.get(pk=int(parametres_portail.get("paiement_ligne_mode_reglement")))
    for index, (montant_paiement, date_paiement) in enumerate(liste_paiements, start=1):

        observations = "Transaction n°%s sur %s (IDpaiement %d)." % (IDtransaction, paiement.systeme_paiement, paiement.pk)
        if len(liste_paiements) > 1:
            observations += " Paiement en %d fois du %s (%d/%d)." % (len(liste_paiements), utils_dates.ConvertDateToFR(datetime.date.today()), index, len(liste_paiements))

        reglement = Reglement.objects.create(
            famille=paiement.famille,
            date=date_paiement,
            mode=mode,
            numero_piece=num_piece,
            montant=decimal.Decimal(montant_paiement),
            payeur=payeur,
            observations=observations,
            compte=compte,
        )

        # Associe le règlement créé au paiement
        paiement.reglements.add(reglement)

        # Ventilation du règlement
        credit = copy.copy(montant_paiement)
        for prestation in prestations:
            if credit and prestation.solde:
                ventilation = min(prestation.solde, credit)
                prestation.solde -= ventilation
                credit -= ventilation
                Ventilation.objects.create(famille=paiement.famille, reglement=reglement, prestation=prestation, montant=ventilation)

        # Mémorisation du paiement dans l'historique du portail
        PortailRenseignement.objects.create(famille=paiement.famille, categorie="famille_reglements", code="Nouveau paiement en ligne", validation_auto=True, idobjet=reglement.pk,
                                            nouvelle_valeur=json.dumps("Paiement %s de %s" % (paiement.systeme_paiement, utils_texte.Formate_montant(reglement.montant))))

    # MAJ du solde des factures
    for facture in factures:
        facture.Maj_solde_actuel()
