# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import CategorieEvenement
from parametrage.views.activites import Onglet
from parametrage.forms.activites_evenements_categories import Formulaire


class Page(Onglet):
    model = CategorieEvenement
    url_liste = "activites_evenements_categories_liste"
    url_ajouter = "activites_evenements_categories_ajouter"
    url_modifier = "activites_evenements_categories_modifier"
    url_supprimer = "activites_evenements_categories_supprimer"
    description_liste = "Vous pouvez saisir ici des catégories d'événements liées à l'activité. Ces catégories pourront ensuite être associées aux événements souhaités."
    description_saisie = "Saisissez toutes les informations concernant la catégorie et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie d'événement"
    objet_pluriel = "des catégories d'événements"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = "evenements"
        context['url_liste'] = self.url_liste
        context['idactivite'] = self.Get_idactivite()
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idactivite': self.Get_idactivite()}), "icone": "fa fa-plus"},
            {"label": "Retour à la liste des événements", "classe": "btn btn-default", "href": reverse_lazy("activites_evenements_liste", kwargs={'idactivite': self.Get_idactivite()}), "icone": "fa fa-arrow-circle-o-left"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idactivite"] = self.Get_idactivite()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idactivite': self.Get_idactivite()})


class Liste(Page, crud.Liste):
    model = CategorieEvenement
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return CategorieEvenement.objects.filter(Q(activite=self.Get_idactivite()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "nom", "actions"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "parametrage/activite_delete.html"
