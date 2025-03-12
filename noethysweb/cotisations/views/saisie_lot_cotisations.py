# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from core.views import crud
from core.models import TypeCotisation, UniteCotisation, Famille, Rattachement, Prestation, Cotisation
from core.utils import utils_texte
from fiche_famille.forms.famille_cotisations import Formulaire_type_cotisation, Formulaire


def Appliquer(request):
    logger.debug("Saisie de cotisations par lot...")

    # Récupération du type de cotisation
    type_cotisation = TypeCotisation.objects.get(pk=request.POST.get("idtype_cotisation"))
    unite_cotisation = UniteCotisation.objects.get(pk=request.POST.get("idunite_cotisation"))

    # Récupération des options
    valeurs_form_options = json.loads(request.POST.get("form_options"))
    form = Formulaire(valeurs_form_options, request=request, idtype_cotisation=type_cotisation.pk, idunite_cotisation=unite_cotisation.pk)
    if not form.is_valid():
        max_errors = 1 if type_cotisation.type == "famille" else 2
        if len(form.errors.as_data().keys()) > max_errors:
            return JsonResponse({"erreur": "Veuillez renseigner correctement les paramètres"}, status=401)

    # Récupération des lignes cochées
    lignes_cochees = json.loads(request.POST.get("lignes_cochees"))
    if not lignes_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins un bénéficiaire dans la liste"}, status=401)
    if type_cotisation.type == "famille":
        liste_objets = Famille.objects.filter(pk__in=lignes_cochees)
    else:
        liste_objets = Rattachement.objects.select_related("individu", "famille").filter(pk__in=lignes_cochees)

    # Récupération des paramètres de la cotisation
    numero = form.cleaned_data["numero"]

    for objet in liste_objets:
        if type_cotisation.type == "famille":
            famille = objet
            individu = None
        else:
            famille = objet.famille
            individu = objet.individu

        # Création de la prestation
        prestation = None
        if form.cleaned_data["facturer"]:
            prestation = Prestation.objects.create(date=form.cleaned_data["date_facturation"], categorie="cotisation",
                                                   label=form.cleaned_data["label_prestation"], famille=famille,
                                                   montant_initial=form.cleaned_data["montant"], individu=individu,
                                                   montant=form.cleaned_data["montant"],
                                                   activite=form.cleaned_data["type_cotisation"].activite)

        # Création de la cotisation
        cotisation = Cotisation.objects.create(date_creation_carte=form.cleaned_data["date_creation_carte"],
            numero=numero, date_debut=form.cleaned_data["date_debut"], date_fin=form.cleaned_data["date_fin"],
            observations=form.cleaned_data["observations"], famille=famille, individu=individu, prestation=prestation,
            type_cotisation=type_cotisation, unite_cotisation=unite_cotisation)
        if form.cleaned_data["activites"]:
            cotisation.activites.set(form.cleaned_data["activites"])
        if numero:
            numero = utils_texte.Incrementer(numero)

    logger.debug("Saisie par lot des cotisations terminée.")
    return JsonResponse({"success": True})


class Page(crud.Page):
    template_name = "cotisations/saisie_lot_cotisations.html"
    url_liste = "saisie_lot_cotisations"
    menu_code = "saisie_lot_cotisations"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context["page_titre"] = "Saisir un lot d'adhésions"
        context["box_titre"] = "Sélection des paramètres"
        context["box_introduction"] = "Vous pouvez ici créer un lot d'adhésions familiales ou individuelles. Commencez par cocher les bénéficiaires dans la liste au bas de la page puis renseignez les paramètres des adhésions. Terminez en cliquant sur le bouton Générer."
        context["onglet_actif"] = "saisie_lot_cotisations"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["active_checkbox"] = True
        context["bouton_supprimer"] = False
        context["hauteur_table"] = "400px"
        context["form_options"] = Formulaire(request=self.request, idtype_cotisation=self.kwargs.get("idtype_cotisation", None), idunite_cotisation=self.kwargs.get("idunite_cotisation", None))
        context["idtype_cotisation"] = self.kwargs.get("idtype_cotisation", None)
        context["idunite_cotisation"] = self.kwargs.get("idunite_cotisation", None)
        context["afficher_menu_brothers"] = True
        return context


class Selection_type_cotisation(Page, crud.Ajouter):
    form_class = Formulaire_type_cotisation
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_type_cotisation, self).get_context_data(**kwargs)
        context["box_introduction"] = "Vous devez sélectionner le type et l'unité d'adhésion à créer."
        context["page_titre"] = "Saisir un lot d'adhésions"
        context["box_titre"] = "Saisir un lot d'adhésions"
        return context

    def post(self, request, **kwargs):
        idtype_cotisation = request.POST.get("type_cotisation")
        idunite_cotisation = request.POST.get("unite_cotisation")
        affichage_beneficiaires = request.POST.get("affichage_beneficiaires")
        type_cotisation = TypeCotisation.objects.get(pk=idtype_cotisation)
        kwargs = {"idtype_cotisation": idtype_cotisation, "idunite_cotisation": idunite_cotisation, "affichage_beneficiaires": affichage_beneficiaires}
        return HttpResponseRedirect(reverse_lazy("saisie_lot_cotisations_%ss" % type_cotisation.type, kwargs=kwargs))
