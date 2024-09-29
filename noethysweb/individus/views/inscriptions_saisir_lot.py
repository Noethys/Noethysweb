# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models.functions import Concat
from django.db.models import F, CharField, Value
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Inscription, Rattachement
from core.utils import utils_dates
from individus.forms.inscriptions_saisir_lot import Formulaire_activite, Formulaire_options


def Appliquer(request):
    logger.debug("Saisir un lot d'inscriptions...")

    # Récupération des inscriptions cochées
    rattachements_coches = json.loads(request.POST.get("rattachements_coches"))
    if not rattachements_coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un individu à inscrire dans la liste"}, status=401)
    rattachements = Rattachement.objects.select_related("individu", "famille").filter(pk__in=rattachements_coches)

    # Récupération des options
    valeurs_form_options = json.loads(request.POST.get("form_options"))
    form = Formulaire_options(valeurs_form_options, idactivite=request.POST.get("idactivite"))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez renseigner correctement les paramètres"}, status=401)

    # Génération des inscriptions
    liste_ajouts = []
    for rattachement in rattachements:
        liste_ajouts.append(Inscription(
            individu=rattachement.individu,
            famille=rattachement.famille,
            activite_id=request.POST.get("idactivite"),
            groupe=form.cleaned_data["groupe"],
            categorie_tarif=form.cleaned_data["categorie_tarif"],
            date_debut=form.cleaned_data["date_debut"],
        ))
    Inscription.objects.bulk_create(liste_ajouts)

    logger.debug("Génération des inscriptions terminée.")
    return JsonResponse({"success": True})


class Page(crud.Page):
    model = Rattachement
    url_liste = "inscriptions_saisir_lot"
    menu_code = "inscriptions_saisir_lot"


class Liste(Page, crud.Liste):
    template_name = "individus/inscriptions_saisir_lot.html"
    model = Rattachement

    def get_queryset(self):
        # Exclut les individus déjà inscrits à cette activité
        inscriptions_existantes = ["%d_%d" % (i.individu_id, i.famille_id) for i in Inscription.objects.filter(activite_id=self.kwargs.get("idactivite", None))]
        rattachements = Rattachement.objects.select_related("individu", "famille").annotate(code=Concat(F("individu_id"), Value("_"), F("famille_id"), output_field=CharField())).exclude(code__in=inscriptions_existantes).filter(self.Get_filtres("Q"))
        return rattachements

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Saisir un lot d'inscriptions"
        context["box_titre"] = "Sélection des paramètres"
        context["box_introduction"] = "Cette fonctionnalité de générer des inscriptions pour les individus sélectionnés. Cochez les individus à inscrire puis renseignez les caractéristiques de l'inscription avant de cliquer sur le bouton Générer."
        context["onglet_actif"] = "inscriptions_saisir_lot"
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
        filtres = ['idrattachement', "igenerique:individu", "fgenerique:famille", "genre", "categorie"]
        check = columns.CheckBoxSelectColumn(label="")
        idindividu = columns.IntegerColumn("ID", sources=['individu__pk'])
        nom = columns.TextColumn("Nom", sources=['individu__nom'])
        prenom = columns.TextColumn("Prénom", sources=['individu__prenom'])
        genre = columns.TextColumn("Genre", sources=None, processor='Get_genre')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        categorie = columns.TextColumn("Profil", sources=['categorie'], processor="Get_categorie")
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        secteur = columns.TextColumn("Secteur", processor="Get_secteur")
        date_naiss = columns.TextColumn("Date naiss.", processor="Get_date_naiss")
        age = columns.TextColumn("Age", sources=['Get_age'], processor="Get_age")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idrattachement", "idindividu", "nom", "prenom", "categorie", "famille", "age", "date_naiss", "genre", "rue_resid", "cp_resid", "ville_resid"]
            hidden_columns = ["idrattachement", "secteur"]
            ordering = ["nom", "prenom"]

        def Get_categorie(self, instance, *args, **kwargs):
            return instance.Get_profil()

        def Get_age(self, instance, *args, **kwargs):
            return instance.individu.Get_age()

        def Get_date_naiss(self, instance, *args, **kwargs):
            return utils_dates.ConvertDateToFR(instance.individu.date_naiss)

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.individu.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.individu.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Get_secteur(self, instance, *args, **kwargs):
            return instance.individu.secteur

        def Get_genre(self, instance, *args, **kwargs):
            return instance.individu.Get_sexe()


class Selection_activite(Page, crud.Ajouter):
    form_class = Formulaire_activite
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_activite, self).get_context_data(**kwargs)
        context["box_introduction"] = "Vous devez sélectionner une activité."
        context["page_titre"] = "Saisir un lot d'inscriptions"
        context["box_titre"] = "Sélection de l'activité"
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("inscriptions_saisir_lot_liste", kwargs={"idactivite": request.POST.get("activite")}))
