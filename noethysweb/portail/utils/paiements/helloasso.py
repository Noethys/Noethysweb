# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Paiement en ligne HelloAsso (API v5 "Checkout Intent") """

import logging, json, hmac
import requests
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.cache import cache
from core.models import Paiement
from core.utils import utils_portail
from portail.utils.paiements.commun import Erreur, Enregistrement_reglement, Get_compte_portail, Get_idtransaction_court

logger = logging.getLogger(__name__)

URLS = {
    "sandbox": {
        "api": "https://api.helloasso-sandbox.com",
        "token": "https://api.helloasso-sandbox.com/oauth2/token",
    },
    "production": {
        "api": "https://api.helloasso.com",
        "token": "https://api.helloasso.com/oauth2/token",
    },
}


class ErreurHelloasso(Exception):
    pass


def Get_mode(parametres_portail={}):
    return parametres_portail.get("helloasso_mode") or "sandbox"


def Get_access_token(parametres_portail={}):
    """ Récupère un jeton d'accès OAuth2 (client_credentials), en le mettant en cache jusqu'à expiration """
    mode = Get_mode(parametres_portail)
    client_id = parametres_portail.get("helloasso_client_id")
    cle_cache = "helloasso_access_token_%s_%s" % (mode, client_id)

    token = cache.get(cle_cache)
    if token:
        return token

    reponse = requests.post(URLS[mode]["token"], data={
        "client_id": client_id,
        "client_secret": parametres_portail.get("helloasso_client_secret"),
        "grant_type": "client_credentials",
    }, timeout=15)

    if reponse.status_code != 200:
        logger.error("Erreur HelloAsso lors de la récupération du token : %s %s", reponse.status_code, reponse.text)
        raise ErreurHelloasso("Impossible de s'authentifier auprès d'HelloAsso.")

    data = reponse.json()
    token = data["access_token"]

    # Mise en cache du token, avec une marge de sécurité d'une minute avant expiration
    duree_validite = int(data.get("expires_in", 1800)) - 60
    cache.set(cle_cache, token, timeout=max(duree_validite, 60))

    return token


def Appel_api(parametres_portail={}, methode="GET", chemin="", donnees=None):
    """ Effectue un appel authentifié à l'API HelloAsso v5 """
    mode = Get_mode(parametres_portail)
    token = Get_access_token(parametres_portail=parametres_portail)
    url = "%s%s" % (URLS[mode]["api"], chemin)
    headers = {"Authorization": "Bearer %s" % token}

    reponse = requests.request(methode, url, json=donnees, headers=headers, timeout=15)

    if reponse.status_code not in (200, 201):
        logger.error("Erreur HelloAsso lors de l'appel %s %s : %s %s", methode, chemin, reponse.status_code, reponse.text)
        raise ErreurHelloasso("Erreur lors de la communication avec HelloAsso (code %d)." % reponse.status_code)

    return reponse.json()


def Creer_checkout_intent(parametres_portail={}, montant=None, email=None, item_name="", back_url="", error_url="", return_url="", metadata=None):
    """ Crée une intention de paiement (Checkout Intent) et renvoie la réponse de l'API (id + redirectUrl) """
    slug = parametres_portail.get("helloasso_organisation_slug")

    corps = {
        "totalAmount": int(round(float(montant) * 100)),
        "initialAmount": int(round(float(montant) * 100)),
        "itemName": item_name,
        "backUrl": back_url,
        "errorUrl": error_url,
        "returnUrl": return_url,
        "containsDonation": False,
    }
    if email:
        corps["payer"] = {"email": email}
    if metadata is not None:
        corps["metadata"] = metadata

    return Appel_api(parametres_portail=parametres_portail, methode="POST", chemin="/v5/organizations/%s/checkout-intents" % slug, donnees=corps)


def Get_checkout_intent(parametres_portail={}, checkout_intent_id=None):
    """ Récupère l'état d'une intention de paiement (utilisé pour vérifier une notification avant de l'appliquer) """
    slug = parametres_portail.get("helloasso_organisation_slug")
    return Appel_api(parametres_portail=parametres_portail, methode="GET", chemin="/v5/organizations/%s/checkout-intents/%s" % (slug, checkout_intent_id))


def Creer_paiement(request=None, demande=None, parametres_portail={}):
    """ Création de l'intention de paiement et renvoi de l'URL de la page de paiement HelloAsso """
    # Enregistrement préalable du paiement (pour obtenir un ID à transmettre en métadonnée à HelloAsso)
    paiement = Paiement.objects.create(famille=demande.famille, systeme_paiement="helloasso", idtransaction="",
                                       montant=demande.montant, saisie=Get_mode(parametres_portail), ventilation=demande.ventilation_str)

    try:
        checkout_intent = Creer_checkout_intent(
            parametres_portail=parametres_portail,
            montant=demande.montant,
            email=demande.famille.mail,
            item_name="Paiement en ligne",
            back_url=request.build_absolute_uri(reverse("retour_helloasso_cancel")),
            error_url=request.build_absolute_uri(reverse("retour_helloasso_error")),
            return_url=request.build_absolute_uri(reverse("retour_helloasso_success")),
            metadata={"idpaiement": paiement.pk},
        )
    except ErreurHelloasso as err:
        logger.error("Page EFFECTUER_PAIEMENT_EN_LIGNE HELLOASSO (Famille %s) : %s", demande.famille, err)
        paiement.delete()
        return Erreur("Le paiement en ligne est momentanément indisponible. Merci de réessayer ultérieurement.")

    # Mémorisation de l'identifiant de la transaction (id de la demande d'encaissement HelloAsso)
    paiement.idtransaction = str(checkout_intent["id"])
    paiement.save()

    logger.debug("Page EFFECTUER_PAIEMENT_EN_LIGNE HELLOASSO (Famille %s) : IDtransaction=%s montant=%s ventilation=%s", demande.famille, paiement.idtransaction, str(demande.montant), demande.ventilation_str)

    return JsonResponse({"systeme_paiement": "helloasso", "urltoredirect": checkout_intent["redirectUrl"]})


@csrf_exempt
@require_http_methods(["POST"])
def notification_helloasso(request, cle=None):
    """ Réception d'une notification (webhook) HelloAsso.
        Important : l'URL de notification n'est pas transmise à la création du paiement, elle doit être
        configurée une fois pour toutes dans l'espace HelloAsso (Mon compte > Configuration de l'API > Notifications),
        avec pour valeur l'URL absolue de cette vue, clé de sécurité incluse (paramètre "Clé de sécurité des
        notifications" du portail). """
    logger.debug("Page NOTIFICATION HELLOASSO")

    parametres_portail = utils_portail.Get_dict_parametres()

    # Vérification de la clé de sécurité, AVANT toute autre analyse, pour rejeter au plus vite les
    # requêtes non légitimes (protection contre le spam de cette URL forcément publique)
    cle_attendue = parametres_portail.get("helloasso_cle_notification") or ""
    if not cle_attendue or not hmac.compare_digest(cle or "", cle_attendue):
        logger.error("Page NOTIFICATION_HELLOASSO : clé de sécurité invalide.")
        return HttpResponse(status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error("Page NOTIFICATION_HELLOASSO : corps de la requête illisible.")
        return HttpResponse(status=400)

    logger.debug(data)

    # On ne traite que les évènements de paiement
    if data.get("eventType") not in ("Payment", "Order"):
        return HttpResponse("Notification ignorée")

    # Récupération de l'identifiant de paiement transmis en métadonnée à la création du checkout intent
    # (HelloAsso renvoie les metadata au niveau racine de la notification, pas dans "data")
    metadata = data.get("metadata") or {}
    idpaiement = metadata.get("idpaiement")
    if not str(idpaiement or "").isdigit():
        logger.error("Page NOTIFICATION_HELLOASSO : aucune métadonnée idpaiement dans la notification.")
        return HttpResponse(status=400)

    # HelloAsso envoie systématiquement au moins deux notifications distinctes pour un même paiement
    # ("Order" et "Payment"), potentiellement en parallèle. On pose un verrou applicatif de courte durée
    # le temps de l'appel réseau vers HelloAsso, pour éviter que les deux notifications ne déclenchent
    # chacune un appel simultané et, pire, un double enregistrement du règlement.
    cle_verrou = "helloasso_notification_lock_%s" % idpaiement
    if not cache.add(cle_verrou, 1, timeout=30):
        logger.debug("Page NOTIFICATION_HELLOASSO : notification pour le paiement ID%s déjà en cours de traitement, on l'ignore.", idpaiement)
        return HttpResponse("Notification already being processed")

    try:
        paiement = Paiement.objects.filter(pk=int(idpaiement), systeme_paiement="helloasso").first()
        if not paiement:
            logger.error("Page NOTIFICATION_HELLOASSO : paiement ID%s introuvable.", idpaiement)
            return HttpResponse(status=404)

        # Si le paiement est déjà PAID, on ne le traite pas une seconde fois
        if paiement.resultat == "PAID":
            return HttpResponse("Notification already processed")

        # Par sécurité, on ne fait jamais confiance au contenu brut de la notification : on rappelle l'API
        # HelloAsso avec le jeton d'accès du compte pour vérifier l'état réel de l'intention de paiement.
        # D'après la documentation HelloAsso, le champ "order" n'est renvoyé que si la commande a bien été
        # créée et que le paiement est un succès. Cet appel réseau est fait HORS transaction, pour ne
        # jamais garder un verrou de ligne en base pendant un appel externe potentiellement lent.
        try:
            checkout_intent = Get_checkout_intent(parametres_portail=parametres_portail, checkout_intent_id=paiement.idtransaction)
        except ErreurHelloasso as err:
            logger.error("Page NOTIFICATION_HELLOASSO : impossible de vérifier le paiement ID%s auprès d'HelloAsso (%s).", idpaiement, err)
            return HttpResponse(status=502)

        resultat = "PAID" if checkout_intent.get("order") else "WAITING"

        # Deuxième ligne de défense contre le double traitement : verrouillage de la ligne en base
        # (au cas où deux processus distincts arriveraient malgré tout à passer le verrou applicatif
        # ci-dessus, par exemple après son expiration).
        with transaction.atomic():
            paiement = Paiement.objects.select_for_update().get(pk=paiement.pk)
            if paiement.resultat == "PAID":
                return HttpResponse("Notification already processed")

            paiement.resultat = resultat
            paiement.message = data.get("eventType")
            paiement.save()

            if resultat == "PAID":
                Enregistrement_reglement(paiement=paiement, compte=Get_compte_portail(parametres_portail), num_piece=Get_idtransaction_court(paiement))

        return HttpResponse("Notification processed")
    finally:
        cache.delete(cle_verrou)
