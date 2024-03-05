# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Activite, Consommation
from core.views.customdatatable import CustomDatatable, Colonne, ColonneAction
from cotisations.forms.liste_cotisations_manquantes import Formulaire
from core.utils import utils_dates
from cotisations.utils import utils_cotisations_manquantes
import json


class Page(crud.Page):
    menu_code = "liste_cotisations_manquantes"


class Liste(Page, crud.CustomListe):
    template_name = "cotisations/liste_cotisations_manquantes.html"

    filtres = ["fgenerique:idfamille", "famille"]
    colonnes = [
        Colonne(code="famille", label="Famille", classe="CharField", label_filtre="Famille"),
        Colonne(code="pieces", label="Détail des adhésions", classe="CharField", label_filtre="Détail"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des adhésions manquantes"
        context['box_titre'] = "Liste des adhésions manquantes"
        context['box_introduction'] = "Voici ci-dessous la liste des adhésions manquantes."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context["hauteur_table"] = "400px"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
            context["datatable"] = self.Get_customdatatable()
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "datatable": self.Get_customdatatable(parametres=form.cleaned_data)
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_customdatatable(self, parametres={}):
        lignes = []

        if parametres:
            # Récupération des paramètres
            date_reference = parametres["date"]
            masquer_complets = parametres["masquer_complets"]

            param_activites = json.loads(parametres["activites"])
            if param_activites["type"] == "groupes_activites":
                liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
            if param_activites["type"] == "activites":
                liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

            if parametres["presents"]:
                date_min = utils_dates.ConvertDateENGtoDate(parametres["presents"].split(";")[0])
                date_max = utils_dates.ConvertDateENGtoDate(parametres["presents"].split(";")[1])
                presents = (date_min, date_max)
            else:
                presents = None

            # Importation des cotisations manquantes
            dictPieces = utils_cotisations_manquantes.Get_liste_cotisations_manquantes(date_reference=date_reference, activites=liste_activites, presents=presents, only_concernes=masquer_complets)

            # Mise en forme des données
            lignes = []
            for idfamille, valeurs in dictPieces.items():
                lignes.append([valeurs["nom_famille"], valeurs["texte"]])

        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())

