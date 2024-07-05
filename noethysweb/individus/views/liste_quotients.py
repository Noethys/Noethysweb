# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse
from django.db.models import Q
from core.views import crud
from core.models import Activite, Inscription, Quotient, Famille
from core.views.customdatatable import CustomDatatable, Colonne
from core.utils import utils_dates
from individus.forms.liste_quotients import Formulaire


class Page(crud.Page):
    menu_code = "liste_quotients"


class Liste(Page, crud.CustomListe):
    template_name = "individus/liste_quotients.html"

    filtres = ["fgenerique:idfamille", "famille", "autorisation_cafpro", "qf", "revenu", "date_debut", "date_fin", "observations"]
    colonnes = [
        Colonne(code="famille", label="Famille", classe="CharField", label_filtre="Famille"),
        Colonne(code="autorisation_cafpro", label="Autorisation CAF-CDAP", classe="BooleanField"),
        Colonne(code="qf", label="QF", classe="DecimalField"),
        Colonne(code="revenu", label="Revenu", classe="DecimalField"),
        Colonne(code="date_debut", label="Date de début", classe="DateField"),
        Colonne(code="date_fin", label="Date de fin", classe="DateField"),
        Colonne(code="observations", label="Observations", classe="CharField"),
        Colonne(code="actions", label="Actions", classe=""),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des quotients familiaux/revenus"
        context['box_titre'] = "Liste des quotients familiaux/revenus"
        context['box_introduction'] = "Voici ci-dessous la liste des quotients familiaux/revenus."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        # context["hauteur_table"] = "500px"
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
            date_situation = parametres["date"]
            type_quotient = parametres["type_quotient"]
            filtre_qf = parametres["filtre"]

            # Si une sélection de familles uniquement
            if parametres["familles"] == "SELECTION":
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

                # Importation des familles
                conditions = Q(activite__in=liste_activites)
                if presents:
                    conditions &= Q(consommation__date__gte=presents[0], consommation__date__lte=presents[1])
                liste_familles = []
                for inscription in Inscription.objects.select_related('famille').filter(conditions).distinct():
                    if inscription.famille not in liste_familles:
                        liste_familles.append(inscription.famille)

            # Si toutes les familles
            if parametres["familles"] == "TOUTES":
                liste_familles = Famille.objects.filter(etat__isnull=True)

            # Importation des quotients
            dict_quotients = {quotient.famille_id: quotient for quotient in Quotient.objects.filter(date_debut__lte=date_situation, date_fin__gte=date_situation, type_quotient=type_quotient)}

            # Mise en forme des données
            lignes = []
            for famille in liste_familles:
                quotient = dict_quotients.get(famille.pk)
                boutons = [
                    """<a type="button" class="btn btn-default btn-xs" href="%s" title="Ouvrir la fiche famille" target="_blank"><i class="fa fa-fw fa-users"></i></a>""" % reverse("famille_quotients_liste", args=[famille.pk]),
                ]
                if filtre_qf == "TOUTES" or (filtre_qf == "AVEC_QF" and quotient) or (filtre_qf == "SANS_QF" and not quotient):
                    lignes.append([
                        famille.nom,
                        "Oui" if famille.autorisation_cafpro else "",
                        quotient.quotient if quotient else "",
                        quotient.revenu if quotient and quotient.revenu else "",
                        utils_dates.ConvertDateToFR(quotient.date_debut) if quotient else "",
                        utils_dates.ConvertDateToFR(quotient.date_fin) if quotient else "",
                        quotient.observations if quotient and quotient.observations else "",
                        " ".join(boutons),
                    ])

        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())
