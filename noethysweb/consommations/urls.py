# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from parametrage.views import calendrier
from consommations.views import grille, gestionnaire, suivi_consommations, etat_global, synthese_consommations, liste_attente, liste_absences, edition_liste_conso, \
                                pointeuse, liste_consommations, liste_repas
from core.decorators import secure_ajax


urlpatterns = [

    # Table des matières
    path('consommations/', toc.Toc.as_view(menu_code="consommations_toc"), name='consommations_toc'),

    # Gestion des consommations
    path('consommations/edition_liste_conso', edition_liste_conso.View.as_view(), name='edition_liste_conso'),
    path('consommations/gestionnaire_consommations', gestionnaire.View.as_view(), name='gestionnaire_conso'),
    path('consommations/pointeuse_consommations', pointeuse.View.as_view(), name='pointeuse_conso'),
    path('consommations/suivi_consommations', suivi_consommations.View.as_view(), name='suivi_consommations'),

    path('consommations/liste_consommations', liste_consommations.Liste.as_view(), name='liste_consommations'),
    # path('consommations/consommations_supprimer_plusieurs/<str:listepk>', liste_consommations.Supprimer_plusieurs.as_view(), name='consommations_supprimer_plusieurs'),

    # Listes par état
    path('consommations/liste_attente', liste_attente.View.as_view(etat="attente"), name='liste_attente'),
    path('consommations/liste_refus', liste_attente.View.as_view(etat="refus"), name='liste_refus'),
    path('consommations/liste_absences', liste_absences.Liste.as_view(), name='liste_absences'),
    path('consommations/traitement_automatique', liste_attente.Traitement_automatique, name='liste_attente_traitement_automatique'),
    path('consommations/liste_repas', liste_repas.View.as_view(), name='liste_repas'),

    # Analyse
    path('consommations/etat_global', etat_global.View.as_view(), name='etat_global'),
    path('consommations/synthese_consommations', synthese_consommations.View.as_view(), name='synthese_consommations'),

    # AJAX
    path('consommations/get_vacances', secure_ajax(calendrier.Get_vacances), name='ajax_get_vacances'),
    path('consommations/get_individus', secure_ajax(grille.Get_individus), name='ajax_get_individus'),
    path('consommations/facturer', secure_ajax(grille.Facturer), name='ajax_facturer'),
    path('consommations/traitement_lot', secure_ajax(grille.Valider_traitement_lot), name='ajax_traitement_lot'),
    path('consommations/impression_pdf', secure_ajax(grille.Impression_pdf), name='ajax_grille_impression_pdf'),
    path('consommations/get_suivi_consommations', secure_ajax(suivi_consommations.Get_suivi_consommations), name='ajax_get_suivi_consommations'),
    path('consommations/get_activites', secure_ajax(suivi_consommations.Get_activites), name='ajax_get_activites'),
    path('consommations/etat_global/appliquer_parametres', secure_ajax(etat_global.Appliquer_parametres), name='ajax_etat_global_appliquer_parametres'),
    path('consommations/etat_global/generer_pdf', secure_ajax(etat_global.Generer_pdf), name='ajax_etat_global_generer_pdf'),
    path('consommations/edition_liste_conso/generer_pdf', secure_ajax(edition_liste_conso.Generer_pdf), name='ajax_edition_liste_conso_generer_pdf'),


]
