# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import CategorieProduit
from parametrage.forms.categories_produits import Formulaire


class Page(crud.Page):
    model = CategorieProduit
    url_liste = "categories_produits_liste"
    url_ajouter = "categories_produits_ajouter"
    url_modifier = "categories_produits_modifier"
    url_supprimer = "categories_produits_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories de produits."
    description_saisie = "Saisissez au moins un nom puis cliquez sur le bouton Enregistrer. Notez que vous pouvez créer des questionnaires pour les catégories de produits depuis le menu Paramétrage > Questionnaires afin d'obtenir des champs de saisie personnalisés."
    objet_singulier = "une catégorie de produits"
    objet_pluriel = "des catégories de produits"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = CategorieProduit

    def get_queryset(self):
        return CategorieProduit.objects.filter(self.Get_filtres("Q")).annotate(nbre_produits=Count("produit"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        image = columns.DisplayColumn("Image", sources="image", processor='Get_image')
        nbre_produits = columns.TextColumn("Nbre produits associés", sources="nbre_produits")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "nom", "image", "nbre_produits"]
            ordering = ["nom"]

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
