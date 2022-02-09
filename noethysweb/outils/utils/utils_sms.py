# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, requests, json, datetime
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from core.models import SMS
from core.utils import utils_historique


def Envoyer_model_sms(idsms=None, request=None):
    # Stoppe l'envoi si mode démo activé
    if settings.MODE_DEMO:
        messages.add_message(request, messages.ERROR, "Vous ne pouvez pas envoyer de SMS en mode démo.")
        return

    # Importation du SMS à envoyer
    sms = SMS.objects.prefetch_related('destinataires').select_related("configuration_sms").get(pk=idsms)

    # Récupère la liste des destinataires
    condition = ~Q(resultat_envoi="ok") if "NON_ENVOYE" in sms.selection else Q()
    destinataires = sms.destinataires.filter(condition)

    # Sélection d'une quantité de SMS à envoyer
    if sms.selection.startswith("NON_ENVOYE_"):
        destinataires = destinataires[:int(sms.selection.replace("NON_ENVOYE_", ""))]

    # Envoi
    liste_envois_succes = []

    # Envoi avec MAILJET
    if sms.configuration_sms.moteur == "mailjet":

        # Préparation de l'envoi
        headers = {"Authorization": "Bearer {api_token}".format(api_token=sms.configuration_sms.token), "Content-Type": "application/json"}
        api_url = "https://api.mailjet.com/v4/sms-send"

        # Envoi des SMS
        texte = sms.texte.replace("\n", "")

        for destinataire in destinataires:
            numero = destinataire.mobile.replace(".", "")
            numero = "+33" + numero[1:]

            # Création du message JSON
            message_data = {"From": sms.configuration_sms.nom_exp, "To": numero, "Text": texte}
            reponse = requests.post(api_url, headers=headers, json=message_data)
            if reponse.ok:
                liste_envois_succes.append(destinataire)
                resultat_envoi = "ok"
            else:
                logger.debug("Erreur envoi SMS : %s" % reponse.text)
                dict_erreur = json.loads(reponse.text)
                resultat_envoi = dict_erreur["ErrorMessage"]

                if "API key authentication/authorization failure" in resultat_envoi:
                    messages.add_message(request, messages.ERROR, "Impossible de se connecter au serveur d'envoi : Le token semble erroné")
                    return

            # Mémorise le résultat de l'envoi dans la DB
            destinataire.date_envoi = datetime.datetime.now()
            destinataire.resultat_envoi = resultat_envoi
            destinataire.save()

            if reponse.ok:
                # Mémorise l'envoi dans l'historique
                utils_historique.Ajouter(titre="Envoi d'un SMS", detail=sms.objet, utilisateur=request.user if request else None, famille=destinataire.famille_id,
                                         individu=destinataire.individu_id, objet="SMS", idobjet=sms.pk, classe="SMS")

    # Enregistre le solde du compte prépayé
    if liste_envois_succes:
        sms.configuration_sms.solde -= len(liste_envois_succes)
        sms.configuration_sms.save()


def Envoyer_sms_test(request=None, dict_options={}):
    """ Pour tester une configuration SMS en envoyant un SMS de test """
    logger.debug("Envoi d'un SMS de test...")

    # Envoi avec MAILJET
    if dict_options["moteur"] == "mailjet":
        headers = {"Authorization": "Bearer {api_token}".format(api_token=dict_options["token"]), "Content-Type": "application/json"}
        numero = dict_options["numero_destination"].replace(".", "")
        message_data = {"From": dict_options["nom_exp"], "To": "+33" + numero[1:], "Text": "Ceci est un SMS de test."}
        reponse = requests.post("https://api.mailjet.com/v4/sms-send", headers=headers, json=message_data)
        if reponse.ok:
            return "Message envoyé avec succès."
        else:
            dict_erreur = json.loads(reponse.text)
            return dict_erreur["ErrorMessage"]

    return "Aucun moteur sélectionné"
