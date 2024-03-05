# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from core.models import QuestionnaireReponse
from core.views.customdatatable import CustomDatatable, Colonne
from core.views import crud, liste_questionnaires_base


class Page(crud.Page):
    model = QuestionnaireReponse
    url_liste = "questionnaires_individus_liste"
    description_liste = "Voici ci-dessous la liste des questionnaires individuels. Commencez par sélectionner une question dans la liste déroulante."


class Liste(Page, liste_questionnaires_base.Liste):
    categorie_question = "individu"
    filtres = ["igenerique:individu", "reponse"]
    colonnes = [
        Colonne(code="individu__nom", label="Nom", classe="CharField", label_filtre="Nom"),
        Colonne(code="individu__prenom", label="Prénom", classe="CharField", label_filtre="Prénom"),
        Colonne(code="reponse", label="Réponse", classe="BooleanField", label_filtre="Valeur"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Questionnaires"
        context['box_titre'] = "Liste des questionnaires individuels"
        return context

    def Get_customdatatable(self):
        lignes = []
        for reponse in QuestionnaireReponse.objects.select_related("question", "individu").filter(Q(question=self.Get_categorie()) & self.Get_filtres("Q")):
            lignes.append([
                reponse.individu.nom,
                reponse.individu.prenom,
                self.Formate_reponse(reponse.Get_reponse_fr()),
            ])
        return CustomDatatable(colonnes=self.colonnes, lignes=lignes)#, filtres=self.Get_filtres())
