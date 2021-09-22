# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from core.models import LISTE_CATEGORIES_QUESTIONNAIRES, QuestionnaireQuestion, Famille, Individu
from core.utils import utils_questionnaires
from parametrage.forms.questionnaires import Formulaire



class Page(crud.Page):
    model = QuestionnaireQuestion
    url_liste = "questions_liste"
    url_ajouter = "questions_ajouter"
    url_modifier = "questions_modifier"
    url_supprimer = "questions_supprimer"
    description_liste = "Sélectionnez une catégorie et consultez les questions correspondantes."
    description_saisie = "Saisissez toutes les informations concernant la question à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une question"
    objet_pluriel = "des questions"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Catégorie"
        context['liste_categories'] = LISTE_CATEGORIES_QUESTIONNAIRES
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
        ]
        return context

    def Get_categorie(self):
        return self.kwargs.get('categorie', 'individu')

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
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
    model = QuestionnaireQuestion


class Liste(Page, crud.Liste):
    model = QuestionnaireQuestion
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return QuestionnaireQuestion.objects.filter(Q(categorie=self.Get_categorie()) & self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_reponses=Count("questionnairereponse"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_deplacements'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idquestion", 'label']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        controle = columns.TextColumn("Contrôle", sources="controle", processor='Get_controle')
        nbre_reponses = columns.TextColumn("Réponses associées", sources="nbre_reponses")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idquestion", 'ordre', 'label', 'controle', 'nbre_reponses']
            ordering = ['ordre']

        def Get_controle(self, instance, **kwargs):
            return instance.get_controle_display()

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.categorie, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.categorie, instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        redirect = super(Ajouter, self).form_valid(form)
        # Création des réponses pour tous (familles ou individus)
        if self.object.categorie == "famille":
            liste_instances = Famille.objects.all()
        elif self.object.categorie == "individu":
            liste_instances = Individu.objects.all()
        else:
            liste_instances = []
        if liste_instances:
            utils_questionnaires.Creation_reponses(categorie=self.object.categorie, liste_instances=liste_instances, question=self.object)
        return redirect

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
