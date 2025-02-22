# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.shortcuts import render
from django.template import Template, RequestContext
from core.models import Activite, Facture, Prestation, LotFactures, FiltreListe, ModeleImpression, PrefixeFacture
from core.views.base import CustomView
from core.utils import utils_dates, utils_parametres
from facturation.utils import utils_facturation, utils_impression_facture
from facturation.forms.factures_generation import Formulaire, Calc_prochain_numero


def Get_prochain_numero(request):
    """ Renvoie le prochain numéro de facture """
    idprefixe = request.POST.get("idprefixe", None)
    if idprefixe:
        prefixe = PrefixeFacture.objects.get(pk=idprefixe)
    else:
        prefixe = None
    numero = Calc_prochain_numero(prefixe)
    return JsonResponse({"numero": numero})


def Modifier_lot_factures(request):
    action = request.POST.get("action")
    idlot = request.POST.get("id")
    nom = request.POST.get("valeur")
    donnees_extra = json.loads(request.POST.get("donnees_extra"))

    # Ajouter un lot
    if action == "ajouter":
        lot = LotFactures.objects.create(nom=nom)
        return JsonResponse({"action": action, "id": lot.pk, "valeur": lot.nom})

    # Modifier un lot
    if action == "modifier":
        lot = LotFactures.objects.get(idlot=int(idlot))
        lot.nom = nom
        lot.save()
        return JsonResponse({"action": action, "id": lot.pk, "valeur": lot.nom})

    # Supprimer un lot
    if action == "supprimer":
        try:
            lot = LotFactures.objects.get(idlot=int(idlot))
            lot.delete()
            return JsonResponse({"action": action, "id": int(idlot)})
        except:
            return JsonResponse({"erreur": "Vous ne pouvez pas supprimer cette donnée"}, status=401)

    return JsonResponse({"erreur": "Erreur !"}, status=401)


def Previsualisation_pdf(request):
    # Récupération des variables
    idfamille = int(request.POST.get("idfamille")) or None
    form = Formulaire(request.POST, request=request)
    form.is_valid()

    # Recherche des données des factures
    liste_factures = Get_factures(form.cleaned_data, IDfamille=idfamille)

    # Récupération du modèle d'impression par défaut
    modele_impression = ModeleImpression.objects.filter(categorie="facture", defaut=True).first()
    if not modele_impression:
        return JsonResponse({"erreur": "Vous devez au préalable créer un modèle d'impression par défaut depuis le menu Paramétrage > Modèles d'impression"}, status=401)
    dict_options = json.loads(modele_impression.options)

    # Génération du PDF
    impression = utils_impression_facture.Impression(dict_donnees={item["idfamille"]: item for item in liste_factures}, dict_options=dict_options, IDmodele=modele_impression.modele_document_id)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})


def Get_factures(data={}, IDfamille=None):
    # Période
    date_debut = utils_dates.ConvertDateENGtoDate(data["periode"].split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(data["periode"].split(";")[1])

    # Sélection familles
    if not IDfamille and data["selection_familles"] == "FAMILLE":
        IDfamille = data["famille"].pk

    # Activités
    data["activites"] = json.loads(data["activites"])
    if data["activites"]["type"] == "groupes_activites":
        liste_activites = [activite.pk for activite in Activite.objects.filter(groupes_activites__in=data["activites"]["ids"])]
    else:
        liste_activites = data["activites"]["ids"]

    # Calcul des factures
    facturation = utils_facturation.Facturation()
    dict_factures = facturation.GetDonnees(liste_activites=liste_activites, date_debut=date_debut, date_fin=date_fin, date_edition=data["date_emission"],
                                           date_echeance=data["date_echeance"], categories_prestations=data["categories"], IDfamille=IDfamille,
                                           date_anterieure=data["prestations_anterieures"], inclure_cotisations_si_conso=data["inclure_cotisations_si_conso"])
    liste_factures = facturation.GetListeTriee(dict_factures)
    return liste_factures



def Recherche_factures(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        html = "{% load crispy_forms_tags %} {% crispy form %} {% include 'core/messages.html' %}<script>init_page();</script>"
        data = Template(html).render(RequestContext(request, {"form": form}))
        liste_messages_erreurs = [erreur[0].message for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"html": data, "erreur": "Veuillez corriger les erreurs suivantes : %s." % ", ".join(liste_messages_erreurs)}, status=401)

    # Mémorisation de la date prestations antérieures
    prestations_anterieures = form.cleaned_data.get("prestations_anterieures")
    utils_parametres.Set(nom="prestations_anterieures", categorie="generation_factures", utilisateur=request.user, valeur=str(prestations_anterieures) if prestations_anterieures else None)

    # Recherche des factures à générer
    liste_factures = Get_factures(form.cleaned_data)
    montant_minimum = utils_parametres.Get(nom="montant_minimum", categorie="generation_factures", utilisateur=request.user, valeur=0.0)
    return render(request, "facturation/factures_generation_selection.html", {"factures": liste_factures, "montant_minimum": montant_minimum})



def Generation_factures(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"html": "ERREUR!", "erreur": "Veuillez renseigner les paramètres manquants"}, status=401)

    # Mémorisation du montant minimum à facturer
    montant_minimum = request.POST.get("montant_minimum")
    utils_parametres.Set(nom="montant_minimum", categorie="generation_factures", utilisateur=request.user, valeur=montant_minimum if montant_minimum else None)

    liste_factures_cochees = json.loads(request.POST.get("liste_factures_json"))
    if not liste_factures_cochees:
        return JsonResponse({"html": "ERREUR!", "erreur": "Vous devez cocher au moins une facture dans la liste !"}, status=401)

    # Recherche des factures à générer
    liste_factures = Get_factures(form.cleaned_data)

    # Recherche le prochain numéro de facture
    numero = int(form.cleaned_data["prochain_numero"])

    # Recherche des régies
    dict_regies = {activite.pk: activite.regie for activite in Activite.objects.select_related("regie").filter(regie__isnull=False)}

    liste_factures_generees = []
    liste_id_factures = []
    dict_reports = {}
    for dict_facture in liste_factures:
        if dict_facture["IDfamille"] in liste_factures_cochees:
            # Recherche de la régie associée
            regie = None
            if dict_facture["liste_activites"]:
                regie = dict_regies.get(dict_facture["liste_activites"][0], None)

            # Enregistrement de la facture
            facture = Facture.objects.create(
                prefixe=form.cleaned_data["prefixe"],
                numero=numero,
                famille_id=dict_facture["IDfamille"],
                date_edition=form.cleaned_data["date_emission"],
                date_echeance=form.cleaned_data["date_echeance"],
                activites=";".join([str(x) for x in dict_facture["liste_activites"]])[:200],
                individus=";".join([str(x) for x in dict_facture["individus"].keys()]),
                date_debut=form.cleaned_data["periode"].split(";")[0],
                date_fin=form.cleaned_data["periode"].split(";")[1],
                total=dict_facture["total"],
                regle=dict_facture["ventilation"],
                solde=dict_facture["solde"],
                solde_actuel=dict_facture["solde"],
                lot=form.cleaned_data["lot_factures"],
                prestations=";".join(form.cleaned_data["categories"]),
                regie=regie,
                date_limite_paiement=form.cleaned_data["date_limite_paiement"],
                observations=form.cleaned_data["observations"],
            )
            liste_factures_generees.append(facture)
            liste_id_factures.append(facture.pk)
            dict_reports[facture.pk] = {
                "total_reports": dict_facture["total_reports"],
                "solde_avec_reports": dict_facture["solde_avec_reports"],
            }
            numero += 1

            # Insertion du IDfacture dans les prestations
            liste_prestations_modifiees = []
            for prestation in dict_facture["listePrestations"]:
                prestation.facture = facture
                liste_prestations_modifiees.append(prestation)
            Prestation.objects.bulk_update(liste_prestations_modifiees, ["facture"])

    # Importation des factures générées
    id_min, id_max = min(liste_id_factures), max(liste_id_factures)
    factures = Facture.objects.select_related('famille').filter(pk__gte=id_min, pk__lte=id_max).order_by("idfacture")

    # Intégration des impayés dans les résultats
    for facture in factures:
        if facture.pk in dict_reports:
            facture.total_reports = dict_reports[facture.pk]["total_reports"]
            facture.solde_avec_reports = dict_reports[facture.pk]["solde_avec_reports"]

    nbre_factures_email = len([facture for facture in factures if facture.famille.email_factures])
    nbre_factures_impression = len(factures) - nbre_factures_email

    # Enregistre le filtre pour l'export vers le Trésor Public
    FiltreListe.objects.filter(nom="facturation.views.lots_pes_factures", utilisateur=request.user).delete()
    parametres = """{"champ": "idfacture", "criteres": ["%d", "%d"], "condition": "COMPRIS", "label_filtre": "Facture : Dernières factures générées"}""" % (id_min, id_max)
    FiltreListe.objects.create(nom="facturation.views.lots_pes_factures", parametres=parametres, utilisateur=request.user)

    # Enregistre le filtre pour l'impression
    FiltreListe.objects.filter(nom="facturation.views.factures_impression", utilisateur=request.user).delete()
    parametres = """{"champ": "idfacture", "criteres": ["%d", "%d"], "condition": "COMPRIS", "label_filtre": "Facture : Dernières factures générées"}""" % (id_min, id_max)
    FiltreListe.objects.create(nom="facturation.views.factures_impression", parametres=parametres, utilisateur=request.user)
    parametres = """{"champ": "famille__email_factures", "criteres": [], "condition": "FAUX", "label_filtre": "Famille : Activation de l'envoi des factures par Email est faux"}"""
    FiltreListe.objects.create(nom="facturation.views.factures_impression", parametres=parametres, utilisateur=request.user)

    # Enregistre le filtre pour l'envoi par email
    FiltreListe.objects.filter(nom="facturation.views.factures_email", utilisateur=request.user).delete()
    parametres = """{"champ": "idfacture", "criteres": ["%d", "%d"], "condition": "COMPRIS", "label_filtre": "Facture : Dernières factures générées"}""" % (id_min, id_max)
    FiltreListe.objects.create(nom="facturation.views.factures_email", parametres=parametres, utilisateur=request.user)
    parametres = """{"champ": "famille__email_factures", "criteres": [], "condition": "VRAI", "label_filtre": "Famille : Activation de l'envoi des factures par Email est vrai"}"""
    FiltreListe.objects.create(nom="facturation.views.factures_email", parametres=parametres, utilisateur=request.user)

    return render(request, "facturation/factures_generation_actions.html", {"factures": factures, "nbre_factures_email": nbre_factures_email, "nbre_factures_impression": nbre_factures_impression})




class View(CustomView, TemplateView):
    menu_code = "factures_generation"
    template_name = "facturation/factures_generation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Génération des factures"
        context['box_titre'] = "Générer un lot de factures"
        context['box_introduction'] = "Veuillez renseigner les paramètres de sélection des factures à générer et cliquez sur le bouton Rechercher."
        idfamille = kwargs.get("idfamille", None)
        context['form'] = kwargs.get("form", Formulaire(request=self.request, idfamille=idfamille))
        return context

