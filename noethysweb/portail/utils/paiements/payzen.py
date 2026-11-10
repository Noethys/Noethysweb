# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Paiement en ligne Payzen (Lyra) """

import logging, decimal, sys, datetime, re
logger = logging.getLogger(__name__)
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from eopayment import Payment, systempayv2
# eopayment limite vads_payment_config à "SINGLE" ou "MULTI" (sans paramètres) : on lève cette restriction
# pour autoriser "MULTI:first=...;count=...;period=..." et "MULTI_EXT:..."
systempayv2.PARAMETER_MAP["vads_payment_config"].choices = None
from core.models import Paiement
from core.utils import utils_portail, utils_fichiers, utils_preferences
from portail.utils.paiements.commun import ETATS_PAIEMENTS, Montant_en_centimes, Centimes_en_montant, Erreur, Enregistrement_reglement, Get_compte_portail, Get_idtransaction_court


def Calcul_echeances_payzen(vads_payment_config="", montant=decimal.Decimal(0)):
    """ Renvoie la liste des échéances [(montant, date), ...] d'un paiement Payzen d'après son vads_payment_config.
        Renvoie None si la configuration est invalide ou incohérente avec le montant total. """
    montant_total = Montant_en_centimes(montant)
    aujourdhui = datetime.date.today()
    vads_payment_config = (vads_payment_config or "SINGLE").replace(">", "=")

    if not vads_payment_config.startswith("MULTI"):
        return [(Centimes_en_montant(montant_total), aujourdhui)]

    try:
        if vads_payment_config.startswith("MULTI_EXT:"):
            # Paiement avancé en plusieurs fois : MULTI_EXT:AAAAMMJJ=montant;AAAAMMJJ=montant;...
            echeances = [(int(centimes), datetime.datetime.strptime(date, "%Y%m%d").date()) for date, centimes in re.findall(r"([0-9]{8})=([0-9]+)", vads_payment_config)]
        else:
            # Paiement simple en plusieurs fois : MULTI:first=xxx;count=n;period=j
            params = dict(param.split("=", 1) for param in vads_payment_config.split(":", 1)[1].split(";") if "=" in param)
            premier, nbre, periode = int(params["first"]), int(params["count"]), int(params["period"])
            if nbre < 1 or premier > montant_total:
                return None
            echeances = [(premier, aujourdhui)]
            if nbre > 1:
                reste = montant_total - premier
                montant_echeance = reste // (nbre - 1)
                for index in range(1, nbre):
                    # Le reliquat éventuel de l'arrondi est affecté à la dernière échéance
                    centimes = montant_echeance + (reste - montant_echeance * (nbre - 1) if index == nbre - 1 else 0)
                    echeances.append((centimes, aujourdhui + datetime.timedelta(days=periode * index)))
    except (KeyError, ValueError, IndexError):
        return None

    # Vérifie la cohérence avec le montant total
    if not echeances or any(centimes <= 0 for centimes, date in echeances) or sum(centimes for centimes, date in echeances) != montant_total:
        return None

    return [(Centimes_en_montant(centimes), date) for centimes, date in echeances]


def GetPaymentPayzen(request=None, parametres_portail={}):
    # Création de la requete Payzen
    p = Payment("payzen", {
        'vads_site_id': parametres_portail.get("payzen_site_id"),
        'vads_ctx_mode': parametres_portail.get("payzen_mode"),
        'secret_test': parametres_portail.get("payzen_certificat_test"),
        'secret_production': parametres_portail.get("payzen_certificat_production"),
        'signature_algo': parametres_portail.get("payzen_algo"),
        'vads_url_return': request.build_absolute_uri(reverse("portail_facturation")),
        'vads_url_cancel': request.build_absolute_uri(reverse("retour_payzen_cancel")),
        'vads_url_error': request.build_absolute_uri(reverse("retour_payzen_error")),
        'vads_url_refused': request.build_absolute_uri(reverse("retour_payzen_refused")),
        'vads_url_success': request.build_absolute_uri(reverse("retour_payzen_success")),
        'vads_contrib': 'noethys',
        })#, logger=logger)

    # Modifie le répertoire temp si on est sous Windows
    if sys.platform.startswith("win"):
        p.backend.PATH = utils_fichiers.GetTempRep()

    return p


def Creer_paiement(request=None, demande=None, parametres_portail={}):
    """ Création du paiement et renvoi du formulaire de paiement Payzen """
    # Envoi de la requete
    p = GetPaymentPayzen(request=request, parametres_portail=parametres_portail)

    if demande.paiement_echelonne == 1:
        # Le paiement échelonné doit être activé dans les paramètres du portail (contrôle côté serveur)
        if not parametres_portail.get("payzen_echelonnement"):
            return Erreur("Le paiement en plusieurs fois n'est pas proposé.")

        # Vérifie le montant minimal pour le paiement échelonné
        montant_minimal_echelonnement = decimal.Decimal("30.0")
        if demande.montant < montant_minimal_echelonnement:
            return Erreur("Le paiement en plusieurs fois nécessite un montant minimal de %s %s !" % (montant_minimal_echelonnement, utils_preferences.Get_symbole_monnaie()))

        # 3 fois standard (calcul en centimes)
        montant_total = Montant_en_centimes(demande.montant)
        vads_payment_config = "MULTI:first=%d;count=3;period=30" % ((montant_total // 3) + (montant_total % 3))

        # N fois avancé : Calcul des dates et montants échelonnés
        # montant_total = float(demande.montant) * 100
        # today = datetime.date.today()
        # paiement_1 = "%s=%d" % (today.strftime("%Y%m%d"), (montant_total // 3) + (montant_total % 3))
        # paiement_2 = "%s=%d" % ((today + datetime.timedelta(days=30)).strftime("%Y%m%d"), montant_total // 3)
        # paiement_3 = "%s=%d" % ((today + datetime.timedelta(days=60)).strftime("%Y%m%d"), montant_total // 3)
        # vads_payment_config = "MULTI_EXT:%s;%s;%s" % (paiement_1, paiement_2, paiement_3)
    else:
        vads_payment_config = "SINGLE"
    requete = p.request(amount=demande.montant, email=demande.famille.mail, vads_payment_config=vads_payment_config)
    transaction_id, f, form = requete

    logger.debug("Page EFFECTUER_PAIEMENT_EN_LIGNE PAYZEN (Famille %s) : IDtransaction=%s montant=%s ventilation=%s", demande.famille, transaction_id, str(demande.montant), demande.ventilation_str)

    # Enregistrement du paiement
    # Le champ objet (inutilisé pour Payzen) mémorise la configuration d'échéances envoyée : elle fait foi lors de l'IPN
    Paiement.objects.create(famille=demande.famille, systeme_paiement="payzen", idtransaction=transaction_id, objet=vads_payment_config,
                            montant=demande.montant, saisie=parametres_portail.get("payzen_mode"), ventilation=demande.ventilation_str)

    # Renvoie le formulaire de paiement au template
    form = str(form)
    form = form.replace("<form ", "<form id='form_paiement' ")
    return JsonResponse({"systeme_paiement": "payzen", "form_paiement": form})


@csrf_exempt
@require_http_methods(["POST"])
def ipn_payzen(request):
    logger.debug("Page RETOUR IPN PAYZEN")

    # Extraction des variables post
    data = request.POST
    logger.debug(data)

    # Récupération des paramètres généraux du portail
    parametres_portail = utils_portail.Get_dict_parametres()

    # Récupération des données et calcul de la signature
    p = GetPaymentPayzen(request=request, parametres_portail=parametres_portail)
    try:
        reponse = p.response(data.urlencode())
    except Exception as err:
        logger.error("IPN PAYZEN : notification illisible (%s).", err)
        return HttpResponse("Notification invalide", status=400)

    # Une notification dont la signature est invalide est rejetée : elle peut avoir été forgée
    if reponse.signed is not True:
        logger.error("IPN PAYZEN IDtransaction=%s : signature invalide, notification rejetée.", reponse.order_id)
        return HttpResponse("Signature invalide", status=400)

    # eopayment choisit la clé de signature (test ou production) d'après le vads_ctx_mode fourni par la notification
    # elle-même : on refuse donc toute notification dont le mode ou la boutique ne correspondent pas au paramétrage,
    # sinon une notification signée avec la clé de test serait acceptée sur un portail en production.
    if data.get("vads_ctx_mode") != parametres_portail.get("payzen_mode") or (data.get("vads_site_id") or "").strip() != str(parametres_portail.get("payzen_site_id") or "").strip():
        logger.error("IPN PAYZEN IDtransaction=%s : mode (%s) ou boutique (%s) non conforme au paramétrage, notification rejetée.", reponse.order_id, data.get("vads_ctx_mode"), data.get("vads_site_id"))
        return HttpResponse("Notification non conforme", status=400)

    # Recherche l'état du paiement
    resultat = ETATS_PAIEMENTS.get(reponse.result, "ERROR")
    vads_url_check_src = data.get("vads_url_check_src", "")
    vads_payment_config = data.get("vads_payment_config", "SINGLE")

    logger.debug("IPN PAYZEN IDtransaction=%s : resultat=%s, origine=%s, payment_config=%s", reponse.order_id, resultat, vads_url_check_src, vads_payment_config)

    # Recherche du paiement préenregistré
    paiement = Paiement.objects.filter(idtransaction=reponse.order_id, systeme_paiement="payzen").last()
    if not paiement:
        logger.error("IPN PAYZEN IDtransaction=%s : paiement pré-enregistré introuvable.", reponse.order_id)
        return HttpResponse("Notification processed")

    # Payzen peut envoyer plusieurs notifications pour une même transaction (rejeu, retour boutique,
    # opérations Back Office, échéances d'un paiement en plusieurs fois...), éventuellement simultanées.
    # Le verrouillage de la ligne et la transaction garantissent que les règlements ne sont créés qu'une seule fois,
    # et qu'aucun règlement partiel n'est conservé en cas d'erreur pendant l'enregistrement.
    with transaction.atomic():
        paiement = Paiement.objects.select_for_update().get(pk=paiement.pk)

        if paiement.resultat == "PAID" or paiement.reglements.exists():
            if resultat != "PAID":
                # Par exemple le refus d'une échéance ultérieure : on ne touche pas aux règlements, mais on le signale
                logger.warning("IPN PAYZEN IDtransaction=%s (IDpaiement %d) : notification '%s' reçue pour un paiement déjà enregistré (origine=%s, message=%s). Vérification manuelle conseillée.",
                               reponse.order_id, paiement.pk, resultat, vads_url_check_src, reponse.bank_status)
            else:
                logger.debug("IPN PAYZEN IDtransaction=%s : paiement déjà enregistré, notification ignorée.", reponse.order_id)
            return HttpResponse("Notification already processed")

        # Calcul des échéances et contrôle du montant notifié par Payzen
        liste_echeances = None
        message = reponse.bank_status
        if resultat == "PAID":
            # La configuration mémorisée à la création du paiement est prioritaire sur celle de la notification
            config_attendue = paiement.objet if (paiement.objet or "").startswith(("SINGLE", "MULTI")) else None
            if config_attendue and vads_payment_config != config_attendue:
                logger.warning("IPN PAYZEN IDtransaction=%s : payment_config notifié (%s) différent de celui envoyé (%s), utilisation de ce dernier.", reponse.order_id, vads_payment_config, config_attendue)
            vads_payment_config = config_attendue or vads_payment_config
            liste_echeances = Calcul_echeances_payzen(vads_payment_config=vads_payment_config, montant=paiement.montant)

            # Contrôle du montant notifié : montant total, ou montant de la 1re échéance pour un paiement en plusieurs fois
            vads_amount = data.get("vads_amount", "")
            montants_acceptes = {Montant_en_centimes(paiement.montant)}
            if liste_echeances:
                montants_acceptes.add(Montant_en_centimes(liste_echeances[0][0]))

            if not liste_echeances:
                logger.error("IPN PAYZEN IDtransaction=%s : configuration d'échéances invalide (%s).", reponse.order_id, vads_payment_config)
                resultat, message = "ERROR", "Configuration d'échéances invalide"
            elif not vads_amount.isdigit() or int(vads_amount) not in montants_acceptes:
                logger.error("IPN PAYZEN IDtransaction=%s : montant notifié (%s centimes) incohérent avec le montant attendu (%s).", reponse.order_id, vads_amount, paiement.montant)
                resultat, message, liste_echeances = "ERROR", "Montant notifié incohérent", None

        paiement.resultat = resultat
        paiement.message = (message or "")[:450]
        paiement.save()

        if resultat == "PAID":
            Enregistrement_reglement(paiement=paiement, compte=Get_compte_portail(parametres_portail), num_piece=Get_idtransaction_court(paiement), liste_echeances=liste_echeances)

    return HttpResponse("Notification processed")
