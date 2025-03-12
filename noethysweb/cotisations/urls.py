# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from cotisations.views import liste_cotisations, liste_cotisations_disponibles, depots_cotisations, saisie_lot_cotisations, liste_cotisations_manquantes, \
                            cotisations_impression, cotisations_email, depots_cotisations_selection, saisie_lot_cotisations_individus, saisie_lot_cotisations_familles

urlpatterns = [

    # Table des matières
    path('cotisations/', toc.Toc.as_view(menu_code="cotisations_toc"), name='cotisations_toc'),

    # Etat des cotisations
    path('cotisations/liste', liste_cotisations.Liste.as_view(), name='cotisations_liste'),
    path('cotisations/cotisations_impression', cotisations_impression.Liste.as_view(), name='cotisations_impression'),
    path('cotisations/cotisations_email', cotisations_email.Liste.as_view(), name='cotisations_email'),

    path('cotisations/supprimer_plusieurs/<str:listepk>', liste_cotisations.Supprimer_plusieurs.as_view(), name='cotisations_supprimer_plusieurs'),
    path('individus/liste_cotisations_manquantes', liste_cotisations_manquantes.Liste.as_view(), name='liste_cotisations_manquantes'),

    # Gestion des cotisations
    path('cotisations/saisie_lot_cotisations', saisie_lot_cotisations.Selection_type_cotisation.as_view(), name='saisie_lot_cotisations'),
    path('cotisations/saisie_lot_cotisations/individus/<int:idtype_cotisation>/<int:idunite_cotisation>/<int:affichage_beneficiaires>', saisie_lot_cotisations_individus.Liste.as_view(), name='saisie_lot_cotisations_individus'),
    path('cotisations/saisie_lot_cotisations/familles/<int:idtype_cotisation>/<int:idunite_cotisation>/<int:affichage_beneficiaires>', saisie_lot_cotisations_familles.Liste.as_view(), name='saisie_lot_cotisations_familles'),

    # Dépôts de cotisations
    path('cotisations/liste_cotisations_disponibles', liste_cotisations_disponibles.Liste.as_view(), name='liste_cotisations_disponibles'),

    path('cotisations/depots_cotisations/liste', depots_cotisations.Liste.as_view(), name='depots_cotisations_liste'),
    path('cotisations/depots_cotisations/ajouter', depots_cotisations.Ajouter.as_view(), name='depots_cotisations_ajouter'),
    path('cotisations/depots_cotisations/modifier/<int:pk>', depots_cotisations.Modifier.as_view(), name='depots_cotisations_modifier'),
    path('cotisations/depots_cotisations/supprimer/<int:pk>', depots_cotisations.Supprimer.as_view(), name='depots_cotisations_supprimer'),
    path('cotisations/depots_cotisations/consulter/<int:pk>', depots_cotisations.Consulter.as_view(), name='depots_cotisations_consulter'),
    path('cotisations/depots_cotisations/cotisations/ajouter/<int:iddepot>', depots_cotisations_selection.Liste.as_view(), name='depots_cotisations_ajouter_cotisation'),
    path('cotisations/depots_cotisations/cotisations/supprimer/<int:iddepot>/<int:pk>', depots_cotisations.Supprimer_cotisation.as_view(), name='depots_cotisations_supprimer_cotisation'),
    path('cotisations/depots_cotisations/cotisations/supprimer_plusieurs/<int:iddepot>/<str:listepk>', depots_cotisations.Supprimer_plusieurs_cotisations.as_view(), name='depots_cotisations_supprimer_plusieurs_cotisations'),

    # AJAX
    path('cotisations/saisie_lot_cotisations/appliquer', secure_ajax(saisie_lot_cotisations.Appliquer), name='ajax_saisie_lot_cotisations_appliquer'),
    path('cotisations/cotisations_impression_pdf', secure_ajax(cotisations_impression.Impression_pdf), name='ajax_cotisations_impression_pdf'),
    path('cotisations/cotisations_email_pdf', secure_ajax(cotisations_email.Impression_pdf), name='ajax_cotisations_email_pdf'),

]
