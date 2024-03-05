# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Activite, Consommation
from django.db.models import Sum
from decimal import Decimal
from core.views.customdatatable import CustomDatatable, Colonne, ColonneAction
from consommations.forms.liste_absences import Formulaire
from core.utils import utils_dates
from django.db.models import Q, Count
import json


class Page(crud.Page):
    menu_code = "liste_absences"


class Liste(Page, crud.CustomListe):
    template_name = "consommations/liste_absences.html"

    filtres = ["fgenerique:idindividu", "individu", "quantite", "absences"]
    colonnes = [
        Colonne(code="individu", label="Individu", classe="CharField", label_filtre="Nom"),
        Colonne(code="quantite", label="Quantité", classe="IntegerField"),
        Colonne(code="absences", label="Détail des absences", classe="CharField", label_filtre="Détail"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des absences"
        context['box_titre'] = "Liste des absences"
        context['box_introduction'] = "Voici ci-dessous la liste des absences."
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
            date_min = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
            date_max = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
            param_activites = json.loads(parametres["activites"])
            conditions_periodes = Q(date__gte=date_min) & Q(date__lte=date_max)
            if param_activites["type"] == "groupes_activites":
                condition_activites = Q(activite__groupes_activites__in=param_activites["ids"])
            if param_activites["type"] == "activites":
                condition_activites = Q(activite__in=param_activites["ids"])
            etat = parametres["etat"]

            # Importation des consommations
            consommations = Consommation.objects.select_related('individu', 'unite').filter(conditions_periodes, condition_activites, etat=etat).order_by("date")

            dict_individus = {}
            for conso in consommations:
                dict_individus.setdefault(conso.individu, {"quantite": 0, "dates": []})
                if conso.date not in dict_individus[conso.individu]["dates"]:
                    dict_individus[conso.individu]["dates"].append(conso.date)
                    dict_individus[conso.individu]["quantite"] += 1

            # Mise en forme des données
            lignes = []
            for individu, dict_individu in dict_individus.items():
                liste_dates = ", ".join([utils_dates.ConvertDateToFR(date) for date in dict_individu["dates"]])
                ligne = [individu.Get_nom(), dict_individu["quantite"], liste_dates]
                lignes.append(ligne)

        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())

