# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import ModeleWord
from core.data.data_modeles_word import CATEGORIES as CATEGORIES_MODELES_WORD
from parametrage.forms.modeles_word import Formulaire


class Page(crud.Page):
    model = ModeleWord
    url_liste = "modeles_word_liste"
    url_ajouter = "modeles_word_ajouter"
    url_modifier = "modeles_word_modifier"
    url_supprimer = "modeles_word_supprimer"
    description_liste = "Sélectionnez une catégorie et consultez les modèles correspondants."
    description_saisie = "Saisissez toutes les informations concernant le modèle à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle de document Word"
    objet_pluriel = "des modèles de documents Word"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Catégorie"
        context['liste_categories'] = CATEGORIES_MODELES_WORD
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
        ]
        return context

    def Get_categorie(self):
        return self.kwargs.get('categorie', 'contrat_collaborateur')

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["categorie"] = self.Get_categorie()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'categorie': self.Get_categorie()})


class Liste(Page, crud.Liste):
    model = ModeleWord
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return ModeleWord.objects.filter(Q(categorie=self.Get_categorie()) & self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmodele", 'nom', 'description', 'defaut']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmodele", 'nom', 'description', 'defaut']
            ordering = ['nom']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.categorie, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.categorie, instance.pk])),
            ]
            return self.Create_boutons_actions(html)

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres modèles
        if form.instance.defaut:
            self.model.objects.filter(categorie=form.instance.categorie).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres modèles
        if form.instance.defaut:
            self.model.objects.filter(categorie=form.instance.categorie).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
