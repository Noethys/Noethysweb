# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal, sys, datetime, re, copy, json
logger = logging.getLogger(__name__)
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from django.contrib import messages
from eopayment import Payment
from portail.views.base import CustomView
from core.models import Activite, Facture, Prestation, Ventilation, PortailPeriode, Paiement, Reglement, Payeur, ModeReglement, CompteBancaire, PortailRenseignement, ModeleImpression, Mandat
from core.utils import utils_portail, utils_fichiers, utils_dates, utils_texte
from django.core.serializers import serialize
from django.views.decorators.http import require_POST
from datetime import date


ETATS_PAIEMENTS = {1: "RECEIVED", 2: "ACCEPTED", 3: "PAID", 4: "DENIED", 5: "CANCELLED", 6: "WAITING", 99: "ERROR"}


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


class View_retour_paiement(CustomView, TemplateView):
    menu_code = "portail_facturation"
    template_name = "portail/retour_paiement.html"
    etat = None

    def get_context_data(self, **kwargs):
        context = super(View_retour_paiement, self).get_context_data(**kwargs)
        context['page_titre'] = _("Facturation")
        context['etat'] = self.etat
        return context


def effectuer_paiement_en_ligne(request):
    # Récupération des paramètres
    liste_impayes = request.POST.get("liste_impayes").split(",")
    montant_reglement = decimal.Decimal(request.POST.get("montant_reglement"))
    paiement_echelonne = int(request.POST.get("paiement_echelonne"))

    # Ajout de la récupération de l'id de la facture
    idfacture = int(request.POST.get("idfacture", 0))
    activite_pay = int(request.POST.get("activite_pay", 0))


    # Récupération des paramètres généraux du portail
    parametres_portail = utils_portail.Get_dict_parametres()

    # Vérifie que le montant est supérieur à zéro
    if not montant_reglement:
        return JsonResponse({"erreur": _("Le montant doit être supérieur à zéro !")}, status=401)

    # Vérifie que le montant est supérieur au montant minimal fixé
    if montant_reglement < decimal.Decimal(parametres_portail.get("paiement_ligne_montant_minimal", 0.0)):
        return JsonResponse({"erreur": _("Le paiement en ligne nécessite un montant minimal de %.2f € !") % parametres_portail.paiement_ligne_montant_minimal}, status=401)

    # Mémorise les numéros de factures et la ventilation
    dict_ventilation = {"facture": {}, "periode": {}, "cotisation": {}}
    for texte in liste_impayes:
        type_impaye, ID, solde = texte.split("##")
        dict_ventilation[type_impaye][int(ID)] = decimal.Decimal(solde)

    # Importation des factures
    liste_factures = Facture.objects.select_related("regie").filter(pk__in=dict_ventilation["facture"].keys()).all().order_by("date_debut")

    # On mémorise la ventilation
    ventilation = []
    for type_impaye in ["facture", "periode", "cotisation"]:
        for ID, solde in dict_ventilation[type_impaye].items():
            if type_impaye == "facture" : prefixe = "F"
            if type_impaye == "periode": prefixe = "P"
            if type_impaye == "cotisation": prefixe = "C"
            ventilation.append("%s%d#%s" % (prefixe, ID, solde))
    ventilation_str = ",".join(ventilation)

    # --------------------------- Mode démo -----------------------------

    if parametres_portail.get("paiement_ligne_systeme") == "demo":
        logger.debug("Page EFFECTUER_PAIEMENT_EN_LIGNE MODE DEMO (Famille %s) : montant=%s ventilation_str=%s", request.user.famille, str(montant_reglement), ventilation_str)
        return JsonResponse({"systeme_paiement": "demo", "texte": "Paiement impossible, vous êtes en mode démo !"})

    # ----------------------- Paiement avec PAYFIP -------------------------

    if parametres_portail.get("paiement_ligne_systeme") == "payfip":
        payfip_mode = parametres_portail.get("payfip_mode")
        logger.debug("Page EFFECTUER_PAIEMENT EN LIGNE : famille=%s payfip_mode=%s", request.user.famille, payfip_mode)

        if payfip_mode == "validation": saisie = "X"
        elif payfip_mode == "production": saisie = "A"
        else: saisie = "T"

        # il y a plus d'une facture sélectionnée
        if len(dict_ventilation["facture"]) > 1:
            logger.debug(u"Page EFFECTUER_PAIEMENT_EN_LIGNE (%s): plus d'une facture selectionnee pour PAYFIP NON TRAITE", request.user.famille)
            return JsonResponse({"erreur": "Paiement en ligne multi-factures impossible"}, status=401)

        # Vérifie qu'il n'y a pas de préfacturation dedans
        if len(dict_ventilation["periode"]) > 0 :
            logger.debug(u"Page EFFECTUER_PAIEMENT_EN_LIGNE (%s): Il n'est pas possible de régler de la préfacturation avec PAYFIP", request.user.famille)
            return JsonResponse({"erreur": "Paiement de la prefacturation impossible avec TIPI"}, status=401)

        # Envoi de la requete
        facture = liste_factures[0]
        if not facture.regie:
            logger.debug(u"Page EFFECTUER_PAIEMENT_EN_LIGNE TIPI (%s): Aucune régie n'a été paramétrée.", request.user.famille)
            return JsonResponse({"erreur": "Aucune régie n'a été paramétrée. Contactez l'administrateur du portail."}, status=401)

        p = Payment("tipi", {'numcli': facture.regie.numclitipi, "automatic_return_url": request.build_absolute_uri(reverse("retour_payfip"))})
        objet = "Paiement %s" % utils_texte.Supprimer_accents(facture.regie.nom)
        requete = p.request(
            amount=str(montant_reglement),
            exer=str(facture.date_debut.year),
            refdet="%06d" % facture.numero,
            objet=objet,
            email=request.user.famille.mail,
            saisie=saisie)
        logger.debug(u"Page EFFECTUER_PAIEMENT_EN_LIGNE (%s): requete: %s // systeme_paiement(%s)", request.user.famille, requete, "payfip")

        # Enregistrement du paiement
        Paiement.objects.create(famille=request.user.famille, systeme_paiement="payfip", idtransaction=requete[0],
                                refdet=facture.numero, montant=montant_reglement, objet=objet, saisie=saisie, ventilation=ventilation_str)

        return JsonResponse({"systeme_paiement": "payfip", "urltoredirect": requete[2]})

    # ----------------------- Paiement avec PAYZEN ----------------------

    if parametres_portail.get("paiement_ligne_systeme") == "payzen":
        # Envoi de la requete
        p = GetPaymentPayzen(request=request, parametres_portail=parametres_portail)

        if paiement_echelonne == 1:
            # Vérifie le montant minimal pour le paiement échelonné
            montant_minimal_echelonnement = decimal.Decimal("30.0")
            if montant_reglement < montant_minimal_echelonnement:
                return JsonResponse({"erreur": "Le paiement en plusieurs fois nécessite un montant minimal de %s € !" % montant_minimal_echelonnement}, status=401)

            # Calcul des dates et montants échelonnés
            montant_total = float(montant_reglement) * 100
            today = datetime.date.today()
            paiement_1 = "%s=%d" % (today.strftime("%Y%m%d"), (montant_total // 3) + (montant_total % 3))
            paiement_2 = "%s=%d" % ((today + datetime.timedelta(days=30)).strftime("%Y%m%d"), montant_total // 3)
            paiement_3 = "%s=%d" % ((today + datetime.timedelta(days=60)).strftime("%Y%m%d"), montant_total // 3)
            vads_payment_config = "MULTI_EXT:%s;%s;%s" % (paiement_1, paiement_2, paiement_3)
        else:
            vads_payment_config = "SINGLE"
        requete = p.request(amount=montant_reglement, email=request.user.famille.mail, vads_payment_config=vads_payment_config)
        transaction_id, f, form = requete

        logger.debug("Page EFFECTUER_PAIEMENT_EN_LIGNE PAYZEN (Famille %s) : IDtransaction=%s montant=%s ventilation_str=%s", request.user.famille, transaction_id, str(montant_reglement), ventilation_str)

        # Enregistrement du paiement
        Paiement.objects.create(famille=request.user.famille, systeme_paiement="payzen", idtransaction=transaction_id,
                                montant=montant_reglement, saisie=parametres_portail.get("payzen_mode"), ventilation=ventilation_str)

        # Renvoie le formulaire de paiement au template
        form = str(form)
        form = form.replace("<form ", "<form id='form_paiement' ")
        return JsonResponse({"systeme_paiement": "payzen", "form_paiement": form})

    # ----------------------- Paiement avec PAYASSO -------------------------
    if parametres_portail.get("paiement_ligne_systeme") == "payasso":
        # Vérifie s'il y a plus d'une facture sélectionnée
        if len(dict_ventilation["facture"]) > 1:
            logger.debug(
                "Page EFFECTUER_PAIEMENT_EN_LIGNE (%s): Plus d'une facture sélectionnée pour PAYASSO NON TRAITÉ",
                request.user.famille)
            return JsonResponse({"erreur": "Paiement en ligne multi-factures impossible"}, status=401)

        # On mémorise la ventilation
        for type_impaye in "facture", "periode", "cotisation":
            for ID, solde in dict_ventilation[type_impaye].items():
                factureid = ID

        logger.debug(
            "Page EFFECTUER_PAIEMENT_EN_LIGNE MODE PAYASSO (Famille %s): montant=%s IDfacture=%s ",
            request.user.famille, str(montant_reglement), factureid )

        """ Cherhe le lien de paiement de l'activité  """
        # Importation de la facture
        factureact = Facture.objects.get(pk=factureid)

        # ID activité
        activite_ids = Facture.objects.filter(idfacture=factureid).values_list('activites', flat=True)

        if len(activite_ids) != 1:
            raise ValueError("Il y a plus d'une activité associée à cette facture.")
        else:
            activite_id = activite_ids[0]

        logger.debug(
            "Page EFFECTUER_PAIEMENT_EN_LIGNE MODE PAYASSO : Activite=%s ",
            activite_id)

        # Obtenez l'ID de l'activité associée à la facture
        activite_id = Facture.objects.filter(idfacture=factureid).values('activites').first()

        # Vérifiez si une activité unique est associée à la facture
        activite_ids = Facture.objects.filter(idfacture=factureid).values_list('activites', flat=True)

        if len(activite_ids) != 1 or ';' in activite_ids[0]:
            return JsonResponse({"erreur": _("Cette facture ne peut être payée via PayAsso !")}, status=401)
        else:
            activite_id = activite_ids[0]

        # Obtenez l'URL de paiement de l'activité
        pay_activite = Activite.objects.filter(idactivite=activite_id).values('pay').first()

        # Log pour déboguer
        logger.debug("Page EFFECTUER_PAIEMENT_EN_LIGNE MODE PAYASSO : URL=%s", pay_activite)

        # Récupérez l'URL de paiement
        urlpayasso = pay_activite.get('pay') if pay_activite else None

        # Vérifie que le montant est supérieur à zéro
        if not urlpayasso:
            return JsonResponse({"erreur": _("Cette facture ne peut être payée via PayAsso !")}, status=401)

        #Numéro unique id transaction
        sequence_of_digits = ''.join(char for char in datetime.datetime.now().strftime("%Y%m%d%H%M%S") if char.isdigit())

        # Utilisez cette chaîne pour le numéro de transaction
        transaction_id = "PAYASSO" + sequence_of_digits

        # Enregistrement du paiement
        Paiement.objects.create(famille=request.user.famille, systeme_paiement="payasso", idtransaction=transaction_id,
                                refdet=factureid, montant=montant_reglement, objet=f"Paiement facture {factureid} via PayAsso", saisie="", ventilation=ventilation_str, resultat = "PAID", message = "Paiement validé sans vérification" )
        logger.debug("Enreg. OK")

#début enregistrement

        logger.debug("Page règlement")
        IDtransaction = transaction_id
        paiement = Paiement.objects.get(idtransaction=transaction_id)

        # Analyse de la ventilation
        dict_paiements = {"facture": {}, "periode": {}, "cotisation": {}}
        for texte in paiement.ventilation.split(","):
            if texte[0] == "F": type_impaye = "facture"
            if texte[0] == "P": type_impaye = "periode"
            if texte[0] == "C": type_impaye = "cotisation"
            ID, montant = texte[1:].split("#")
            dict_paiements[type_impaye][int(ID)] = float(montant)

        # Importation des périodes et des factures
        periodes = PortailPeriode.objects.filter(pk__in=dict_paiements["periode"].keys())
        factures = Facture.objects.select_related("regie", "regie__compte_bancaire").filter(
            pk__in=dict_paiements["facture"].keys())

        num_piece = ""
        liste_paiements = [(paiement.montant, datetime.date.today())]
        compte = CompteBancaire.objects.first()

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

        # Importation des ventilations existantes
        ventilations = Ventilation.objects.values("prestation").filter(famille=paiement.famille,
                                                                       prestation__in=prestations).annotate(
            total=Sum("montant"))
        dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
        for prestation in prestations:
            prestation.solde = prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0))
            prestation.nouvelle_ventilation = decimal.Decimal(0)

        # Création du règlement
        for index, (montant_paiement, date_paiement) in enumerate(liste_paiements, start=1):

            observations = "Transaction n°%s sur %s (IDpaiement %d)." % (
            IDtransaction, paiement.systeme_paiement, paiement.pk)
            if len(liste_paiements) > 1:
                observations += " Paiement en %d fois du %s (%d/%d)." % (
                len(liste_paiements), utils_dates.ConvertDateToFR(datetime.date.today()), index, len(liste_paiements))

            reglement = Reglement.objects.create(
                famille=paiement.famille,
                date=datetime.date.today(),
                mode=ModeReglement.objects.get(pk=int(parametres_portail.get("paiement_ligne_mode_reglement"))),
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
                    prestation.nouvelle_ventilation = ventilation
                    prestation.solde -= ventilation
                    credit -= ventilation
                    Ventilation.objects.create(famille=paiement.famille, reglement=reglement, prestation=prestation,
                                               montant=ventilation)

            # Mémorisation du paiement dans l'historique du portail
            PortailRenseignement.objects.create(famille=paiement.famille, categorie="famille_reglements",
                                                code="Nouveau paiement en ligne", validation_auto=True,
                                                idobjet=reglement.pk,
                                                nouvelle_valeur=json.dumps("Paiement %s de %s" % (
                                                paiement.systeme_paiement,
                                                utils_texte.Formate_montant(reglement.montant))))

        # MAJ du solde des factures
        for facture in factures:
            facture.Maj_solde_actuel()

    #fin enregistrement

        # Renvoyer la réponse JSON
        return JsonResponse({"systeme_paiement": "payasso", "urlpayasso": urlpayasso})


@csrf_exempt
@require_http_methods(["POST"])
def retour_payfip(request):
    logger.debug("Page RETOUR PAYFIP")

    # Extraction des variables post
    data = request.POST

    # Extraction des champs non traités par eopayment
    resultrans = data.get("resultrans", 0)
    numauto = data.get("numauto", 0)
    dattrans = data.get("dattrans", 0)
    heurtrans = data.get("heurtrans", 0)

    # Récupération des données et calcul de la signature
    p = Payment("tipi", {})
    reponse = p.response(data.urlencode())

    # Recherche l'état du paiement
    resultat = ETATS_PAIEMENTS[reponse.result]

    # Modification du paiement préenregistré
    paiement = Paiement.objects.filter(idtransaction=reponse.transaction_id).last()
    if not paiement:
        logger.debug("Page RETOUR_PAYFIP: le paiement pre-enregistre n'a pas été trouvé.")
        return

    # Réponse dans le log
    logger.debug("Page RETOUR_PAYFIP: reponse=%s refdet=%s)", reponse, paiement.refdet)

    # Si le paiement est déjà PAID
    if paiement.resultat == "PAID":
        logger.debug("Page RETOUR_PAYFIP: Le paiement est déjà PAID.")
        return

    paiement.resultrans = resultrans
    paiement.resultat = resultat
    paiement.numauto = numauto
    paiement.dattrans = dattrans
    paiement.heurtrans = heurtrans
    paiement.message = reponse.bank_status
    paiement.save()

    # Enregistrement du résultat et redirection
    if resultat == "PAID":
        Enregistrement_reglement(paiement=paiement)

    return HttpResponse("Notification processed")
    logger.debug("Vue retour_payasso ")


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
    reponse = p.response(data.urlencode())

    # Vérifie que la signature de la réponse est correcte
    if reponse.signed != True:
        logger.debug(u"Paiement en ligne IDtransaction=%s : ATTENTION, erreur de signature dans la réponse !" % reponse.order_id)

    # Recherche l'état du paiement
    resultat = ETATS_PAIEMENTS[reponse.result]

    # Recherche s'il s'agit un paiement MULTI
    if resultat == "ERROR":
        vads_card_brand = data.get("vads_card_brand", 0, type=str)
        vads_result = data.get("vads_result", 0, type=str)
        if reponse.signed == True and vads_card_brand == "MULTI" and vads_result == "00":
            resultat = "PAID"

    # Affichage de la réponse dans le log
    logger.debug(u"Paiement en ligne IDtransaction=%s : signature=%s, resultat=%s" % (reponse.order_id, reponse.signed, resultat))

    # Modification du paiement préenregistré
    paiement = Paiement.objects.get(idtransaction=reponse.order_id)
    paiement.resultat = resultat
    paiement.message = reponse.bank_status
    paiement.save()

    # Paiement échelonné
    vads_payment_config = data.get("vads_payment_config", "SINGLE")
    vads_payment_config = vads_payment_config.replace("=", ">")

    # Enregistrement de l'action
    if resultat == "PAID":
        Enregistrement_reglement(paiement=paiement, vads_payment_config=vads_payment_config)

    return HttpResponse("Notification processed")


def Enregistrement_reglement(paiement=None, vads_payment_config=None):
    logger.debug("Page règlement")
    IDtransaction = paiement.idtransaction.split("_")[1] if "_" in paiement.idtransaction else paiement.idtransaction

    # Récupération des paramètres généraux du portail
    parametres_portail = utils_portail.Get_dict_parametres()

    # Analyse de la ventilation
    dict_paiements = {"facture": {}, "periode": {}, "cotisation": {}}
    for texte in paiement.ventilation.split(","):
        if texte[0] == "F": type_impaye = "facture"
        if texte[0] == "P": type_impaye = "periode"
        if texte[0] == "C": type_impaye = "cotisation"
        ID, montant = texte[1:].split("#")
        dict_paiements[type_impaye][int(ID)] = float(montant)

    # Importation des périodes et des factures
    periodes = PortailPeriode.objects.filter(pk__in=dict_paiements["periode"].keys())
    factures = Facture.objects.select_related("regie", "regie__compte_bancaire").filter(pk__in=dict_paiements["facture"].keys())

    num_piece = ""
    liste_paiements = [(paiement.montant, datetime.date.today())]

    if "payzen" in paiement.systeme_paiement:
        compte = CompteBancaire.objects.get(pk=int(parametres_portail.get("paiement_ligne_compte_bancaire")))
        num_piece = IDtransaction
        if vads_payment_config.startswith("MULTI"):
            # Paiement en plusieurs fois
            liste_paiements = [(float(montant) / 100, datetime.datetime.strptime(date, "%Y%m%d")) for date, montant in re.findall(r"([0-9]+)>([0-9]+)", vads_payment_config)]

    if "payfip" in paiement.systeme_paiement:
        compte = factures[0].regie.compte_bancaire
        #num_piece = "auth_num-" + self.dict_parametres["numauto"]

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

    # Importation des ventilations existantes
    ventilations = Ventilation.objects.values("prestation").filter(famille=paiement.famille, prestation__in=prestations).annotate(total=Sum("montant"))
    dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
    for prestation in prestations:
        prestation.solde = prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0))
        prestation.nouvelle_ventilation = decimal.Decimal(0)

    # Création du règlement
    for index, (montant_paiement, date_paiement) in enumerate(liste_paiements, start=1):

        observations = "Transaction n°%s sur %s (IDpaiement %d)." % (IDtransaction, paiement.systeme_paiement, paiement.pk)
        if len(liste_paiements) > 1:
            observations += " Paiement en %d fois du %s (%d/%d)." % (len(liste_paiements), utils_dates.ConvertDateToFR(datetime.date.today()), index, len(liste_paiements))

        reglement = Reglement.objects.create(
            famille=paiement.famille,
            date=datetime.date.today(),
            mode=ModeReglement.objects.get(pk=int(parametres_portail.get("paiement_ligne_mode_reglement"))),
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
                prestation.nouvelle_ventilation = ventilation
                prestation.solde -= ventilation
                credit -= ventilation
                Ventilation.objects.create(famille=paiement.famille, reglement=reglement, prestation=prestation, montant=ventilation)

        # Mémorisation du paiement dans l'historique du portail
        PortailRenseignement.objects.create(famille=paiement.famille, categorie="famille_reglements", code="Nouveau paiement en ligne", validation_auto=True, idobjet=reglement.pk,
                                            nouvelle_valeur=json.dumps("Paiement %s de %s" % (paiement.systeme_paiement, utils_texte.Formate_montant(reglement.montant))))

    # MAJ du solde des factures
    for facture in factures:
        facture.Maj_solde_actuel()


def get_detail_facture(request):
    """ Génére un texte HTML contenant le détail d'une facture """
    idfacture = int(request.POST.get("idfacture", 0))

    # Importation de la facture
    facture = Facture.objects.get(pk=idfacture)
    if facture.famille != request.user.famille:
        return JsonResponse({"texte": "Accès interdit"}, status=401)

    # Importation des prestations
    prestations = Prestation.objects.select_related("individu", "activite").filter(facture=facture).order_by("date")

    # Création du texte HTML
    context = {
        "facture": facture,
        "prestations": prestations,
        "parametres_portail": utils_portail.Get_dict_parametres(),
    }
    return render(request, 'portail/detail_facture.html', context)


def imprimer_facture(request):
    """ Imprimer une facture au format PDF """
    idfacture = int(request.POST.get("idfacture", 0))
    idmodele_impression = int(request.POST.get("idmodele_impression", 0))

    # Importation des options d'impression
    modele_impression = ModeleImpression.objects.get(pk=idmodele_impression)
    dict_options = json.loads(modele_impression.options)
    dict_options["modele"] = modele_impression.modele_document

    # Création du PDF
    from facturation.utils import utils_facturation
    facturation = utils_facturation.Facturation()
    resultat = facturation.Impression(liste_factures=[idfacture,], dict_options=dict_options)

    return JsonResponse({"nom_fichier": resultat["nom_fichier"]})


class View(CustomView, TemplateView):
    menu_code = "portail_facturation"
    template_name = "portail/facturation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Facturation"
        logger.debug("Def context")

        # Vérifie si la famille est abonnée au prélèvement automatique
        context["prelevement_actif"] = Mandat.objects.filter(famille=self.request.user.famille, actif=True).exists()
        context['paiement_actif'] = not (context['parametres_portail']["paiement_ligne_off_si_prelevement"] and context["prelevement_actif"])

        # Importation des paiements PAYFIP en cours
        context['liste_paiements'] = Paiement.objects.filter(famille=self.request.user.famille, systeme_paiement="payfip", resultat__isnull=True, horodatage__gt=datetime.datetime.now() - datetime.timedelta(minutes=5))
        dict_paiements = {"F": {}, "P": {}, "C": {}}
        for paiement in context['liste_paiements']:
            for texte in paiement.ventilation.split(","):
                type_impaye = texte[0]
                ID, montant = texte[1:].split("#")
                ID, montant = int(ID), decimal.Decimal(montant)
                dict_paiements[type_impaye].setdefault(ID, decimal.Decimal(0))
                dict_paiements[type_impaye][ID] += montant

        # Importation des paiements PAYASSO en cours
        context['liste_paiements'] = Paiement.objects.filter(famille=self.request.user.famille, systeme_paiement="payasso", resultat__isnull=True, horodatage__gt=datetime.datetime.now() - datetime.timedelta(minutes=5))
        dict_paiements = {"F": {}, "P": {}, "C": {}}
        for paiement in context['liste_paiements']:
            for texte in paiement.ventilation.split(","):
                type_impaye = texte[0]
                ID, montant = texte[1:].split("#")
                ID, montant = int(ID), decimal.Decimal(montant)
                dict_paiements[type_impaye].setdefault(ID, decimal.Decimal(0))
                dict_paiements[type_impaye][ID] += montant

        # Affichage des notifications de paiements récents
        for paiement in Paiement.objects.filter(famille=self.request.user.famille, notification__isnull=True, horodatage__gt=datetime.datetime.now() - datetime.timedelta(hours=1)):
            if paiement.resultat == "PAID":
                messages.add_message(self.request, messages.SUCCESS, "Le paiement en ligne de %.2f Euros a été enregistré avec succès" % paiement.montant)
            elif paiement.resultat == "DENIED":
                messages.add_message(self.request, messages.ERROR, "Le paiement en ligne de %.2f Euros a été refusé" % paiement.montant)
            elif paiement.resultat == "CANCELLED":
                messages.add_message(self.request, messages.ERROR, "Le paiement en ligne de %.2f Euros a été annulé" % paiement.montant)
            else:
                messages.add_message(self.request, messages.ERROR, "Le paiement en ligne de %.2f Euros a rencontré une erreur. La notification de paiement semble absente." % paiement.montant)
            paiement.notification = datetime.datetime.now()
            paiement.save()

        # Importation des factures impayées
        liste_factures = []
        liste_factures_impayees = []
        total_factures_impayees = decimal.Decimal(0)
        for facture in Facture.objects.filter(famille=self.request.user.famille).exclude(etat="annulation").order_by("-date_edition"):
            if facture.pk in dict_paiements["F"]:
                facture.regle = facture.total
                facture.solde_actuel = decimal.Decimal(0)
            if facture.solde_actuel and (not facture.date_limite_paiement or datetime.date.today() <= facture.date_limite_paiement):
                liste_factures_impayees.append(facture)
                total_factures_impayees += facture.solde_actuel
            liste_factures.append(facture)
        context['liste_factures_impayees'] = liste_factures_impayees
        context['liste_factures'] = liste_factures

        # Importation de la préfacturation des périodes
        total_periodes_impayees = decimal.Decimal(0)
        liste_finale_periodes = []

        # Récupération des périodes de réservations
        liste_dates_extremes = []
        liste_periodes = []
        for periode in PortailPeriode.objects.select_related("activite").prefetch_related("categories").filter(prefacturation=True):
            if periode.Is_famille_authorized(famille=self.request.user.famille):
                periode.total = decimal.Decimal(0)
                periode.regle = decimal.Decimal(0)
                periode.solde = decimal.Decimal(0)
                liste_periodes.append(periode)
                liste_dates_extremes.append(periode.date_debut)
                liste_dates_extremes.append(periode.date_fin)
        if liste_periodes:
            date_min = min(liste_dates_extremes)
            date_max = max(liste_dates_extremes)

            # Recherche les impayés par période de réservations
            if liste_periodes:
                ventilations = Ventilation.objects.values("prestation").filter(famille=self.request.user.famille, prestation__date__gte=date_min, prestation__date__lte=date_max).annotate(total=Sum("montant"))
                dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
                for prestation in Prestation.objects.filter(famille=self.request.user.famille, date__gte=date_min, date__lte=date_max, facture__isnull=True):
                    solde_prestation = prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0))
                    if solde_prestation > decimal.Decimal(0):
                        for periode in liste_periodes:
                            if periode.date_debut <= prestation.date <= periode.date_fin and prestation.activite_id == periode.activite_id:
                                periode.total += prestation.montant
                                periode.regle += dict_ventilations.get(prestation.pk, decimal.Decimal(0))
                                periode.solde += solde_prestation

                # Ajoute les paiements en cours
                for periode in liste_periodes:
                    if periode.pk in dict_paiements["P"]:
                        periode.regle = periode.total
                        periode.solde = decimal.Decimal(0)
                    total_periodes_impayees += periode.solde
                    if periode.solde:
                        liste_finale_periodes.append(periode)

        context["liste_periodes_prefacturation"] = liste_finale_periodes

        # Importation de la préfacturation des cotisations
        total_cotisations_impayees = decimal.Decimal(0)
        liste_finale_cotisations = []

        ventilations = Ventilation.objects.values("prestation").filter(famille=self.request.user.famille, prestation__cotisation__isnull=False).annotate(total=Sum("montant"))
        dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
        for prestation in Prestation.objects.select_related("cotisation").filter(famille=self.request.user.famille, cotisation__isnull=False, facture__isnull=True, cotisation__unite_cotisation__prefacturation=True):
            solde_prestation = prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0))
            if solde_prestation > decimal.Decimal(0):
                prestation.total = prestation.montant
                prestation.regle = dict_ventilations.get(prestation.pk, decimal.Decimal(0))
                prestation.solde = solde_prestation

                # Ajoute les paiements en cours
                if prestation.pk in dict_paiements["C"]:
                    prestation.regle = prestation.total
                    prestation.solde = decimal.Decimal(0)
                total_cotisations_impayees += prestation.solde
                if prestation.solde:
                    liste_finale_cotisations.append(prestation)

        context["liste_cotisations_prefacturation"] = liste_finale_cotisations

        # Création du texte de rappel des impayés
        liste_impayes = []
        texte_impayes = None
        if liste_factures_impayees:
            liste_impayes.append(_("1 facture à régler") if len(liste_factures_impayees) == 1 else _("%d factures à régler") % len(liste_factures_impayees))
        if liste_finale_periodes or liste_finale_cotisations:
            liste_impayes.append(_("des prestations à régler en avance"))
        if liste_impayes:
            texte_impayes = _("Il reste %s pour un total de") % utils_texte.Convert_liste_to_texte_virgules(liste_impayes) + " <strong>%s</strong>" % utils_texte.Formate_montant(total_factures_impayees + total_periodes_impayees + total_cotisations_impayees)
        context["texte_impayes"] = texte_impayes

        # Calcul du solde
        if context["parametres_portail"].get("facturation_afficher_solde_famille", False):
            total_prestations = Prestation.objects.values('famille_id').filter(famille=self.request.user.famille).aggregate(total=Sum("montant"))
            total_reglements = Reglement.objects.values('famille_id').filter(famille=self.request.user.famille).aggregate(total=Sum("montant"))
            total_du = total_prestations["total"] if total_prestations["total"] else decimal.Decimal(0)
            total_regle = total_reglements["total"] if total_reglements["total"] else decimal.Decimal(0)
            context["solde_famille"] = total_du - total_regle

        return context