# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ModeReglement
from parametrage.forms.modes_reglements import Formulaire



class Page(crud.Page):
    model = ModeReglement
    url_liste = "modes_reglements_liste"
    url_ajouter = "modes_reglements_ajouter"
    url_modifier = "modes_reglements_modifier"
    url_supprimer = "modes_reglements_supprimer"
    description_liste = "Voici ci-dessous la liste des modes de règlements."
    description_saisie = "Saisissez toutes les informations concernant le mode de règlement à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un mode de règlement"
    objet_pluriel = "des modes de règlements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ModeReglement

    def get_queryset(self):
        return ModeReglement.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idmode', 'label']

        image = columns.DisplayColumn("Image", sources="image", processor='Get_image')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idmode', 'label']
            ordering = ['label']

        def Get_image(self, instance, **kwargs):
            if instance.image:
                return """<img class='img-fluid img-thumbnail' style='max-height: 80px;' src='%s'>""" % instance.image.url
            return ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
