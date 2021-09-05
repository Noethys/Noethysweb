# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Ferie, LISTE_MOIS
from parametrage.forms.feries_fixes import Formulaire
from django.db.models import Q


class Page(crud.Page):
    model = Ferie
    url_liste = "feries_fixes_liste"
    url_ajouter = "feries_fixes_ajouter"
    url_modifier = "feries_fixes_modifier"
    url_supprimer = "feries_fixes_supprimer"
    description_liste = "Voici ci-dessous la liste des jours fériés fixes."
    description_saisie = "Saisissez toutes les informations concernant le jour férié fixe et cliquez sur le bouton Enregistrer."
    objet_singulier = "un jour férié fixe"
    objet_pluriel = "des jours fériés fixes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Ferie

    def get_queryset(self):
        return Ferie.objects.filter(Q(type="fixe") & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idferie', 'nom', 'jour', 'mois']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        mois = columns.TextColumn("Mois", sources=['mois'], processor='Get_nom_mois')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idferie', 'nom', 'jour', 'mois', 'actions']
            ordering = ['mois', 'jour']

        def Get_nom_mois(self, instance, **kwargs):
            return LISTE_MOIS[instance.mois-1]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

