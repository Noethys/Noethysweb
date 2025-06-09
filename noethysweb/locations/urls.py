# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from locations.views import liste_locations, locations_impression, locations_email, planning_locations, synthese_locations

urlpatterns = [

    # Table des matières
    path('locations/', toc.Toc.as_view(menu_code="locations_toc"), name='locations_toc'),

    # Etat des locations
    path('locations/liste', liste_locations.Liste.as_view(), name='locations_liste'),
    path('locations/locations_impression', locations_impression.Liste.as_view(), name='locations_impression'),
    path('locations/locations_email', locations_email.Liste.as_view(), name='locations_email'),
    path('locations/supprimer_plusieurs/<str:listepk>', liste_locations.Supprimer_plusieurs.as_view(), name='locations_supprimer_plusieurs'),

    # Gestion des locations
    path('locations/planning_locations', planning_locations.View.as_view(), name='planning_locations'),

    # Analyse
    path('locations/synthese_locations', synthese_locations.View.as_view(), name='synthese_locations'),

    # AJAX
    path('locations/locations_impression_pdf', secure_ajax(locations_impression.Impression_pdf), name='ajax_locations_impression_pdf'),
    path('locations/locations_email_pdf', secure_ajax(locations_email.Impression_pdf), name='ajax_locations_email_pdf'),
    path('locations/planning/get_produits', secure_ajax(planning_locations.Get_produits), name='ajax_planning_locations_get_produits'),
    path('locations/planning/get_locations', secure_ajax(planning_locations.Get_locations), name='ajax_planning_locations_get_locations'),
    path('locations/planning/get_form_detail_location', secure_ajax(planning_locations.Get_form_detail_location), name='ajax_planning_locations_get_form_detail_location'),
    path('locations/planning/valid_form_detail_location', secure_ajax(planning_locations.Valid_form_detail_location), name='ajax_planning_locations_valid_form_detail_location'),
    path('locations/planning/modifier_location', secure_ajax(planning_locations.Modifier_location), name='ajax_planning_locations_modifier_location'),
    path('locations/planning/supprimer_location', secure_ajax(planning_locations.Supprimer_location), name='ajax_planning_locations_supprimer_location'),
    path('locations/planning/supprimer_occurences', secure_ajax(planning_locations.Supprimer_occurences), name='ajax_planning_locations_supprimer_occurences'),
    path('locations/planning/get_form_parametres', secure_ajax(planning_locations.Get_form_parametres), name='ajax_planning_locations_get_form_parametres'),
    path('locations/planning/valid_form_parametres', secure_ajax(planning_locations.Valid_form_parametres), name='ajax_planning_locations_valid_form_parametres'),
]
