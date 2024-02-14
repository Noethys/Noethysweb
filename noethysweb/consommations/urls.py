# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from parametrage.views import calendrier
from consommations.forms import grille_forfaits
from consommations.views import grille, gestionnaire, suivi_consommations, etat_global, synthese_consommations, liste_attente, liste_absences, edition_liste_conso, \
                                pointeuse, liste_consommations, liste_repas, etat_nomin, liste_durees, consommations_traitement_lot, evolution_reservations, \
                                detail_consommations #, pointeuse_barcodes
from core.decorators import secure_ajax


urlpatterns = [

    # Table des matières
    path('consommations/', toc.Toc.as_view(menu_code="consommations_toc"), name='consommations_toc'),

    # Gestion des consommations
    path('consommations/edition_liste_conso', edition_liste_conso.View.as_view(), name='edition_liste_conso'),
    path('consommations/gestionnaire_consommations', gestionnaire.View.as_view(), name='gestionnaire_conso'),
    path('consommations/pointeuse_consommations', pointeuse.View.as_view(), name='pointeuse_conso'),
    # path('consommations/pointeuse_barcodes', pointeuse_barcodes.View.as_view(), name='pointeuse_barcodes'),
    path('consommations/suivi_consommations', suivi_consommations.View.as_view(), name='suivi_consommations'),
    path('consommations/detail_consommations/<str:donnee>', detail_consommations.View.as_view(), name='detail_consommations'),

    path('consommations/liste_consommations', liste_consommations.Liste.as_view(), name='liste_consommations'),
    path('consommations/liste_consommations/modifier/<int:pk>', liste_consommations.Modifier.as_view(), name='liste_consommations_modifier'),
    path('consommations/liste_consommations/supprimer/<int:pk>', liste_consommations.Supprimer.as_view(), name='liste_consommations_supprimer'),
    path('consommations/consommations_supprimer_plusieurs/<str:listepk>', liste_consommations.Supprimer_plusieurs.as_view(), name='consommations_supprimer_plusieurs'),

    path('consommations/consommations_traitement_lot/selection_activite', consommations_traitement_lot.Selection_activite.as_view(), name='consommations_traitement_lot'),
    path('consommations/consommations_traitement_lot/liste/<int:idactivite>', consommations_traitement_lot.Liste.as_view(), name='consommations_traitement_lot_liste'),

    # Listes par état
    path('consommations/liste_attente', liste_attente.View.as_view(etat="attente"), name='liste_attente'),
    path('consommations/liste_refus', liste_attente.View.as_view(etat="refus"), name='liste_refus'),
    path('consommations/liste_absences', liste_absences.Liste.as_view(), name='liste_absences'),
    path('consommations/traitement_automatique', liste_attente.Traitement_automatique, name='liste_attente_traitement_automatique'),
    path('consommations/liste_repas', liste_repas.View.as_view(), name='liste_repas'),
    path('consommations/liste_durees', liste_durees.View.as_view(), name='liste_durees'),

    # Analyse
    path('consommations/etat_global', etat_global.View.as_view(), name='etat_global'),
    path('consommations/etat_nomin', etat_nomin.View.as_view(), name='etat_nomin'),
    path('consommations/synthese_consommations', synthese_consommations.View.as_view(), name='synthese_consommations'),
    path('consommations/evolution_reservations', evolution_reservations.View.as_view(), name='evolution_reservations'),

    # AJAX
    path('consommations/get_vacances', secure_ajax(calendrier.Get_vacances), name='ajax_get_vacances'),
    path('consommations/get_individus', secure_ajax(grille.Get_individus), name='ajax_get_individus'),
    path('consommations/get_familles', secure_ajax(grille_forfaits.Get_familles), name='ajax_get_familles'),
    path('consommations/get_forfaits_disponibles', secure_ajax(grille_forfaits.Get_forfaits_disponibles), name='ajax_get_forfaits_disponibles'),
    path('consommations/creation_forfait', secure_ajax(grille_forfaits.Creation_forfait), name='ajax_creation_forfait'),
    path('consommations/facturer', secure_ajax(grille.Facturer), name='ajax_facturer'),
    path('consommations/traitement_lot', secure_ajax(grille.Valider_traitement_lot), name='ajax_traitement_lot'),
    path('consommations/impression_pdf', secure_ajax(grille.Impression_pdf), name='ajax_grille_impression_pdf'),
    path('consommations/get_suivi_consommations', secure_ajax(suivi_consommations.Get_suivi_consommations), name='ajax_get_suivi_consommations'),
    path('consommations/get_activites', secure_ajax(suivi_consommations.Get_activites), name='ajax_get_activites'),
    path('consommations/etat_global/appliquer_parametres', secure_ajax(etat_global.Appliquer_parametres), name='ajax_etat_global_appliquer_parametres'),
    path('consommations/etat_global/generer_pdf', secure_ajax(etat_global.Generer_pdf), name='ajax_etat_global_generer_pdf'),
    path('consommations/edition_liste_conso/generer_pdf', secure_ajax(edition_liste_conso.Generer_pdf), name='ajax_edition_liste_conso_generer_pdf'),
    path('consommations/edition_liste_conso/exporter_excel', secure_ajax(edition_liste_conso.Exporter_excel), name='ajax_edition_liste_conso_exporter_excel'),
    # path('consommations/pointeuse_barcodes/on_scan_individu', secure_ajax(pointeuse_barcodes.On_scan_individu), name='ajax_consommations_on_scan_individu'),
    path('consommations/consommations_traitement_lot', secure_ajax(consommations_traitement_lot.Appliquer), name='ajax_consommations_traitement_lot'),
    path('consommations/liste_consommations/dissocier_prestation', secure_ajax(liste_consommations.Dissocier_prestation), name='ajax_consommations_dissocier_prestation'),
    path('consommations/attribution_manuelle', secure_ajax(liste_attente.Attribution_manuelle), name='liste_attente_attribution_manuelle'),
]
