# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TransportCompagnie
from parametrage.forms.compagnies import Formulaire
from individus.utils import utils_transports


class Page(crud.Page):
    model = TransportCompagnie
    url_liste = "compagnies_liste"
    url_ajouter = "compagnies_ajouter"
    url_modifier = "compagnies_modifier"
    url_supprimer = "compagnies_supprimer"
    description_liste = "Voici ci-dessous la liste des compagnies."
    description_saisie = "Saisissez toutes les informations concernant la compagnie à saisir et cliquez sur le bouton Enregistrer."

    def get_context_data(self, **kwargs):
        parametre = utils_transports.CATEGORIES[self.Get_categorie()]["parametrage"]["compagnies"]
        self.objet_singulier = "une %s" % parametre["label_singulier"]
        self.objet_pluriel = "des %s" % parametre["label_pluriel"]
        context = super(Page, self).get_context_data(**kwargs)
        context["categorie"] = self.Get_categorie()
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={"categorie": self.Get_categorie()}), "icone": "fa fa-plus"},
            {"label": "Revenir au paramétrage des transports", "classe": "btn btn-default", "href": reverse_lazy("parametrage_transports"), "icone": "fa fa-reply"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["categorie"] = self.Get_categorie()
        return form_kwargs

    def Get_categorie(self):
        return self.kwargs.get("categorie", None)

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'categorie': self.Get_categorie()})


class Liste(Page, crud.Liste):
    model = TransportCompagnie

    def get_queryset(self):
        return TransportCompagnie.objects.filter(self.Get_filtres("Q"), categorie=self.Get_categorie())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcompagnie", "nom", "rue", "cp", "ville"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcompagnie", "nom", "rue", "cp", "ville"]
            ordering = ["nom"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("compagnies_modifier", kwargs={"categorie": instance.categorie, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("compagnies_supprimer", kwargs={"categorie": instance.categorie, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
