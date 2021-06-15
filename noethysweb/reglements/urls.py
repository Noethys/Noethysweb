# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from core.decorators import Verifie_ventilation
from reglements.views import liste_reglements, liste_recus, liste_detaillee_reglements, synthese_modes_reglements, depots_reglements, detail_prestations_depot, \
                            liste_reglements_disponibles, corriger_ventilation


urlpatterns = [

    # Table des matières
    path('reglements/', toc.Toc.as_view(menu_code="reglements_toc"), name='reglements_toc'),

    # Règlements
    path('reglements/liste_reglements', liste_reglements.Liste.as_view(), name='liste_reglements'),
    path('reglements/reglements_supprimer_plusieurs/<str:listepk>', liste_reglements.Supprimer_plusieurs.as_view(), name='reglements_supprimer_plusieurs'),
    path('reglements/liste_recus', liste_recus.Liste.as_view(), name='liste_recus'),
    path('reglements/liste_detaillee_reglements', liste_detaillee_reglements.Liste.as_view(), name='liste_detaillee_reglements'),

    # Analyse
    path('reglements/detail_prestations_depot', Verifie_ventilation(detail_prestations_depot.View.as_view()), name='detail_prestations_depot'),
    path('reglements/synthese_modes_reglements', Verifie_ventilation(synthese_modes_reglements.View.as_view()), name='synthese_modes_reglements'),

    # Dépôts de règlements
    path('reglements/liste_reglements_disponibles', liste_reglements_disponibles.Liste.as_view(), name='liste_reglements_disponibles'),
    path('reglements/depots_reglements/liste', depots_reglements.Liste.as_view(), name='depots_reglements_liste'),
    path('reglements/depots_reglements/ajouter', depots_reglements.Ajouter.as_view(), name='depots_reglements_ajouter'),
    path('reglements/depots_reglements/modifier/<int:pk>', depots_reglements.Modifier.as_view(), name='depots_reglements_modifier'),
    path('reglements/depots_reglements/supprimer/<int:pk>', depots_reglements.Supprimer.as_view(), name='depots_reglements_supprimer'),

    # Ventilation
    path('reglements/corriger_ventilation', corriger_ventilation.View.as_view(), name='corriger_ventilation'),

    # AJAX
    path('reglements/depots_reglements/modifier_reglements', secure_ajax(depots_reglements.Modifier_reglements), name='ajax_modifier_reglements_depot'),
    path('reglements/depots_reglements/get_stats', secure_ajax(depots_reglements.Get_stats), name='ajax_get_reglements_stats'),

]
