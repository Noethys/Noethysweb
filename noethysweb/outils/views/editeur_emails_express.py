# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import JsonResponse
from core.models import ModeleEmail, Mail, PieceJointe, Destinataire, Famille, Individu, Contact, AdresseMail, DocumentJoint
from outils.utils import utils_email
from outils.forms.editeur_emails_express import Formulaire
from django.shortcuts import render
import json, re
from email.utils import parseaddr


def Envoyer_email(request):
    """ Envoi d'email sur appel ajax """
    # Récupération des variables
    idmail = int(request.POST.get("idmail"))
    objet = request.POST.get("objet")
    html = request.POST.get("html")
    adresse_exp = request.POST.get("adresse_exp")
    destinataires = request.POST.getlist("dest")

    # Validations
    if not objet: return JsonResponse({"message": "Vous devez saisir un objet"}, status=401)
    if not html: return JsonResponse({"message": "Vous devez saisir un texte"}, status=401)
    if not adresse_exp: return JsonResponse({"message": "Vous devez sélectionner une adresse d'expédition"}, status=401)

    # Enregistrement des éventuelles modifications dans le mail
    mail = Mail.objects.get(pk=idmail)
    mail.adresse_exp_id = adresse_exp
    mail.objet = objet
    mail.html = html
    mail.save()

    # Analyse des destinataires saisis
    liste_adresses, liste_anomalies = [], []
    validation = utils_email.Validation_adresse()
    for dest in destinataires:
        nom, adresse = parseaddr(dest)
        if validation.Check(adresse=adresse):
            liste_adresses.append(adresse)
        else:
            liste_anomalies.append(adresse)
    if liste_anomalies:
        return JsonResponse({"message": "Les adresses suivantes ne sont pas valides : %s" % ", ".join(liste_anomalies)}, status=401)
    if not liste_adresses:
        return JsonResponse({"message": "Vous devez sélectionner ou saisir au moins une adresse valide"}, status=401)

    destinataire_defaut = mail.destinataires.first()

    destinataire_defaut_found = False
    for adresse in liste_adresses:
        if destinataire_defaut and adresse != destinataire_defaut.adresse:
            destinataire = Destinataire.objects.create(categorie="saisie_libre", adresse=adresse, valeurs=destinataire_defaut.valeurs)
            for document in destinataire_defaut.documents.all():
                document_joint = DocumentJoint.objects.create(nom=document.nom, fichier=document.fichier)
                destinataire.documents.add(document_joint)
            mail.destinataires.add(destinataire)
        else:
            destinataire_defaut_found = True
    if not destinataire_defaut_found:
        destinataire_defaut.delete()

    liste_envois_succes = utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)
    if liste_envois_succes == False:
        return JsonResponse({"message": "L'email n'a pas pu être envoyé"}, status=401)
    liste_reussis = [destinataire.adresse for destinataire in liste_envois_succes]
    liste_echecs = [adresse for adresse in liste_adresses if adresse not in liste_reussis]
    if len(liste_reussis) == len(liste_adresses):
        return JsonResponse({"message": "Le mail a été envoyé avec succès à %d destinataire(s)" % len(liste_adresses)})
    if len(liste_reussis) == 0:
        return JsonResponse({"message": "L'email n'a pas pu être envoyé"}, status=401)
    return JsonResponse({"message": "Le mail a été envoyé avec succès à %s mais n'a pas pu être envoyé à %s" % (", ".join(liste_reussis), ", ".join(liste_echecs))}, status=401)



def Get_view_editeur_email(request):
    """ Renvoie l'éditeur d'emails dans un modal """
    # Récupère d'éventuelles données
    donnees = json.loads(request.POST.get("donnees"))
    # Création du mail
    modele_email = ModeleEmail.objects.filter(categorie=donnees["categorie"], defaut=True).first()
    mail = Mail.objects.create(
        categorie=donnees["categorie"],
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    if 'idfamille' in donnees:

        # Importation de la famille
        famille = Famille.objects.get(pk=donnees["idfamille"])
        # Création du destinataire et du document joint
        destinataire = Destinataire.objects.create(categorie="famille", famille=famille, adresse=famille.mail, valeurs=json.dumps(donnees["champs"]))
        if "nom_fichier" in donnees:
            document_joint = DocumentJoint.objects.create(nom=donnees["label_fichier"], fichier=donnees["nom_fichier"])
            destinataire.documents.add(document_joint)
        mail.destinataires.add(destinataire)

    else : #individu
        # Importation de l'individu
        individu = Individu.objects.get(pk=donnees["idindividu"])
        destinataire = Destinataire.objects.create(categorie="individu", individu=individu, adresse=individu.mail, valeurs=json.dumps(donnees["champs"]))
        if "nom_fichier" in donnees:
            document_joint = DocumentJoint.objects.create(nom=donnees["label_fichier"], fichier=donnees["nom_fichier"])
            destinataire.documents.add(document_joint)
        mail.destinataires.add(destinataire)

    # Prépare le context
    context = {
        "page_titre": "Editeur d'emails",
        "form": Formulaire(instance=mail, request=request),
        "modeles": ModeleEmail.objects.filter(categorie=request.POST.get("categorie", donnees["categorie"])),
    }
    return render(request, 'outils/editeur_emails_express.html', context)