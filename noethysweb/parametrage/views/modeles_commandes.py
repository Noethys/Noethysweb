# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Q, Count
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import CommandeModele
from parametrage.forms.modeles_commandes import Formulaire


class Page(crud.Page):
    model = CommandeModele
    url_liste = "modeles_commandes_liste"
    url_ajouter = "modeles_commandes_ajouter"
    url_modifier = "modeles_commandes_modifier"
    url_supprimer = "modeles_commandes_supprimer"
    description_liste = "Voici ci-dessous la liste des modèles de commandes. Après avoir ajouté ici un modèle, allez dans le paramétrage des colonnes des modèles de commandes."
    description_saisie = "Saisissez toutes les informations concernant le modèle à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle de commande"
    objet_pluriel = "des modèles de commandes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = CommandeModele

    def get_queryset(self):
        return CommandeModele.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_commandes=Count("commande"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmodele", "nom", "restaurateur", "defaut"]
        defaut = columns.TextColumn("Défaut", sources="defaut", processor="Get_default")
        nbre_commandes = columns.TextColumn("Commandes associées", sources="nbre_commandes")
        actions = columns.TextColumn("Actions", sources=None, processor="Get_actions_standard")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmodele", "nom", "restaurateur", "defaut", "nbre_commandes", "actions"]
            ordering = ['nom']

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres modèles
        if form.instance.defaut:
            self.model.objects.filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres modèles
        if form.instance.defaut:
            self.model.objects.filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Supprimer(Page, crud.Supprimer):
    pass

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
