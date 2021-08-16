# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ImageArticle
from parametrage.forms.images_articles import Formulaire


class Page(crud.Page):
    model = ImageArticle
    url_liste = "images_articles_liste"
    url_ajouter = "images_articles_ajouter"
    url_modifier = "images_articles_modifier"
    url_supprimer = "images_articles_supprimer"
    description_liste = "Voici ci-dessous la liste des images à intégrer dans des articles du portail."
    description_saisie = "Saisissez un titre et une image puis cliquez sur le bouton Enregistrer."
    objet_singulier = "une image"
    objet_pluriel = "des images"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ImageArticle

    def get_queryset(self):
        return ImageArticle.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_articles=Count("article"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idimage", "titre"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        image = columns.DisplayColumn("Image", sources="image", processor='Get_image')
        nbre_articles = columns.TextColumn("Nbre articles associés", sources="nbre_articles")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idimage", "titre", "image", "nbre_articles"]
            ordering = ["titre"]

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
