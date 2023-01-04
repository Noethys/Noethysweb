# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, time, re, datetime, mimetypes, json
logger = logging.getLogger(__name__)
from django.conf import settings
from django.core import mail as djangomail
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.contrib import messages
from email.mime.image import MIMEImage
from core.models import Mail
from core.utils import utils_dates, utils_historique, utils_texte


class Validation_adresse():
    """ Validation d'une adresse mail """
    def __init__(self):
        self.regex = re.compile(r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+")

    def Check(self, adresse=""):
        return re.search(self.regex, adresse)



# def Envoyer_rappel(destinataires, objet=None, html=None, pieces=[], document=None, remplacements={}):
#     """ Envoyer un email """
#
#     # Remplacement des mots-clés
#     for motcle, valeur in remplacements.items():
#         html = html.replace(motcle, valeur)
#
#     # Recherche les images intégrées
#     images = re.findall('src="([^"]+)"', html)
#
#     # Remplacement des liens des images intégrées
#     index = 0
#     for image in images:
#         html = html.replace(image, "cid:image%d" % index)
#         index += 1
#
#     # Création du message
#     message = EmailMultiAlternatives(subject=objet, body=utils_texte.Textify(html), from_email=settings.EMAIL_HOST_USER, to=destinataires)
#     message.mixed_subtype = 'related'
#     message.attach_alternative(html, "text/html")
#
#     # Création des images intégrées
#     index = 0
#     for image in images:
#         fp = open(settings.BASE_DIR + image, 'rb')
#         msg_img = MIMEImage(fp.read())
#         fp.close()
#         msg_img.add_header("Content-ID", "<image%d>" % index)
#         msg_img.add_header('Content-Disposition', 'inline', filename="image%d" % index)
#         message.attach(msg_img)
#         index += 1
#
#     # Création des pièces jointes
#     for piece in pieces:
#         message.attach(piece.name, piece.file.getvalue(), mimetypes.guess_type(piece.name)[0])
#
#     # Rattachement d'un fichier hébergé
#     if document:
#         message.attach_file(settings.MEDIA_ROOT + document)
#
#     # Envoi du mail
#     resultat = message.send(fail_silently=True)
#     return resultat



def Envoyer_model_mail(idmail=None, request=None):
    # Stoppe l'envoi si mode démo activé
    if settings.MODE_DEMO:
        messages.add_message(request, messages.ERROR, "Vous ne pouvez pas envoyer d'emails en mode démo.")
        return

    # Importation de l'email
    mail = Mail.objects.prefetch_related('destinataires', 'pieces_jointes').select_related("adresse_exp").get(pk=idmail)

    # Backend CONSOLE (Par défaut)
    backend = 'django.core.mail.backends.console.EmailBackend'
    backend_kwargs = {}

    # Backend SMTP
    if mail.adresse_exp.moteur == "smtp":
        backend = 'django.core.mail.backends.smtp.EmailBackend'
        backend_kwargs = {
            "host": mail.adresse_exp.hote, "port": mail.adresse_exp.port, "username": mail.adresse_exp.utilisateur,
            "password": mail.adresse_exp.motdepasse,
            "use_tls": mail.adresse_exp.use_tls, #"use_ssl": mail.adresse_exp.use_ssl,
        }

    # Backend MAILJET
    if mail.adresse_exp.moteur == "mailjet":
        backend = 'anymail.backends.mailjet.EmailBackend'
        backend_kwargs = {
            "api_key": mail.adresse_exp.Get_parametre("api_key"),
            "secret_key": mail.adresse_exp.Get_parametre("api_secret"),
        }

    # Recherche si envoi par lot activé
    nbre_mails_lot = mail.adresse_exp.Get_parametre("nbre_mails")
    duree_pause = mail.adresse_exp.Get_parametre("duree_pause")

    # Création de la connexion
    connection = djangomail.get_connection(backend=backend, fail_silently=False, **backend_kwargs)
    try:
        connection.open()
    except Exception as err:
        messages.add_message(request, messages.ERROR, "Connexion impossible au serveur de messagerie : %s" % err)
        return

    # Chargement de la signature de l'utilisateur
    signature = ""
    if "{UTILISATEUR_SIGNATURE}" in mail.html:
        if request.user.signature:
            signature = request.user.signature.html
        else:
            messages.add_message(request, messages.ERROR, "Vous avez demandé à intéger une signature d'emails alors que votre profil utilisateur n'est associé à aucune signature.")
            return

    # Valeurs de fusion par défaut
    valeurs_defaut = {
        "{UTILISATEUR_NOM_COMPLET}": request.user.get_full_name() if request else "",
        "{UTILISATEUR_NOM}": request.user.last_name if request else "",
        "{UTILISATEUR_PRENOM}": request.user.first_name if request else "",
        "{UTILISATEUR_SIGNATURE}": signature,
        "{DATE_LONGUE}": utils_dates.DateComplete(datetime.date.today()),
        "{DATE_COURTE}": utils_dates.ConvertDateToFR(datetime.date.today()),
    }

    # Récupère la liste des destinataires
    condition = ~Q(resultat_envoi="ok") if "NON_ENVOYE" in mail.selection else Q()
    destinataires = mail.destinataires.filter(condition)

    # Sélection d'une quantité de mails à envoyer
    if mail.selection.startswith("NON_ENVOYE_"):
        destinataires = destinataires[:int(mail.selection.replace("NON_ENVOYE_", ""))]

    # Envoi de chaque mail
    index_lot = 1
    liste_envois_succes = []
    for destinataire in destinataires:
        html = mail.html
        objet = mail.objet

        # Remplacement des mots-clés
        try:
            valeurs = json.loads(destinataire.valeurs)
        except:
            valeurs = {}
        valeurs.update(valeurs_defaut)
        for motcle, valeur in valeurs.items():
            html = html.replace(motcle, valeur)
            objet = objet.replace(motcle, valeur)

        # Recherche les images intégrées
        images = re.findall('src="([^"]+)"', html)

        # Remplacement des liens des images intégrées
        index = 0
        for image in images:
            html = html.replace(image, "cid:image%d" % index)
            index += 1

        # Création du message
        message = EmailMultiAlternatives(subject=objet, body=utils_texte.Textify(html), from_email=mail.adresse_exp.adresse, to=[destinataire.adresse], connection=connection)
        message.mixed_subtype = 'related'
        message.attach_alternative(html, "text/html")

        # Création des images intégrées
        index = 0
        for image in images:
            fp = open(settings.BASE_DIR + image, 'rb')
            msg_img = MIMEImage(fp.read())
            fp.close()
            msg_img.add_header("Content-ID", "<image%d>" % index)
            msg_img.add_header('Content-Disposition', 'inline', filename="image%d" % index)
            message.attach(msg_img)
            index += 1

        # Rattachement des pièces jointes
        for piece in mail.pieces_jointes.all():
            # message.attach(piece.name, piece.file.getvalue(), mimetypes.guess_type(piece.name)[0])
            message.attach_file(settings.MEDIA_ROOT + "/" + piece.fichier.name)

        # Rattachement des documents joints
        for document in destinataire.documents.all():
            message.attach_file(settings.MEDIA_ROOT + "/" + document.fichier.name)

        # Envoie le mail
        try:
            resultat = message.send()
        except Exception as err:
            resultat = err

        # Mémorise le résultat de l'envoi dans la DB
        destinataire.date_envoi = datetime.datetime.now()
        destinataire.resultat_envoi = "ok" if resultat == 1 else resultat
        destinataire.save()

        if resultat == 1:
            liste_envois_succes.append(destinataire)

            # Mémorise l'envoi dans l'historique
            utils_historique.Ajouter(titre="Envoi d'un email", detail=objet, utilisateur=request.user if request else None, famille=destinataire.famille_id,
                                     individu=destinataire.individu_id, objet="Email", idobjet=mail.pk, classe="Mail")

        # Pause si envoi par lot activé
        if nbre_mails_lot and len(destinataires) > 1:
            if index_lot >= int(nbre_mails_lot):
                time.sleep(int(duree_pause))
                index_lot = 0
            index_lot += 1

    connection.close()
    return liste_envois_succes



def Envoyer_mail_test(request=None, dict_options={}):
    """ Pour tester une adresse d'expédition en envoyant un mail de test """
    logger.debug("Envoi d'un email de test...")

    # Backend CONSOLE (Par défaut)
    backend = 'django.core.mail.backends.console.EmailBackend'
    backend_kwargs = {}

    # Backend SMTP
    if dict_options["moteur"] == "smtp":
        backend = 'django.core.mail.backends.smtp.EmailBackend'
        backend_kwargs = {"host": dict_options["hote"], "port": dict_options["port"], "username": dict_options["utilisateur"], "password": dict_options["motdepasse"], "use_tls": dict_options["use_tls"]}

    # Backend MAILJET
    if dict_options["moteur"] == "mailjet":
        backend = 'anymail.backends.mailjet.EmailBackend'
        backend_kwargs = {"api_key": dict_options["cle_api"], "secret_key": dict_options["cle_secrete"],}

    # Création de la connexion
    connection = djangomail.get_connection(backend=backend, fail_silently=False, **backend_kwargs)
    try:
        connection.open()
        logger.debug("Connexion au serveur de messagerie réussi...")
    except Exception as err:
        return "Connexion impossible au serveur de messagerie : %s" % err

    # Création du message
    message = EmailMultiAlternatives(subject="Test de messagerie", body="Ceci est un message test.", from_email=dict_options["adresse"], to=[dict_options["adresse_destination"]], connection=connection)

    # Envoie le mail
    try:
        resultat = message.send()
        logger.debug("Email envoyé...")
    except Exception as err:
        resultat = err

    connection.close()
    return "Message envoyé avec succès." if resultat else resultat
