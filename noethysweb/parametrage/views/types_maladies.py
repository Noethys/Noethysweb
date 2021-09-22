# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_dates
from core.models import TypeMaladie, TypeVaccin
from parametrage.forms.types_maladies import Formulaire


class Page(crud.Page):
    model = TypeMaladie
    url_liste = "types_maladies_liste"
    url_ajouter = "types_maladies_ajouter"
    url_modifier = "types_maladies_modifier"
    url_supprimer = "types_maladies_supprimer"
    description_liste = "Voici ci-dessous la liste des types de maladies."
    description_saisie = "Saisissez toutes les informations concernant la maladie à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de maladie"
    objet_pluriel = "des types de maladies"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeMaladie

    def get_queryset(self):
        return TypeMaladie.objects.filter(self.Get_filtres("Q")).annotate(nbre_individus=Count('individu_maladies')).annotate(nbre_vaccins=Count('vaccin_maladies'))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_maladie", "nom", "vaccin_obligatoire"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        vaccin_obligatoire = columns.TextColumn("Vaccination obligatoire", sources=["vaccin_obligatoire"], processor='Get_vaccin_obligatoire')
        nbre_individus = columns.TextColumn("Individus associés", sources="nbre_individus")
        nbre_vaccins = columns.TextColumn("Vaccins associés", sources="nbre_vaccins")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_maladie", "nom", "vaccin_obligatoire", "nbre_individus", "nbre_vaccins"]
            ordering = ["nom"]
            processors = {
                'vaccin_date_naiss_min': helpers.format_date('%d/%m/%Y'),
            }

        def Get_vaccin_obligatoire(self, instance, *args, **kwargs):
            if instance.vaccin_obligatoire:
                if instance.vaccin_date_naiss_min:
                    texte_date_naiss_min = " (à partir du %s)" % utils_dates.ConvertDateToFR(instance.vaccin_date_naiss_min)
                else:
                    texte_date_naiss_min = ""
                return "<small class='badge badge-success'>Oui%s</small>" % texte_date_naiss_min
            return ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [
        ("individu(s)", "individu_maladies"),
        ("vaccin(s)", "vaccin_maladies")
    ]
