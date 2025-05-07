# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, time
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render
from django.template import Template, RequestContext
from django.db.models import Q
from django.contrib import messages
from core.models import Activite, Quotient, Famille, Inscription, TypeQuotient, Mail, Destinataire
from core.views.base import CustomView
from core.utils import utils_dates
from individus.forms.importer_quotients import Formulaire, Formulaire_parametres_enregistrer
from individus.utils import utils_api_particulier
from fiche_famille.forms.famille_quotients import Formulaire as Formulaire_quotient
from fiche_famille.views.famille_quotients import Validation_form


def Rechercher(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        html = "{% load crispy_forms_tags %} {% crispy form %}<script>init_page();</script>"
        data = Template(html).render(RequestContext(request, {"form": form}))
        liste_messages_erreurs = [erreur[0].message for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"html": data, "erreur": "Veuillez corriger les erreurs suivantes : %s." % ", ".join(liste_messages_erreurs)}, status=401)

    parametres = form.cleaned_data

    # Si une sélection de familles uniquement
    if parametres["familles"] == "SELECTION":
        param_activites = json.loads(parametres["activites"])
        if param_activites["type"] == "groupes_activites":
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
        presents = utils_dates.ConvertDateRangePicker(parametres["presents"]) if parametres["presents"] else None

        # Importation des familles
        conditions = Q(activite__in=liste_activites)
        if presents:
            conditions &= Q(consommation__date__gte=presents[0], consommation__date__lte=presents[1])
        liste_familles_temp = []
        for inscription in Inscription.objects.select_related("famille").filter(conditions).distinct():
            if inscription.famille not in liste_familles_temp:
                liste_familles_temp.append(inscription.famille)

    # Si toutes les familles
    if parametres["familles"] == "TOUTES":
        liste_familles_temp = Famille.objects.filter(etat__isnull=True)

    # Importation des quotients
    dict_quotients_actuels = {quotient.famille_id: quotient for quotient in Quotient.objects.filter(date_debut__lte=parametres["date"], date_fin__gte=parametres["date"], famille__in=liste_familles_temp).order_by("date_fin")}
    dict_quotients_precedents = {quotient.famille_id: quotient for quotient in Quotient.objects.filter(date_fin__lte=parametres["date"], famille__in=liste_familles_temp).order_by("date_fin")}

    # Intialisation de l'API
    api = utils_api_particulier.Api_particulier(request=request)
    if api.erreurs_generales:
        return JsonResponse({"html": api.Get_html_erreurs(), "erreur": "erreurs !"}, status=401)

    liste_familles = []
    for famille in liste_familles_temp:
        quotient_actuel = dict_quotients_actuels.get(famille.pk)
        if parametres["filtre_quotients"] == "TOUTES" or (parametres["filtre_quotients"] == "AVEC_QF" and quotient_actuel) or (parametres["filtre_quotients"] == "SANS_QF" and not quotient_actuel):
            famille.quotient_actuel = quotient_actuel
            famille.quotient_precedent = dict_quotients_precedents.get(famille.pk)
            famille.resultat = api.Consulter_famille(famille=famille)
            famille.erreurs = api.Get_html_erreurs_famille(idfamille=famille.pk)
            liste_familles.append(famille)

    if api.erreurs_generales:
        html = "{% load crispy_forms_tags %} {% crispy form %}<script>init_page();</script>"
        data = Template(html).render(RequestContext(request, {"form": form}))
        return JsonResponse({"html": data, "erreur": "Veuillez corriger les erreurs suivantes : %s." % ", ".join(api.erreurs_generales)}, status=401)

    form_enregistrer = Formulaire_parametres_enregistrer()
    return render(request, "individus/importer_quotients_selection.html", {"familles": liste_familles, "form_enregistrer": form_enregistrer})


def Enregistrer(request):
    time.sleep(1)

    # Paramètres du formulaire
    form = Formulaire_parametres_enregistrer(json.loads(request.POST.get("form_parametres")), request=request)
    if not form.is_valid():
        return JsonResponse({"html": "ERREUR!", "erreur": "Veuillez renseigner les paramètres manquants"}, status=401)
    parametres = form.cleaned_data

    # Récupération des familles cochées
    liste_familles = json.loads(request.POST.get("liste_familles"))

    # Importation des types de quotients
    types_quotients = TypeQuotient.objects.all()

    def Get_type_quotient(choix_fournisseur=""):
        for type_quotient in types_quotients:
            if (choix_fournisseur == "CNAF" and "CAF" in type_quotient.nom) or (choix_fournisseur == "MSA" and "MSA" in type_quotient.nom):
                return type_quotient
            return None

    dict_resultats = {}
    for dict_temp in liste_familles:
        famille = Famille.objects.get(pk=dict_temp["idfamille"])
        data = {
            "famille": famille.pk,
            "date_debut": str(parametres["date_debut"]),
            "date_fin": str(parametres["date_fin"]),
            "quotient": dict_temp["valeur"],
            "type_quotient": Get_type_quotient(dict_temp["fournisseur"]).pk
        }

        form = Formulaire_quotient(data=data, idfamille=famille.pk)
        if not form.is_valid():
            liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
            dict_resultats[famille] = liste_erreurs
            continue

        # Validation et recalcul des prestations si besoins
        resultat, form = Validation_form(form, request=request, idfamille=famille.pk, verbe_action="Ajouter")
        if not resultat:
            liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
            dict_resultats[famille] = liste_erreurs
            continue

        dict_resultats[famille] = True

    return render(request, "individus/importer_quotients_resultats.html", {"dict_resultats": dict_resultats})


def Envoyer_emails(request):
    time.sleep(1)

    # Récupération des familles cochées
    liste_familles = json.loads(request.POST.get("liste_familles"))
    if not liste_familles:
        return JsonResponse({"erreur": "Veuillez cocher au moins une ligne dans la liste"}, status=401)

    # Création du mail
    logger.debug("Création d'un nouveau mail...")
    mail = Mail.objects.create(
        categorie="saisie_libre",
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    # Importation des familles
    dict_familles = {famille.pk: famille for famille in Famille.objects.filter(pk__in=liste_familles)}

    # Création des destinataires
    logger.debug("Enregistrement des destinataires...")
    liste_anomalies = []
    for idfamille in liste_familles:
        famille = dict_familles[idfamille]
        if famille.mail:
            destinataire = Destinataire.objects.create(categorie="famille", famille=famille, adresse=famille.mail)
            mail.destinataires.add(destinataire)
        else:
            liste_anomalies.append(famille.nom)

    if liste_anomalies:
        messages.add_message(request, messages.ERROR, "Adresses mail manquantes : %s" % ", ".join(liste_anomalies))

    # Création de l'URL pour ouvrir l'éditeur d'emails
    logger.debug("Redirection vers l'éditeur d'emails...")
    url = reverse_lazy("editeur_emails", kwargs={'pk': mail.pk})
    return JsonResponse({"url": url})


class View(CustomView, TemplateView):
    menu_code = "importer_quotients"
    template_name = "individus/importer_quotients.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Importer des quotients"
        context["box_titre"] = "Importer des quotients depuis l'API Particulier"
        context["box_introduction"] = "Veuillez renseigner les paramètres de sélection des familles et cliquez sur le bouton Rechercher."
        context["form"] = kwargs.get("form", Formulaire(request=self.request))
        return context
