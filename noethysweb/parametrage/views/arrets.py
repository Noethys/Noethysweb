# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, Deplacer_lignes
from core.views import crud
from core.models import TransportArret, TransportLigne
from parametrage.forms.arrets import Formulaire
from individus.utils import utils_transports


class Page(crud.Page):
    model = TransportArret
    url_liste = "arrets_liste"
    url_ajouter = "arrets_ajouter"
    url_modifier = "arrets_modifier"
    url_supprimer = "arrets_supprimer"
    description_liste = "Voici ci-dessous la liste des arrêts."
    description_saisie = "Saisissez toutes les informations concernant l'arrêt à saisir et cliquez sur le bouton Enregistrer."

    def get_context_data(self, **kwargs):
        parametre = utils_transports.CATEGORIES[self.Get_categorie()]["parametrage"]["arrets"]
        self.objet_singulier = "une %s" % parametre["label_singulier"]
        self.objet_pluriel = "des %s" % parametre["label_pluriel"]
        context = super(Page, self).get_context_data(**kwargs)
        context["categorie"] = self.Get_categorie()
        context["idligne"] = self.Get_ligne()
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={"categorie": self.Get_categorie(), "idligne": self.Get_ligne()}), "icone": "fa fa-plus"},
            {"label": "Revenir au paramétrage des transports", "classe": "btn btn-default", "href": reverse_lazy("parametrage_transports"), "icone": "fa fa-reply"},
        ]
        context['label_regroupement'] = "Ligne de %s" % parametre["label_singulier"]
        context['liste_regroupements'] = [(item.pk, item.nom) for item in TransportLigne.objects.filter(categorie=self.Get_categorie()).order_by("nom")]
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["categorie"] = self.Get_categorie()
        form_kwargs["idligne"] = self.Get_ligne()
        return form_kwargs

    def Get_categorie(self):
        return self.kwargs.get("categorie", None)

    def Get_ligne(self):
        idligne = self.kwargs.get("idligne", None)
        if idligne:
            return idligne
        lignes = TransportLigne.objects.filter(categorie=self.kwargs.get("categorie", None)).order_by("nom")
        return lignes[0].pk if lignes else 0

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={"categorie": self.Get_categorie(), "idligne": self.Get_ligne()})


class Liste(Page, crud.Liste):
    model = TransportArret
    template_name = "parametrage/arrets.html"

    def get_queryset(self):
        return TransportArret.objects.select_related("ligne").filter(self.Get_filtres("Q"), ligne_id=self.Get_ligne())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_deplacements'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idarret", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idarret", "ordre", "nom"]
            ordering = ["ordre"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("arrets_modifier", kwargs={"categorie": instance.ligne.categorie, "idligne": instance.ligne_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("arrets_supprimer", kwargs={"categorie": instance.ligne.categorie, "idligne": instance.ligne_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass

class Deplacer(Deplacer_lignes):
    model = TransportArret