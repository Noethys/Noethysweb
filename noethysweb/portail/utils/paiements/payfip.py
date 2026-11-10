# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Paiement en ligne PayFiP (DGFiP), en mode URL ou web service """

import logging, re
logger = logging.getLogger(__name__)
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.db import transaction
from django.conf import settings
from eopayment import Payment
from eopayment.payfip_ws import normalize_objet
from core.models import Facture, Paiement
from portail.utils.paiements.commun import ETATS_PAIEMENTS, Centimes_en_montant, Erreur, Get_factures_ventilation, Enregistrement_reglement

# Adresses IP d'émission des notifications PayFiP (guide de mise en oeuvre PayFiP régie URL, DGFiP, juin 2025)
PAYFIP_IPS_NOTIFICATION = getattr(settings, "PAYFIP_IPS_NOTIFICATION", ("145.242.11.3", "145.242.11.240", "145.242.11.241"))


def Get_payment_payfip_ws(request=None, numcli=None, saisie="T"):
    """ Backend PayFiP par web service (permet de vérifier le résultat d'un paiement auprès de la DGFiP) """
    return Payment("payfip_ws", {
        "numcli": numcli,
        "saisie": saisie,
        "normal_return_url": request.build_absolute_uri(reverse("retour_payfip_utilisateur")),
        "automatic_return_url": request.build_absolute_uri(reverse("retour_payfip")),
    })


def Creer_paiement(request=None, demande=None, parametres_portail={}):
    """ Création du paiement et renvoi de l'URL de la page de paiement PayFiP """
    famille = demande.famille
    payfip_mode = parametres_portail.get("payfip_mode")
    payfip_ws = parametres_portail.get("payfip_protocole") == "ws"
    logger.debug("PAYFIP Création du paiement : famille=%s payfip_mode=%s payfip_ws=%s", famille, payfip_mode, payfip_ws)

    # Code SAISIE : T=test, X=validation/activation, A=production (mode URL) ou W=production (web service)
    if payfip_mode == "validation": saisie = "X"
    elif payfip_mode == "production": saisie = "W" if payfip_ws else "A"
    else: saisie = "T"

    # PayFiP : une seule facture et rien d'autre (le paiement est rattaché au titre côté DGFiP)
    if len(demande.dict_ventilation["facture"]) != 1 or demande.dict_ventilation["cotisation"]:
        logger.debug("PAYFIP (%s): une et une seule facture est nécessaire", famille)
        return Erreur("Avec PayFiP, sélectionnez une seule facture à la fois.")

    # Vérifie qu'il n'y a pas de préfacturation dedans
    if demande.dict_ventilation["periode"]:
        logger.debug("PAYFIP (%s): il n'est pas possible de régler de la préfacturation", famille)
        return Erreur("Paiement de la prefacturation impossible avec PAYFIP")

    facture = demande.liste_factures[0]
    if not facture.regie:
        logger.debug("PAYFIP (%s): aucune régie n'a été paramétrée.", famille)
        return Erreur("Aucune régie n'a été paramétrée. Contactez l'administrateur du portail.")

    objet = normalize_objet("Paiement %s" % facture.regie.nom)
    refdet = "%s%06d" % (facture.prefixe.prefixe if facture.prefixe else "", facture.numero)
    try:
        if payfip_ws:
            # Web service : transaction identifiée par un idOp non devinable, résultat vérifié auprès de la DGFiP au retour
            p = Get_payment_payfip_ws(request=request, numcli=facture.regie.numclitipi, saisie=saisie)
            idtransaction, url_inutilisee, url_paiement = p.request(amount=demande.montant, exer=str(facture.date_debut.year),
                                                                    refdet=refdet, subject=objet, email=famille.mail)
        else:
            # Mode URL : la notification n'est pas signée, elle sera filtrée par adresse IP et contrôlée (voir retour_payfip)
            p = Payment("tipi", {"numcli": facture.regie.numclitipi, "automatic_return_url": request.build_absolute_uri(reverse("retour_payfip"))})
            idtransaction, url_inutilisee, url_paiement = p.request(amount=str(demande.montant), exer=str(facture.date_debut.year),
                                                                    refdet=refdet, objet=objet, email=famille.mail, saisie=saisie)
    except Exception as err:
        logger.error("PAYFIP (%s): erreur lors de la création du paiement : %s", famille, err)
        return Erreur("Le paiement en ligne est momentanément indisponible. Merci de réessayer ultérieurement.")
    logger.debug("PAYFIP (%s): idtransaction=%s refdet=%s montant=%s", famille, idtransaction, refdet, demande.montant)

    # Enregistrement du paiement
    Paiement.objects.create(famille=famille, systeme_paiement="payfip", idtransaction=idtransaction,
                            refdet=refdet, montant=demande.montant, objet=objet, saisie=saisie, ventilation=demande.ventilation_str)

    return JsonResponse({"systeme_paiement": "payfip", "urltoredirect": url_paiement})


@csrf_exempt
@require_http_methods(["POST"])
def retour_payfip(request):
    """ Notification serveur à serveur de PayFiP. URL publique et non signée : son contenu n'est pas digne de confiance. """
    data = request.POST
    idop = (data.get("idOp") or data.get("idop") or "").strip()
    logger.debug("PAYFIP Notification : ip=%s donnees=%s", request.META.get("REMOTE_ADDR"), data)

    try:
        if idop:
            return Retour_payfip_ws(request, idop)
        return Retour_payfip_url(request, data)
    except Exception as err:
        logger.exception("PAYFIP Notification : erreur : %s", err)
        return HttpResponse("Error", status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def retour_payfip_utilisateur(request):
    """ Retour du navigateur de l'usager après le paiement : simple redirection, aucun traitement """
    return redirect("portail_facturation")


def Retour_payfip_ws(request, idop):
    """ Web service : seul l'idOp est lu, le résultat réel est demandé à la DGFiP """
    if not re.match(r"^[A-Za-z0-9\-]{1,50}$", idop):
        return HttpResponse("Notification ignored", status=400)

    with transaction.atomic():
        # Verrouillage de la ligne pour éviter un double enregistrement (notifications simultanées)
        paiement = Paiement.objects.select_for_update().filter(systeme_paiement="payfip", idtransaction=idop).exclude(refdet=idop).first()
        if not paiement:
            logger.warning("PAYFIP Notification : paiement pré-enregistré introuvable pour idop=%s", idop)
            return HttpResponse("Notification ignored", status=404)
        if paiement.resultat == "PAID":
            return HttpResponse("Notification processed")

        facture = Get_facture_paiement(paiement)
        if not facture:
            return HttpResponse("Notification ignored", status=404)

        reponse = Get_payment_payfip_ws(request=request, numcli=facture.regie.numclitipi, saisie=paiement.saisie).payment_status(idop, transaction_date=paiement.horodatage)
        resultat = ETATS_PAIEMENTS.get(reponse.result, "ERROR")
        if resultat == "WAITING":
            return HttpResponse("Notification processed")

        Traitement_resultat(paiement=paiement, facture=facture, resultat=resultat, donnees=reponse.bank_data or {}, message=reponse.bank_status)

    return HttpResponse("Notification processed")


def Retour_payfip_url(request, data):
    """ Mode URL : aucune signature n'existe. Protection par filtrage des IP de la DGFiP + contrôles de cohérence """
    ip = request.META.get("REMOTE_ADDR")
    if ip not in PAYFIP_IPS_NOTIFICATION:
        # Requête ignorée. Redirection vers le portail au cas où il s'agirait du navigateur d'un usager.
        logger.warning("PAYFIP Notification ignorée car provenant d'une IP non autorisée (%s) : %s", ip, data)
        return redirect("portail_facturation")

    refdet, resultrans = data.get("refdet", ""), data.get("resultrans", "")
    try:
        montant = Centimes_en_montant(data.get("montant"))
    except (TypeError, ValueError):
        return HttpResponse("Notification ignored", status=400)

    with transaction.atomic():
        # Paiement en attente correspondant au refdet et au montant notifiés (verrouillé contre les notifications simultanées)
        paiement = Paiement.objects.select_for_update().filter(systeme_paiement="payfip", idtransaction=refdet, refdet=refdet, montant=montant, resultat__isnull=True).order_by("-pk").first()
        if not paiement:
            logger.warning("PAYFIP Notification : aucun paiement en attente pour refdet=%s montant=%s", refdet, montant)
            return HttpResponse("Notification processed")

        facture = Get_facture_paiement(paiement)
        if not facture:
            return HttpResponse("Notification ignored", status=404)

        resultat = {"P": "PAID", "V": "PAID", "R": "DENIED", "Z": "DENIED", "A": "CANCELLED"}.get(resultrans, "ERROR")
        Traitement_resultat(paiement=paiement, facture=facture, resultat=resultat, donnees=data, message="resultrans=%s" % resultrans)

    return HttpResponse("Notification processed")


def Get_facture_paiement(paiement=None):
    """ Facture (et régie) associée à un paiement PayFiP """
    facture = Facture.objects.select_related("regie", "regie__compte_bancaire").filter(famille=paiement.famille, pk__in=Get_factures_ventilation(paiement)).first()
    if not facture or not facture.regie:
        logger.error("PAYFIP Notification : facture ou régie introuvable pour le paiement %s", paiement.pk)
        return None
    return facture


def Traitement_resultat(paiement=None, facture=None, resultat=None, donnees={}, message=""):
    """ Contrôle de cohérence avec le paiement pré-enregistré puis enregistrement du résultat (à appeler dans une transaction) """
    if resultat == "PAID":
        try:
            montant = Centimes_en_montant(donnees.get("montant"))
        except (TypeError, ValueError):
            montant = None
        controles = {
            "montant": (montant, paiement.montant),
            "refdet": (str(donnees.get("refdet")), paiement.refdet),
            "numcli": (str(donnees.get("numcli")).strip(), str(facture.regie.numclitipi).strip()),
            "saisie": (str(donnees.get("saisie")), paiement.saisie),
        }
        anomalies = {code: valeurs for code, valeurs in controles.items() if valeurs[0] != valeurs[1]}
        if anomalies:
            logger.error("PAYFIP Notification : incohérences pour le paiement %s : %s", paiement.pk, anomalies)
            resultat = "ERROR"
            message = "Incoherence : %s" % ", ".join(anomalies.keys())

    paiement.resultat = resultat
    paiement.resultrans = str(donnees.get("resultrans") or "")[:50]
    paiement.numauto = str(donnees.get("numauto") or "")[:50]
    paiement.dattrans = str(donnees.get("dattrans") or "")[:50]
    paiement.heurtrans = str(donnees.get("heurtrans") or "")[:50]
    paiement.message = (message or "")[:450]
    paiement.save()

    if resultat == "PAID":
        # Le règlement est rattaché au compte bancaire de la régie
        Enregistrement_reglement(paiement=paiement, compte=facture.regie.compte_bancaire)
