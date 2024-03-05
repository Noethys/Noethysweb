# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime, logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Inscription, Consommation, Ouverture
from core.utils import utils_dates
from individus.forms.inscriptions_modifier import Formulaire_activite, Formulaire_options


def Appliquer(request):
    logger.debug("Modifier les inscriptions par lot...")

    # Récupération des inscriptions cochées
    inscriptions_cochees = json.loads(request.POST.get("inscriptions_cochees"))
    if not inscriptions_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une inscription à modifier dans la liste"}, status=401)
    inscriptions = Inscription.objects.filter(pk__in=inscriptions_cochees)

    # Récupération des options
    valeurs_form_options = json.loads(request.POST.get("form_options"))
    form = Formulaire_options(valeurs_form_options, idactivite=request.POST.get("idactivite"))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez renseigner correctement les paramètres"}, status=401)

    # On vérifie qu'il n'existe pas de consommations associées en dehors de la période de la réservation
    if form.cleaned_data["date_fin"]:
        nbre_conso = Consommation.objects.filter(Q(inscription__in=inscriptions) & Q(date__gt=form.cleaned_data["date_fin"])).count()
        if nbre_conso:
            return JsonResponse({"erreur": "Modification impossible : %d consommations existent après la période d'inscription sélectionnée" % nbre_conso}, status=401)

    if form.cleaned_data["date_debut"]:
        nbre_conso = Consommation.objects.filter(Q(inscription__in=inscriptions) & Q(date__lte=form.cleaned_data["date_debut"])).count()
        if nbre_conso:
            return JsonResponse({"erreur": "Modification impossible : %d consommations existent avant la période d'inscription sélectionnée" % nbre_conso}, status=401)

    # Modification de la date de début
    if form.cleaned_data["modifier_date_debut"]:
        logger.debug("Changement de date de début pour %d inscriptions..." % len(inscriptions))
        for inscription in inscriptions:
            inscription.date_debut = form.cleaned_data["date_debut"]
        Inscription.objects.bulk_update(inscriptions, ["date_debut"], batch_size=50)

    # Modification de la date de fin
    if form.cleaned_data["modifier_date_fin"]:
        logger.debug("Changement de date de fin pour %d inscriptions..." % len(inscriptions))
        for inscription in inscriptions:
            inscription.date_fin = form.cleaned_data["date_fin"]
        Inscription.objects.bulk_update(inscriptions, ["date_fin"], batch_size=50)

    # Modification du groupe
    if form.cleaned_data["modifier_groupe"]:
        logger.debug("Changement de groupe pour %d inscriptions..." % len(inscriptions))
        for inscription in inscriptions:
            inscription.groupe = form.cleaned_data["groupe"]
        Inscription.objects.bulk_update(inscriptions, ["groupe"], batch_size=50)

    # Modification de la catégorie de tarif
    if form.cleaned_data["modifier_categorie_tarif"]:
        logger.debug("Changement de catégorie de tarif pour %d inscriptions..." % len(inscriptions))
        for inscription in inscriptions:
            inscription.categorie_tarif = form.cleaned_data["categorie_tarif"]
        Inscription.objects.bulk_update(inscriptions, ["categorie_tarif"], batch_size=50)

    # Importation des consommations existantes
    consommations = []
    if form.cleaned_data["action_conso"] in ("MODIFIER_TOUT", "MODIFIER_AUJOURDHUI", "MODIFIER_DATE"):
        conditions = Q(inscription__in=inscriptions)
        if form.cleaned_data["action_conso"] == "MODIFIER_AUJOURDHUI":
            conditions &= Q(date__gte=datetime.date.today())
        if form.cleaned_data["action_conso"] == "MODIFIER_DATE":
            conditions &= Q(date__gte=form.cleaned_data["date_application_conso"])
        consommations = Consommation.objects.filter(conditions)

    # Changement du groupe
    if form.cleaned_data["modifier_groupe"] and consommations:
        # Vérifie que les unités et dates souhaitées sont ouvertes sur le nouveau groupe
        ouvertures = [(ouverture.date, ouverture.unite_id) for ouverture in Ouverture.objects.filter(groupe=form.cleaned_data["groupe"])]
        anomalies = [utils_dates.ConvertDateToFR(conso.date) for conso in consommations if (conso.date, conso.unite_id) not in ouvertures]
        if anomalies:
            return JsonResponse({"erreur": "Modification impossible des consommations ! Les consommations ne peuvent pas être transférées sur les dates suivantes car les unités sont fermées : %s." % ", ".join(anomalies)}, status=401)
        # Modifie le groupe des consommations existantes
        logger.debug("Changement de groupe pour %d consommations..." % len(consommations))
        nouvelles_conso = []
        for conso in consommations:
            conso.groupe = form.cleaned_data["groupe"]
            nouvelles_conso.append(conso)
        Consommation.objects.bulk_update(nouvelles_conso, ["groupe"], batch_size=50)

    # Changement de la catégorie de tarif
    if form.cleaned_data["modifier_categorie_tarif"] and consommations:
        # Recalcule les prestations
        dict_conso = {}
        for conso in consommations:
            dict_conso.setdefault(conso.individu_id, [])
            dict_conso[conso.individu_id].append(conso)
        from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
        for inscription in inscriptions:
            liste_dates = [conso.date for conso in dict_conso.get(inscription.individu_id, [])]
            grille = Grille_virtuelle(request=request, idfamille=inscription.famille_id, idindividu=inscription.individu_id,
                                      idactivite=inscription.activite_id, date_min=min(liste_dates), date_max=max(liste_dates))
            for conso in consommations:
                grille.Modifier(criteres={"idconso": conso.pk}, modifications={"categorie_tarif": form.cleaned_data["categorie_tarif"].pk})
            grille.Enregistrer()

    logger.debug("Application des modifications d'inscriptions terminée.")
    return JsonResponse({"success": True})


class Page(crud.Page):
    model = Inscription
    url_liste = "inscriptions_modifier"
    menu_code = "inscriptions_modifier"


class Liste(Page, crud.Liste):
    template_name = "individus/inscriptions_modifier.html"
    model = Inscription

    def get_queryset(self):
        return Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif").filter(self.Get_filtres("Q"), activite_id=self.kwargs.get("idactivite", None))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Modifier des inscriptions par lot"
        context["box_titre"] = "Sélection des paramètres"
        context["box_introduction"] = "Sélectionnez l'action à effectuer, renseignez les nouveaux paramètres de l'inscription puis cochez les inscriptions à modifier."
        context["onglet_actif"] = "inscriptions_modifier"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["active_checkbox"] = True
        context["bouton_supprimer"] = False
        context["hauteur_table"] = "400px"
        context["form_options"] = Formulaire_options(idactivite=self.kwargs.get("idactivite", None))
        context["idactivite"] = self.kwargs.get("idactivite", None)
        context["afficher_menu_brothers"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "igenerique:individu", "idinscription", "date_debut", "date_fin", "groupe__nom", "statut", "categorie_tarif__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        groupe = columns.TextColumn("Groupe", sources=["groupe__nom"])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=["categorie_tarif__nom"])
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", "individu", "famille", "date_debut", "date_fin", "groupe", "categorie_tarif"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["individu__nom", "individu__prenom"]


class Selection_activite(Page, crud.Ajouter):
    form_class = Formulaire_activite
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_activite, self).get_context_data(**kwargs)
        context["box_introduction"] = "Vous devez sélectionner une activité."
        context["page_titre"] = "Modifier des inscriptions par lot"
        context["box_titre"] = "Sélection de l'activité"
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("inscriptions_modifier_liste", kwargs={"idactivite": request.POST.get("activite")}))
