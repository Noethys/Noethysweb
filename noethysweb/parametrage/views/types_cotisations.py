# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Q, Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypeCotisation
from parametrage.forms.types_cotisations import Formulaire


class Page(crud.Page):
    model = TypeCotisation
    url_liste = "types_cotisations_liste"
    url_ajouter = "types_cotisations_ajouter"
    url_modifier = "types_cotisations_modifier"
    url_supprimer = "types_cotisations_supprimer"
    description_liste = "Voici ci-dessous la liste des types d'adhésion."
    description_saisie = "Saisissez toutes les informations concernant le type d'adhésion à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type d'adhésion"
    objet_pluriel = "des types d'adhésions"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeCotisation

    def get_queryset(self):
        return TypeCotisation.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_cotisations=Count("cotisation"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idtype_cotisation', 'nom', 'type', 'carte', 'defaut']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        carte = columns.TextColumn("Carte", sources="carte", processor='Get_carte')
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')
        nbre_cotisations = columns.TextColumn("Adhésions associées", sources="nbre_cotisations")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idtype_cotisation', 'nom', 'type', 'carte', 'defaut', 'nbre_cotisations']
            ordering = ['nom']

        def Get_carte(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.carte else ""

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres types
        if form.instance.defaut:
            self.model.objects.filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres types
        if form.instance.defaut:
            self.model.objects.filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [
        ("activité(s)", "activite_types_cotisations"),
        ("tarif(s)", "tarif_cotisations"),
    ]

    def delete(self, request, *args, **kwargs):
        reponse = super(Supprimer, self).delete(request, *args, **kwargs)

        # Si le défaut a été supprimé, on le réattribue à un autre type
        if reponse.status_code != 303:
            if len(self.model.objects.filter(defaut=True)) == 0:
                objet = self.model.objects.all().first()
                if objet:
                    objet.defaut = True
                    objet.save()
        return reponse
