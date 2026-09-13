# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from core.views.mydatatableview import MyDatatable, columns, Deplacer_lignes
from core.views import crud
from core.models import LISTE_CATEGORIES_QUESTIONNAIRES, QuestionnaireGroupe
from parametrage.forms.questionnaires_groupes import Formulaire


class Page(crud.Page):
    model = QuestionnaireGroupe
    url_liste = "questionnaires_groupes_liste"
    url_ajouter = "questionnaires_groupes_ajouter"
    url_modifier = "questionnaires_groupes_modifier"
    url_supprimer = "questionnaires_groupes_supprimer"
    description_liste = "Vous pouvez ici créer des regroupements permettant de rassembler les questions de vos questionnaires. Sélectionnez une catégorie de questionnaire et consultez les regroupements de questions correspondants."
    description_saisie = "Saisissez le nom du regroupement de questions et cliquez sur le bouton Enregistrer."
    objet_singulier = "un regroupement de questions"
    objet_pluriel = "des regroupements de questions"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Catégorie"
        context['liste_categories'] = LISTE_CATEGORIES_QUESTIONNAIRES
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
            {"label": "Revenir à la liste des questions", "classe": "btn btn-default", "href": reverse_lazy("questions_liste", kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-arrow-left"},
        ]
        return context

    def Get_categorie(self):
        return self.kwargs.get('categorie', 'individu')

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


class Deplacer(Deplacer_lignes):
    model = QuestionnaireGroupe


class Liste(Page, crud.Liste):
    model = QuestionnaireGroupe
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return QuestionnaireGroupe.objects.filter(Q(categorie=self.Get_categorie()) & self.Get_filtres("Q")).annotate(nbre_questions=Count("questionnairequestion"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_deplacements'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idgroupe", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nbre_questions = columns.TextColumn("Questions associées", sources=['nbre_questions'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idgroupe", "ordre", "nom", "nbre_questions"]
            ordering = ["ordre"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.categorie, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.categorie, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
