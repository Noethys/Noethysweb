# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu
from fiche_individu.forms.individu_maladies import Formulaire


class Page(crud.Page):
    model = Individu
    url_liste = "maladies_liste"
    url_modifier = "maladies_modifier"
    description_liste = "Voici ci-dessous la liste des maladies des individus."
    description_saisie = "Sélectionnez un ou plusieurs maladies dans la liste proposée et cliquez sur le bouton Enregistrer."
    objet_singulier = "une maladie"
    objet_pluriel = "des maladies"


class Liste(Page, crud.Liste):
    model = Individu

    def get_queryset(self):
        return Individu.objects.prefetch_related("maladies").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Maladies"
        context['box_titre'] = "Liste des maladies"
        return context

    class datatable_class(MyDatatable):
        filtres = ["idindividu", "igenerique:pk", "maladies__nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        individu = columns.CompoundColumn("Individu", sources=['nom', 'prenom'])
        maladies = columns.TextColumn("Maladies", sources=["maladies__nom"], processor='Get_maladies')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idindividu", "individu", "maladies", "actions"]
            ordering = ["individu"]

        def Get_maladies(self, instance, *args, **kwargs):
            return ", ".join([maladie.nom for maladie in instance.maladies.all()])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
