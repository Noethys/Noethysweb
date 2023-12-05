# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import CompteBancaire
from parametrage.forms.comptes_bancaires import Formulaire



class Page(crud.Page):
    model = CompteBancaire
    url_liste = "comptes_bancaires_liste"
    url_ajouter = "comptes_bancaires_ajouter"
    url_modifier = "comptes_bancaires_modifier"
    url_supprimer = "comptes_bancaires_supprimer"
    description_liste = "Voici ci-dessous la liste des comptes bancaires."
    description_saisie = "Saisissez toutes les informations concernant le compte bancaire à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un compte bancaire"
    objet_pluriel = "des comptes bancaires"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = CompteBancaire

    def get_queryset(self):
        return CompteBancaire.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idcompte', 'nom', 'numero', 'defaut']
        numero = columns.TextColumn("Numéro", sources=None, processor='Get_numero')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idcompte', 'nom', 'numero', 'defaut']
            ordering = ['nom']

        def Get_numero(self, instance, **kwargs):
            return instance.numero

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres objets
        self.Supprimer_defaut_autres_objets(form)
        return super().form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres objets
        self.Supprimer_defaut_autres_objets(form)
        return super().form_valid(form)

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire

    # def delete(self, request, *args, **kwargs):
    #     reponse = super(Supprimer, self).delete(request, *args, **kwargs)
    #     if reponse.status_code != 303:
    #         # Si le défaut a été supprimé, on le réattribue à une autre objet
    #         self.Attribuer_defaut()
    #     return reponse
