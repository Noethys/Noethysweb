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
from core.utils import utils_historique, utils_dates


def Envoyer_model_sms(idsms=None, request=None):
    # Stoppe l'envoi si mode démo activé
    if settings.MODE_DEMO:
        messages.add_message(request, messages.ERROR, "Vous ne pouvez pas envoyer de SMS en mode démo.")
        return

    # Importation du SMS à envoyer
    sms = SMS.objects.prefetch_related('destinataires').select_related("configuration_sms").get(pk=idsms)

    # Valeurs de fusion par défaut
    valeurs_defaut = {
        "{UTILISATEUR_NOM_COMPLET}": request.user.get_full_name() if request else "",
        "{UTILISATEUR_NOM}": request.user.last_name if request else "",
        "{UTILISATEUR_PRENOM}": request.user.first_name if request else "",
        "{DATE_LONGUE}": utils_dates.DateComplete(datetime.date.today()),
        "{DATE_COURTE}": utils_dates.ConvertDateToFR(datetime.date.today()),
    }

    # Récupère la liste des destinataires
    condition = ~Q(resultat_envoi="ok") if "NON_ENVOYE" in sms.selection else Q()
    destinataires = sms.destinataires.filter(condition)

    # Sélection d'une quantité de SMS à envoyer
    if sms.selection.startswith("NON_ENVOYE_"):
        destinataires = destinataires[:int(sms.selection.replace("NON_ENVOYE_", ""))]

    # Envoi
    liste_envois_succes = []

    # Envoi des SMS
    for destinataire in destinataires:
        texte = sms.texte.replace("\n", "")
        numero = destinataire.mobile.replace(".", "")
        numero = "+33" + numero[1:]
        resultat_envoi = None

        # Remplacement des mots-clés
        try:
            valeurs = json.loads(destinataire.valeurs)
        except:
            valeurs = {}
        valeurs.update(valeurs_defaut)
        for motcle, valeur in valeurs.items():
            texte = texte.replace(motcle, valeur)

        # Envoi avec MAILJET
        if sms.configuration_sms.moteur == "mailjet":
            headers = {"Authorization": "Bearer {api_token}".format(api_token=sms.configuration_sms.token), "Content-Type": "application/json"}
            reponse = requests.post("https://api.mailjet.com/v4/sms-send", headers=headers, json={"From": sms.configuration_sms.nom_exp, "To": numero, "Text": texte})
            if reponse.ok:
                liste_envois_succes.append(destinataire)
                resultat_envoi = "ok"
            else:
                logger.debug("Erreur envoi SMS : %s" % reponse.text)
                dict_erreur = json.loads(reponse.text)
                resultat_envoi = dict_erreur["ErrorMessage"]
                if "API key authentication/authorization failure" in resultat_envoi:
                    messages.add_message(request, messages.ERROR, "Impossible de se connecter au serveur d'envoi : Le token semble erroné")
                    return []

        # Envoi avec OVH
        if sms.configuration_sms.moteur == "ovh":
            params = {"account": sms.configuration_sms.nom_compte, "login": sms.configuration_sms.identifiant, "password": sms.configuration_sms.motdepasse,
                      "from": sms.configuration_sms.nom_exp, "to": numero, "message": texte, "noStop": 1, "contentType": "text/json"}
            r = requests.get("https://www.ovh.com/cgi-bin/sms/http2sms.cgi", params=params)
            reponse = r.json()
            if reponse["status"] == 100:
                liste_envois_succes.append(destinataire)
                resultat_envoi = "ok"
            else:
                resultat_envoi = reponse["message"]

        # Envoi avec BREVO
        if sms.configuration_sms.moteur == "brevo":
            headers = {"accept": "application/json", "api-key": sms.configuration_sms.token, "Content-Type": "application/json"}
            data = {"sender": sms.configuration_sms.nom_exp, "recipient": numero, "content": texte, "type": "transactional"}
            reponse = requests.post("https://api.brevo.com/v3/transactionalSMS/sms", headers=headers, json=data)
            dict_reponse = reponse.json()
            if reponse.status_code == 201:
                liste_envois_succes.append(destinataire)
                resultat_envoi = "ok"
            else:
                resultat_envoi = "%s : %s" % (dict_reponse["code"], dict_reponse["message"])
                logger.debug("Erreur envoi SMS : %s" % resultat_envoi)

        # Mémorise le résultat de l'envoi dans la DB
        destinataire.date_envoi = datetime.datetime.now()
        destinataire.resultat_envoi = resultat_envoi
        destinataire.save()

        if resultat_envoi == "ok":
            # Mémorise l'envoi dans l'historique
            utils_historique.Ajouter(titre="Envoi d'un SMS", detail=sms.objet, utilisateur=request.user if request else None, famille=destinataire.famille_id,
                                     individu=destinataire.individu_id, collaborateur=destinataire.collaborateur_id, objet="SMS", idobjet=sms.pk, classe="SMS")

    # Enregistre le solde du compte prépayé
    if liste_envois_succes:
        sms.configuration_sms.solde -= len(liste_envois_succes)
        sms.configuration_sms.save()

    return liste_envois_succes


def Envoyer_sms_test(request=None, dict_options={}):
    """ Pour tester une configuration SMS en envoyant un SMS de test """
    logger.debug("Envoi d'un SMS de test...")

    # Préparation du numéro du destinataire de test
    numero = dict_options["numero_destination"].replace(".", "")

    # Envoi avec MAILJET
    if dict_options["moteur"] == "mailjet":
        headers = {"Authorization": "Bearer {api_token}".format(api_token=dict_options["token"]), "Content-Type": "application/json"}
        message_data = {"From": dict_options["nom_exp"], "To": "+33" + numero[1:], "Text": "Ceci est un SMS de test."}
        reponse = requests.post("https://api.mailjet.com/v4/sms-send", headers=headers, json=message_data)
        if reponse.ok:
            return "Message envoyé avec succès."
        else:
            dict_erreur = json.loads(reponse.text)
            return dict_erreur["ErrorMessage"]

    # Envoi avec OVH
    if dict_options["moteur"] == "ovh":
        params = {"account": dict_options["nom_compte"], "login": dict_options["identifiant"], "password": dict_options["motdepasse"],
                  "from": dict_options["nom_exp"], "to": "+33" + numero[1:], "message": "Ceci est un SMS de test", "noStop": 1, "contentType": "text/json"}
        r = requests.get("https://www.ovh.com/cgi-bin/sms/http2sms.cgi", params=params)
        reponse = r.json()
        if reponse["status"] == 100:
            credit_restant = int(float(reponse["creditLeft"]))
            return "Message envoyé avec succès. Crédit restant : %d SMS." % credit_restant
        else:
            return reponse["message"]

    # Envoi avec Brevo
    if dict_options["moteur"] == "brevo":
        headers = {"accept": "application/json", "api-key": dict_options["token"], "Content-Type": "application/json"}
        data = {"sender": dict_options["nom_exp"], "recipient": "+33" + numero[1:], "content": "Ceci est un SMS de test", "type": "transactional"}
        reponse = requests.post("https://api.brevo.com/v3/transactionalSMS/sms", headers=headers, json=data)
        dict_reponse = reponse.json()
        if reponse.status_code == 201:
            return "Message envoyé avec succès."
        else:
            return "%s : %s" % (dict_reponse["code"], dict_reponse["message"])

    return "Aucun moteur sélectionné"
