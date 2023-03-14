# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Produit, TarifProduit
from core.utils import utils_preferences
from parametrage.forms.produits import Formulaire


class Page(crud.Page):
    model = Produit
    url_liste = "produits_liste"
    url_ajouter = "produits_ajouter"
    url_modifier = "produits_modifier"
    url_supprimer = "produits_supprimer"
    description_liste = "Voici ci-dessous la liste des produits."
    description_saisie = "Saisissez au minimum un nom puis cliquez sur le bouton Enregistrer. Notez que vous pouvez créer des questionnaires pour les produits depuis le menu Paramétrage > Questionnaires afin d'obtenir des champs de saisie personnalisés."
    objet_singulier = "un produit"
    objet_pluriel = "des produits"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Produit

    def get_queryset(self):
        return Produit.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idproduit", "nom", "categorie"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        image = columns.DisplayColumn("Image", sources="image", processor='Get_image')
        tarification = columns.TextColumn("Tarification", sources=None, processor='Get_tarification')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idproduit", "nom", "categorie", "image", "tarification"]
            ordering = ["nom"]

        def Get_image(self, instance, **kwargs):
            if instance.image:
                return """<img class='img-fluid img-thumbnail' style='max-height: 80px;' src='%s'>""" % instance.image.url
            return ""

        def Get_tarification(self, instance, *args, **kwargs):
            # Importation des tarifs avancés
            if not hasattr(self, "dict_tarifs"):
                self.dict_tarifs = {}
                for tarif in TarifProduit.objects.filter(produit__isnull=False):
                    if tarif.produit not in self.dict_tarifs:
                        self.dict_tarifs[tarif.produit] = []
                    self.dict_tarifs[tarif.produit].append(tarif)

            # Affichage du texte de la colonne tarification
            if instance.montant:
                return "%.2f %s" % (instance.montant, utils_preferences.Get_symbole_monnaie())
            if instance in self.dict_tarifs:
                pluriel = "s" if len(self.dict_tarifs[instance]) > 1 else ""
                texte = "%d tarif%s avancé%s" % (len(self.dict_tarifs[instance]), pluriel, pluriel)
            else:
                texte = "Gratuit"
            url_liste = reverse("produits_tarifs_liste", args=[instance.pk])
            return texte + """&nbsp; <a type='button' class='btn btn-default btn-sm' href='%s' title='Ajouter, modifier ou supprimer des tarifs avancés'><i class="fa fa-gear"></i></a>""" % url_liste


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
