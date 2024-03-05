# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu
from fiche_individu.forms.individu_regimes_alimentaires import Formulaire


class Page(crud.Page):
    model = Individu
    url_liste = "regimes_alimentaires_liste"
    url_modifier = "regimes_alimentaires_modifier"
    description_liste = "Voici ci-dessous la liste des régimes alimentaires des individus."
    description_saisie = "Sélectionnez un ou plusieurs régimes alimentaires dans la liste proposée et cliquez sur le bouton Enregistrer."
    objet_singulier = "un régime alimentaire"
    objet_pluriel = "des régimes alimentaires"


class Liste(Page, crud.Liste):
    model = Individu

    def get_queryset(self):
        return Individu.objects.prefetch_related("regimes_alimentaires").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Régimes alimentaires"
        context['box_titre'] = "Liste des régimes alimentaires"
        return context

    class datatable_class(MyDatatable):
        filtres = ["idindividu", "igenerique:pk", "regimes_alimentaires__nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        individu = columns.CompoundColumn("Individu", sources=['nom', 'prenom'])
        regimes = columns.TextColumn("Régimes", sources=["regimes_alimentaires__nom"], processor='Get_regimes')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idindividu", "individu", "regimes", "actions"]
            ordering = ["individu"]

        def Get_regimes(self, instance, *args, **kwargs):
            return ", ".join([regime.nom for regime in instance.regimes_alimentaires.all()])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
