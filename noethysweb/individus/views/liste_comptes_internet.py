# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, time
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Max
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Mail, Utilisateur, Destinataire, ModeleEmail
from fiche_famille.utils import utils_internet


def Envoyer_email(request):
    time.sleep(1)

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
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Importation des comptes internet
    familles = Famille.objects.select_related("utilisateur").filter(pk__in=coches)

    # Recherche le dernier ID de la table Destinataires
    dernier_destinataire = Destinataire.objects.last()
    idmax = dernier_destinataire.pk if dernier_destinataire else 0

    # Création des destinataires et des documents joints
    logger.debug("Enregistrement des destinataires et documents joints...")
    liste_anomalies = []
    liste_ajouts = []
    for famille in familles:
        if famille.mail:
            valeurs = {
                "{NOM_FAMILLE}": famille.nom,
                "{IDENTIFIANT_INTERNET}": famille.internet_identifiant,
                "{MOTDEPASSE_INTERNET}": famille.internet_mdp,
                "{DATE_EXPIRATION_MOTDEPASSE}": famille.utilisateur.date_expiration_mdp.strftime("%d/%m/%Y") if famille.utilisateur.date_expiration_mdp else "",
                }
            liste_ajouts.append(Destinataire(categorie="famille", famille=famille, adresse=famille.mail, valeurs=json.dumps(valeurs)))
        else:
            liste_anomalies.append(famille.nom)

    if liste_ajouts:
        # Enregistre les destinataires
        Destinataire.objects.bulk_create(liste_ajouts)
        # Associe les destinataires au mail
        destinataires = Destinataire.objects.filter(pk__gt=idmax)
        ThroughModel = Mail.destinataires.through
        ThroughModel.objects.bulk_create([ThroughModel(mail_id=mail.pk, destinataire_id=destinataire.pk) for destinataire in destinataires])

    if liste_anomalies:
        texte_anomalies = "%d adresses mail manquantes : %s" % (len(liste_anomalies), ", ".join(liste_anomalies))
        messages.add_message(request, messages.ERROR, texte_anomalies)
        logger.debug(texte_anomalies)

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})


def Desactiver(request):
    time.sleep(1)

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
    time.sleep(1)

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
    time.sleep(1)

    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un compte internet dans la liste"}, status=401)

    # Reinitialisation des comptes dans la DB
    for famille in Famille.objects.select_related("utilisateur").all():
        if famille.pk in coches:
            internet_mdp, date_expiration_mdp = utils_internet.CreationMDP()
            famille.internet_mdp = internet_mdp
            if not famille.utilisateur:
                utilisateur = Utilisateur(username=famille.internet_identifiant, categorie="famille", force_reset_password=True, date_expiration_mdp=date_expiration_mdp)
                utilisateur.save()
                utilisateur.set_password(internet_mdp)
                utilisateur.save()
                famille.utilisateur = utilisateur
            else:
                famille.utilisateur.set_password(internet_mdp)
                famille.utilisateur.force_reset_password = True
                famille.utilisateur.date_expiration_mdp = date_expiration_mdp
                famille.utilisateur.save()
            famille.save()

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "%d mots de passe ont été réinitialisés avec succès" % len(coches))
    return JsonResponse({"url": reverse_lazy("liste_comptes_internet")})


def Reinitialiser_identifiant(request):
    time.sleep(1)

    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un compte internet dans la liste"}, status=401)

    # Reinitialisation des comptes dans la DB
    for famille in Famille.objects.select_related("utilisateur").all():
        if famille.pk in coches:
            internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=famille.pk)
            famille.internet_identifiant = internet_identifiant
            famille.utilisateur.username = internet_identifiant
            if not famille.utilisateur:
                utilisateur = Utilisateur(username=internet_identifiant, categorie="famille", force_reset_password=True)
                utilisateur.save()
                utilisateur.set_password(famille.internet_mdp)
                utilisateur.save()
                famille.utilisateur = utilisateur
            famille.save()
            famille.utilisateur.save()

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
        return Famille.objects.select_related("utilisateur").annotate(derniere_action=Max("historique__horodatage")).filter(self.Get_filtres("Q"))

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
        filtres = ["fgenerique:pk", "idfamille", "internet_actif", "internet_identifiant", "internet_mdp", "derniere_action"]
        check = columns.CheckBoxSelectColumn(label="")
        internet_actif = columns.TextColumn("Activation", sources=["internet_actif"], processor='Get_internet_actif')
        internet_identifiant = columns.TextColumn("Identifiant", sources=[], processor='Get_internet_identifiant')
        internet_mdp = columns.TextColumn("Mot de passe", sources=[], processor='Get_internet_mdp')
        date_expiration_mdp = columns.TextColumn("Expiration mdp", sources=["utilisateur__date_expiration_mdp"], processor=helpers.format_date("%d/%m/%Y %H:%M"))
        derniere_action = columns.TextColumn("Dernière action", sources=None, processor=helpers.format_date('%d/%m/%Y'))

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idfamille', 'nom', "internet_actif", "internet_identifiant", "internet_mdp", "date_expiration_mdp", "derniere_action"]
            ordering = ["nom"]

        def Get_internet_actif(self, instance, *args, **kwargs):
            return "<i class='fa fa-check margin-r-5 text-green'></i>" if instance.internet_actif else "<i class='fa fa-close margin-r-5 text-red'></i>"

        def Get_internet_identifiant(self, instance, *args, **kwargs):
            return instance.internet_identifiant

        def Get_internet_mdp(self, instance, *args, **kwargs):
            return "******" if instance.internet_mdp and instance.internet_mdp.startswith("custom") else instance.internet_mdp
