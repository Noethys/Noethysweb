# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from comptabilite.views import operations_tresorerie, operations_budgetaires, liste_comptes, liste_virements, suivi_budget, suivi_tresorerie, \
                                rapprochements, rapprochements_selection, achats_demandes, achats_articles, edition_liste_achats, suivi_achats, \
                                planning_achats


urlpatterns = [

    # Table des matières
    path('comptabilite/', toc.Toc.as_view(menu_code="comptabilite_toc"), name='comptabilite_toc'),

    # Comptes
    path('comptabilite/liste_comptes', liste_comptes.Liste.as_view(), name='comptabilite_liste_comptes'),

    # Opérations de trésorerie
    path('comptabilite/operations_tresorerie/liste', operations_tresorerie.Liste.as_view(), name='operations_tresorerie_liste'),
    path('comptabilite/operations_tresorerie/liste/<int:categorie>', operations_tresorerie.Liste.as_view(), name='operations_tresorerie_liste'),
    path('comptabilite/operations_tresorerie/ajouter_debit/<int:categorie>', operations_tresorerie.Ajouter.as_view(type="debit"), name='operations_tresorerie_ajouter_debit'),
    path('comptabilite/operations_tresorerie/ajouter_credit/<int:categorie>', operations_tresorerie.Ajouter.as_view(type="credit"), name='operations_tresorerie_ajouter_credit'),
    path('comptabilite/operations_tresorerie/modifier/<int:categorie>/<int:pk>', operations_tresorerie.Modifier.as_view(), name='operations_tresorerie_modifier'),
    path('comptabilite/operations_tresorerie/supprimer/<int:categorie>/<int:pk>', operations_tresorerie.Supprimer.as_view(), name='operations_tresorerie_supprimer'),

    # Opérations budgétaires
    path('comptabilite/operations_budgetaires/liste', operations_budgetaires.Liste.as_view(), name='operations_budgetaires_liste'),
    path('comptabilite/operations_budgetaires/liste/<int:categorie>', operations_budgetaires.Liste.as_view(), name='operations_budgetaires_liste'),
    path('comptabilite/operations_budgetaires/ajouter_debit/<int:categorie>', operations_budgetaires.Ajouter.as_view(type="debit"), name='operations_budgetaires_ajouter_debit'),
    path('comptabilite/operations_budgetaires/ajouter_credit/<int:categorie>', operations_budgetaires.Ajouter.as_view(type="credit"), name='operations_budgetaires_ajouter_credit'),
    path('comptabilite/operations_budgetaires/modifier/<int:categorie>/<int:pk>', operations_budgetaires.Modifier.as_view(), name='operations_budgetaires_modifier'),
    path('comptabilite/operations_budgetaires/supprimer/<int:categorie>/<int:pk>', operations_budgetaires.Supprimer.as_view(), name='operations_budgetaires_supprimer'),

    # Liste des virements
    path('comptabilite/virements/liste', liste_virements.Liste.as_view(), name='virements_liste'),
    path('comptabilite/virements/ajouter', liste_virements.Ajouter.as_view(), name='virements_ajouter'),
    path('comptabilite/virements/modifier/<int:pk>', liste_virements.Modifier.as_view(), name='virements_modifier'),
    path('comptabilite/virements/supprimer/<int:pk>', liste_virements.Supprimer.as_view(), name='virements_supprimer'),

    # Analyse
    path('comptabilite/suivi_budget', suivi_budget.View.as_view(), name='suivi_budget'),
    path('comptabilite/suivi_tresorerie', suivi_tresorerie.View.as_view(), name='suivi_tresorerie'),
    path('comptabilite/suivi_tresorerie/<int:categorie>', suivi_tresorerie.View.as_view(), name='suivi_tresorerie'),

    # Rapprochement bancaire
    path('comptabilite/rapprochement/liste', rapprochements.Liste.as_view(), name='rapprochements_liste'),
    path('comptabilite/rapprochement/ajouter', rapprochements.Ajouter.as_view(), name='rapprochements_ajouter'),
    path('comptabilite/rapprochement/modifier/<int:pk>', rapprochements.Modifier.as_view(), name='rapprochements_modifier'),
    path('comptabilite/rapprochement/supprimer/<int:pk>', rapprochements.Supprimer.as_view(), name='rapprochements_supprimer'),
    path('comptabilite/rapprochement/consulter/<int:pk>', rapprochements.Consulter.as_view(), name='rapprochements_consulter'),
    path('comptabilite/rapprochement/operations/ajouter/<int:idreleve>', rapprochements_selection.Liste.as_view(), name='rapprochements_ajouter_operation'),
    path('comptabilite/rapprochement/operations/supprimer/<int:idreleve>/<int:pk>', rapprochements.Supprimer_operation.as_view(), name='rapprochements_supprimer_operation'),
    path('comptabilite/rapprochement/operations/supprimer_plusieurs/<int:idreleve>/<str:listepk>', rapprochements.Supprimer_plusieurs_operations.as_view(), name='rapprochements_supprimer_plusieurs_operations'),

    # Achats : Demandes
    path('comptabilite/achats_demandes/liste', achats_demandes.Liste.as_view(), name='achats_demandes_liste'),
    path('comptabilite/achats_demandes/ajouter', achats_demandes.Ajouter.as_view(), name='achats_demandes_ajouter'),
    path('comptabilite/achats_demandes/modifier/<int:pk>', achats_demandes.Modifier.as_view(), name='achats_demandes_modifier'),
    path('comptabilite/achats_demandes/supprimer/<int:pk>', achats_demandes.Supprimer.as_view(), name='achats_demandes_supprimer'),
    path('comptabilite/suivi_achats', suivi_achats.View.as_view(), name='suivi_achats'),
    path('comptabilite/planning_achats', planning_achats.View.as_view(), name='planning_achats'),

    # Achats : Articles
    path('comptabilite/achats_articles/liste', achats_articles.Liste.as_view(), name='achats_articles_liste'),
    path('comptabilite/achats_articles/modifier/<int:pk>', achats_articles.Modifier.as_view(), name='achats_articles_modifier'),
    path('comptabilite/achats_articles/supprimer/<int:pk>', achats_articles.Supprimer.as_view(), name='achats_articles_supprimer'),

    # Edition de la liste des achats
    path('comptabilite/edition_liste_achats', edition_liste_achats.View.as_view(), name='edition_liste_achats'),

    # AJAX
    path('comptabilite/operations_tresorerie/get_form_ventilation', secure_ajax(operations_tresorerie.Get_form_ventilation), name='ajax_operations_tresorerie_form_ventilation'),
    path('comptabilite/achats_demandes/get_form_article', secure_ajax(achats_demandes.Get_form_article), name='ajax_achats_demandes_form_article'),
    path('comptabilite/achats_articles/modifier_achete', secure_ajax(achats_articles.Modifier_achete), name='ajax_modifier_article_achete'),
    path('comptabilite/edition_liste_achats/generer_pdf', secure_ajax(edition_liste_achats.Generer_pdf), name='ajax_edition_liste_achats_generer_pdf'),
    path('comptabilite/suivi_achats_get_form_parametres', secure_ajax(suivi_achats.Get_form_parametres), name='ajax_suivi_achats_get_form_parametres'),
    path('comptabilite/suivi_achats_valider_form_parametres', secure_ajax(suivi_achats.Valider_form_parametres), name='ajax_suivi_achats_valider_form_parametres'),
    path('comptabilite/planning_achats/get_achats', secure_ajax(planning_achats.Get_achats), name='ajax_planning_achats_get_achats'),
    path('comptabilite/planning_achats/get_form_detail_achat', secure_ajax(planning_achats.Get_form_detail_achat), name='ajax_planning_achats_get_form_detail_achat'),
    path('comptabilite/planning_achats/valid_form_detail_achat', secure_ajax(planning_achats.Valid_form_detail_achat), name='ajax_planning_achats_valid_form_detail_achat'),
    path('comptabilite/planning_achats/modifier_achat', secure_ajax(planning_achats.Modifier_achat), name='ajax_planning_achats_modifier_achat'),
    path('comptabilite/planning_achats/supprimer_achat', secure_ajax(planning_achats.Supprimer_achat), name='ajax_planning_achats_supprimer_achat'),

]
