# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from fiche_famille.utils import utils_internet
from core.models import Famille, Mail, DocumentJoint, Destinataire, AdresseMail, ModeleEmail
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Max
import json


def Envoyer_email(request):
    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un compte internet dans la liste"}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    modele_email = ModeleEmail.objects.filter(categorie="portail", defaut=True).first()
    mail = Mail.objects.create(
        categorie="portail",
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=AdresseMail.objects.filter(defaut=True).first(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Importation des comptes internet
    familles = Famille.objects.filter(pk__in=coches)

    # Création des destinataires et des documents joints
    logger.debug("Enregistrement des destinataires et documents joints...")
    liste_anomalies = []
    for famille in familles:
        if famille.mail:
            valeurs = {"NOM_FAMILLE": famille.nom, "IDENTIFIANT_INTERNET": famille.internet_identifiant, "MOTDEPASSE_INTERNET": famille.internet_mdp}
            destinataire = Destinataire.objects.create(categorie="famille", famille=famille, adresse=famille.mail, valeurs=json.dumps(valeurs))
            mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})


def Desactiver(request):
    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un compte internet dans la liste"}, status=401)

    # Désactivation des comptes dans la DB
    for famille in Famille.objects.all():
        if famille.pk in coches:
            famille.internet_actif = False
            famille.save()

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "%d comptes ont été désactivés avec succès" % len(coches))
    return JsonResponse({"url": reverse_lazy("liste_comptes_internet")})


def Activer(request):
    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un compte internet dans la liste"}, status=401)

    # Activation des comptes dans la DB
    for famille in Famille.objects.all():
        if famille.pk in coches:
            famille.internet_actif = True
            famille.save()

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "%d comptes ont été activés avec succès" % len(coches))
    return JsonResponse({"url": reverse_lazy("liste_comptes_internet")})


def Reinitialiser_mdp(request):
    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un compte internet dans la liste"}, status=401)

    # Reinitialisation des comptes dans la DB
    for famille in Famille.objects.all():
        if famille.pk in coches:
            famille.internet_mdp = utils_internet.CreationMDP()
            famille.save()

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "%d mots de passe ont été réinitialisés avec succès" % len(coches))
    return JsonResponse({"url": reverse_lazy("liste_comptes_internet")})


def Reinitialiser_identifiant(request):
    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un compte internet dans la liste"}, status=401)

    # Reinitialisation des comptes dans la DB
    for famille in Famille.objects.all():
        if famille.pk in coches:
            famille.internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=famille.pk)
            famille.save()

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "%d identifiants ont été réinitialisés avec succès" % len(coches))
    return JsonResponse({"url": reverse_lazy("liste_comptes_internet")})



class Page(crud.Page):
    model = Famille
    url_liste = "liste_comptes_internet"
    menu_code = "liste_comptes_internet"


class Liste(Page, crud.Liste):
    template_name = "individus/liste_comptes_internet.html"
    model = Famille

    def get_queryset(self):
        return Famille.objects.annotate(derniere_action=Max("historique__horodatage")).filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Comptes internet"
        context['box_titre'] = "Liste des comptes internet"
        context['box_introduction'] = "Vous pouvez ici consulter la liste des codes internet des familles. Il est également possible d'activer, désactiver, réinitialiser des comptes, ou d'envoyer des codes d'accès par Email. Cochez les comptes souhaités et cliquez sur le bouton d'action souhaité. La colonne Dernière action indique la date de la dernière action trouvée dans l'historique pour la famille. Cela vous permet d'identifier les familles qui ne fréquentent plus la structure."
        context['onglet_actif'] = "liste_comptes_internet"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fpresent:famille", "idfamille", 'nom', "internet_actif", "internet_identifiant", "internet_mdp", "derniere_action"]

        check = columns.CheckBoxSelectColumn(label="")
        internet_actif = columns.TextColumn("Activation", sources=["internet_actif"], processor='Get_internet_actif')
        internet_mdp = columns.TextColumn("Mot de passe", sources=[], processor='Get_internet_mdp')
        derniere_action = columns.TextColumn("Dernière action", sources=["derniere_action"], processor=helpers.format_date('%d/%m/%Y'))

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idfamille', 'nom', "internet_actif", "internet_identifiant", "internet_mdp", "derniere_action"]
            ordering = ["nom"]

        def Get_internet_actif(self, instance, *args, **kwargs):
            return "<i class='fa fa-check margin-r-5 text-green'></i>" if instance.internet_actif else "<i class='fa fa-close margin-r-5 text-red'></i>"

        def Get_internet_mdp(self, instance, *args, **kwargs):
            return "******" if instance.internet_mdp and instance.internet_mdp.startswith("custom") else instance.internet_mdp
