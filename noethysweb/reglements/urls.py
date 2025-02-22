# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from core.decorators import Verifie_ventilation
from reglements.views import liste_reglements, liste_recus, liste_detaillee_reglements, synthese_modes_reglements, \
                            depots_reglements, depots_reglements_selection, detail_prestations_depot, \
                            liste_reglements_disponibles, corriger_ventilation, liste_paiements, reglements_lot_factures, \
                            detail_ventilations_depots, detail_ventilations_reglements, depots_reglements_avis, edition_ventilations_reglements


urlpatterns = [

    # Table des matières
    path('reglements/', toc.Toc.as_view(menu_code="reglements_toc"), name='reglements_toc'),

    # Règlements
    path('reglements/liste_reglements', liste_reglements.Liste.as_view(), name='liste_reglements'),
    path('reglements/reglements_supprimer_plusieurs/<str:listepk>', liste_reglements.Supprimer_plusieurs.as_view(), name='reglements_supprimer_plusieurs'),
    path('reglements/liste_recus', liste_recus.Liste.as_view(), name='liste_recus'),
    path('reglements/liste_detaillee_reglements', liste_detaillee_reglements.Liste.as_view(), name='liste_detaillee_reglements'),
    path('reglements/reglements_lot_factures', reglements_lot_factures.View.as_view(), name='reglements_lot_factures'),
    path('reglements/detail_ventilations_reglements', Verifie_ventilation(detail_ventilations_reglements.View.as_view()), name='detail_ventilations_reglements'),
    path('reglements/edition_ventilations_reglements', Verifie_ventilation(edition_ventilations_reglements.View.as_view()), name='edition_ventilations_reglements'),
    path('reglements/liste_paiements', liste_paiements.Liste.as_view(), name='liste_paiements'),

    # Analyse
    path('reglements/detail_prestations_depot', Verifie_ventilation(detail_prestations_depot.View.as_view()), name='detail_prestations_depot'),
    path('reglements/detail_ventilations_depots', Verifie_ventilation(detail_ventilations_depots.View.as_view()), name='detail_ventilations_depots'),
    path('reglements/synthese_modes_reglements', Verifie_ventilation(synthese_modes_reglements.View.as_view()), name='synthese_modes_reglements'),

    # Dépôts de règlements
    path('reglements/liste_reglements_disponibles', liste_reglements_disponibles.Liste.as_view(), name='liste_reglements_disponibles'),

    path('reglements/depots_reglements/liste', depots_reglements.Liste.as_view(), name='depots_reglements_liste'),
    path('reglements/depots_reglements/ajouter', depots_reglements.Ajouter.as_view(), name='depots_reglements_ajouter'),
    path('reglements/depots_reglements/modifier/<int:pk>', depots_reglements.Modifier.as_view(), name='depots_reglements_modifier'),
    path('reglements/depots_reglements/supprimer/<int:pk>', depots_reglements.Supprimer.as_view(), name='depots_reglements_supprimer'),
    path('reglements/depots_reglements/consulter/<int:pk>', depots_reglements.Consulter.as_view(), name='depots_reglements_consulter'),
    path('reglements/depots_reglements/reglements/ajouter/<int:iddepot>', depots_reglements_selection.Liste.as_view(), name='depots_reglements_ajouter_reglement'),
    path('reglements/depots_reglements/reglements/supprimer/<int:iddepot>/<int:pk>', depots_reglements.Supprimer_reglement.as_view(), name='depots_reglements_supprimer_reglement'),
    path('reglements/depots_reglements/reglements/supprimer_plusieurs/<int:iddepot>/<str:listepk>', depots_reglements.Supprimer_plusieurs_reglements.as_view(), name='depots_reglements_supprimer_plusieurs_reglements'),
    path('reglements/depots_reglements/reglements/avis/<int:iddepot>', depots_reglements_avis.Liste.as_view(), name='depots_reglements_envoyer_avis'),

    # Ventilation
    path('reglements/corriger_ventilation', corriger_ventilation.View.as_view(), name='corriger_ventilation'),

    # AJAX
    path('facturation/depots_reglements_impression_pdf', secure_ajax(depots_reglements.Impression_pdf), name='ajax_depots_reglements_impression_pdf'),
    path('facturation/edition_ventilations_reglements/generer_pdf', secure_ajax(edition_ventilations_reglements.Generer_pdf), name='ajax_edition_ventilations_reglements_generer_pdf'),
]
