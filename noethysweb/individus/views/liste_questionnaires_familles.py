# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from core.models import QuestionnaireReponse
from core.views.customdatatable import CustomDatatable, Colonne, ColonneAction
from core.views import crud, liste_questionnaires_base


class Page(crud.Page):
    model = QuestionnaireReponse
    url_liste = "questionnaires_familles_liste"
    description_liste = "Voici ci-dessous la liste des questionnaires familiaux. Commencez par sélectionner une question dans la liste déroulante."


class Liste(Page, liste_questionnaires_base.Liste):
    categorie_question = "famille"
    filtres = ["fgenerique:famille", "reponse"]
    colonnes = [
        Colonne(code="famille__nom", label="Famille", classe="CharField", label_filtre="Nom"),
        Colonne(code="reponse", label="Réponse", classe="BooleanField", label_filtre="Valeur"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Questionnaires"
        context['box_titre'] = "Liste des questionnaires familiaux"
        return context

    def Get_customdatatable(self):
        lignes = []
        for reponse in QuestionnaireReponse.objects.select_related("question", "famille").filter(Q(question=self.Get_categorie()) & self.Get_filtres("Q")):
            lignes.append([
                reponse.famille.nom,
                self.Formate_reponse(reponse.Get_reponse_fr()),
            ])
        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())
