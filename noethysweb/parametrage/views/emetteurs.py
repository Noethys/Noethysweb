# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Emetteur
from parametrage.forms.emetteurs import Formulaire



class Page(crud.Page):
    model = Emetteur
    url_liste = "emetteurs_liste"
    url_ajouter = "emetteurs_ajouter"
    url_modifier = "emetteurs_modifier"
    url_supprimer = "emetteurs_supprimer"
    description_liste = "Voici ci-dessous la liste des émetteurs."
    description_saisie = "Saisissez toutes les informations concernant l'émetteur à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un émetteur de règlements"
    objet_pluriel = "des émetteurs de règlements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Emetteur

    def get_queryset(self):
        return Emetteur.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idemetteur', 'nom', 'mode__label']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        image = columns.DisplayColumn("Image", sources="image", processor='Get_image')
        mode = columns.TextColumn("Label", sources=["mode__label"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idemetteur', 'nom', 'mode', 'image']
            ordering = ['nom']

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
