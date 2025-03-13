# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.http import JsonResponse
from django.shortcuts import render
from core.models import ModeleSMS, SMS, DestinataireSMS, Famille , Individu
from outils.forms.editeur_sms_express import Formulaire
from outils.utils import utils_sms


def Envoyer_sms(request):
    """ Envoi du SMS sur appel ajax """
    # Récupération des variables
    idsms = int(request.POST.get("idsms"))
    objet = request.POST.get("objet")
    texte = request.POST.get("texte")
    configuration_sms = request.POST.get("configuration_sms")
    destinataire = request.POST.get("destinataire")

    # Validations
    if not objet: return JsonResponse({"message": "Vous devez saisir un objet"}, status=401)
    if not texte: return JsonResponse({"message": "Vous devez saisir un texte"}, status=401)
    if not configuration_sms: return JsonResponse({"message": "Vous devez sélectionner une configuration SMS"}, status=401)
    if not destinataire: return JsonResponse({"message": "Vous devez sélectionner un destinataire"}, status=401)

    # Enregistrement des éventuelles modifications dans le SMS
    sms = SMS.objects.get(pk=idsms)
    sms.configuration_sms_id = configuration_sms
    sms.objet = objet
    sms.texte = texte
    sms.save()

    sms.destinataires.first().mobile = destinataire
    sms.destinataires.first().save()

    # Envoi du SMS
    liste_envois_succes = utils_sms.Envoyer_model_sms(idsms=sms.pk, request=request)
    if len(liste_envois_succes) == 1:
        return JsonResponse({"message": "Le SMS a été envoyé avec succès"})
    else:
        return JsonResponse({"message": "Le SMS n'a pas pu être envoyé"}, status=401)


def Get_view_editeur_sms(request):
    """ Renvoie l'éditeur de SMS dans un modal """
    # Récupère d'éventuelles données
    donnees = json.loads(request.POST.get("donnees"))

    # Création du SMS
    modele_sms = ModeleSMS.objects.filter(categorie=donnees["categorie"], defaut=True).first()
    sms = SMS.objects.create(
        objet=modele_sms.objet if modele_sms else "",
        texte=modele_sms.texte if modele_sms else "",
        configuration_sms=request.user.Get_configuration_sms_defaut(),
        selection="NON_ENVOYE",
        utilisateur=request.user,
    )

    if 'idfamille' in donnees:

        # Importation de la famille
        famille = Famille.objects.get(pk=donnees["idfamille"])
        # Création du destinataire
        destinataire = DestinataireSMS.objects.create(categorie="famille", famille=famille, mobile=famille.mobile, valeurs=json.dumps(donnees["champs"]))
        sms.destinataires.add(destinataire)

    else : #individu
        # Importation de l'individu
        individu = Individu.objects.get(pk=donnees["idindividu"])
        # Création du destinataire
        destinataire = DestinataireSMS.objects.create(categorie="individu", individu=individu, mobile=individu.mobile, valeurs=json.dumps(donnees["champs"]))
        sms.destinataires.add(destinataire)

    # Prépare le context
    context = {
        "page_titre": "Editeur de SMS",
        "form": Formulaire(instance=sms, request=request),
        "modeles": ModeleSMS.objects.filter(categorie=request.POST.get("categorie", donnees["categorie"])),
    }
    return render(request, 'outils/editeur_sms_express.html', context)