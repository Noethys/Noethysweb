# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from core.views import crud
from core.models import QuestionnaireReponse, QuestionnaireQuestion, FiltreListe, Famille, LISTE_CATEGORIES_QUESTIONNAIRES


class Liste(crud.CustomListe):
    template_name = "core/crud/liste_avec_categorie.html"
    categorie_question = None

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Questionnaires"
        context['box_titre'] = "Liste des questionnaires familiaux"

        # Importation des catégories de questions
        dict_categories_questions = {code: label for code, label in LISTE_CATEGORIES_QUESTIONNAIRES}

        # Importation des questions
        context['label_categorie'] = "Question"
        context['categorie'] = int(self.Get_categorie()) if self.Get_categorie() else None
        questions = QuestionnaireQuestion.objects.filter(Q(categorie=self.categorie_question) & self.Get_condition_structure()).order_by("categorie", "ordre")
        context['liste_categories'] = [(None, "--------")] + [(question.pk, "%s : %s" % (dict_categories_questions[question.categorie], question.label)) for question in questions]

        question = QuestionnaireQuestion.objects.get(pk=self.Get_categorie()) if self.Get_categorie() else None

        context['options_filtre'] = "idquestion=%s" % self.Get_categorie()
        context['impression_introduction'] = "Question : %s" % question.label if question else "Aucune question"
        context["datatable"] = self.Get_customdatatable() if question else ""

        # Ajustement de la classe de la réponse
        self.colonnes[len(self.colonnes)-1].classe = self.Get_classe_reponse(question=question)

        # Suppression des filtres associés à une autre question
        if self.Get_categorie():
            filtres_liste = context['filtres_liste']
            context['filtres_liste'] = []
            for filtre in filtres_liste:
                try:
                    idquestion = int(filtre["options"].split("=")[1])
                except:
                    idquestion = None
                if filtre["champ"] != "reponse" or idquestion == int(self.Get_categorie()):
                    context['filtres_liste'].append(filtre)
                else:
                    FiltreListe.objects.get(pk=filtre["idfiltre"]).delete()

        return context

    def Get_categorie(self):
        return self.kwargs.get("categorie", None)

    def Get_classe_reponse(self, question=None):
        classe = None
        if question:
            if question.controle in ("ligne_texte", "bloc_texte", "liste_deroulante", "liste_deroulante_avancee", "liste_coches"):
                classe = "CharField"
            elif question.controle in ("entier", "slider"):
                classe = "IntegerField"
            elif question.controle in ("decimal", "montant"):
                classe = "DecimalField"
            elif question.controle == "case_coche":
                classe = "BooleanField"
        return classe

    def Formate_reponse(self, reponse=None):
        if reponse and isinstance(reponse, str):
            if reponse.lower() == "oui": return "<small class='badge badge-pill badge-success'><i class='fa fa-check margin-r-5'></i>Oui</small>"
            if reponse.lower() == "non": return "<small class='badge badge-pill badge-danger'><i class='fa fa-remove margin-r-5'></i>Non</small>"
        return reponse
