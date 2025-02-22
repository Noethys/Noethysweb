# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import Verifie_ventilation
from core.decorators import secure_ajax
from facturation.views import factures_generation, liste_prestations, liste_factures, liste_deductions, liste_soldes, synthese_impayes, \
                                synthese_prestations, liste_tarifs, rappels_generation, liste_rappels, factures_impression, factures_email, \
                                rappels_impression, rappels_email, lots_pes, lots_pes_factures, recalculer_prestations, edition_prestations, \
                                lots_prelevements, lots_prelevements_factures, attestations_fiscales_generation, attestations_fiscales_impression, \
                                attestations_fiscales_email, liste_attestations_fiscales, liste_aides, solder_impayes, edition_recap_factures, \
                                factures_modifier, export_ecritures_cloe, saisie_lot_forfaits_credits, synthese_deductions, export_ecritures_cwe, \
                                liste_factures_detaillees

urlpatterns = [

    # Table des matières
    path('facturation/', toc.Toc.as_view(menu_code="facturation_toc"), name='facturation_toc'),

    # Factures
    path('facturation/factures_generation', Verifie_ventilation(factures_generation.View.as_view()), name='factures_generation'),
    path('facturation/factures_generation/<int:idfamille>', factures_generation.View.as_view(), name='factures_generation'),
    path('facturation/liste_factures', liste_factures.Liste.as_view(), name='liste_factures'),
    path('facturation/liste_factures_detaillees', liste_factures_detaillees.Liste.as_view(), name='liste_factures_detaillees'),
    path('facturation/liste_factures/supprimer/<int:pk>', liste_factures.Supprimer.as_view(), name='liste_factures_supprimer'),
    path('facturation/liste_factures/supprimer_plusieurs/<str:listepk>', liste_factures.Supprimer_plusieurs.as_view(), name='liste_factures_supprimer_plusieurs'),
    path('facturation/liste_factures/annuler/<int:pk>', liste_factures.Annuler.as_view(), name='liste_factures_annuler'),
    path('facturation/liste_factures/annuler_plusieurs/<str:listepk>', liste_factures.Annuler_plusieurs.as_view(), name='liste_factures_annuler_plusieurs'),
    path('facturation/factures_impression', factures_impression.Liste.as_view(), name='factures_impression'),
    path('facturation/factures_email', factures_email.Liste.as_view(), name='factures_email'),
    path('facturation/edition_recap_factures', edition_recap_factures.View.as_view(), name='edition_recap_factures'),
    path('facturation/factures_modifier', factures_modifier.Liste.as_view(), name='factures_modifier'),

    # Rappels
    path('facturation/rappels_generation', Verifie_ventilation(rappels_generation.View.as_view()), name='rappels_generation'),
    path('facturation/rappels_generation/<int:idfamille>', rappels_generation.View.as_view(), name='rappels_generation'),
    path('facturation/liste_rappels', liste_rappels.Liste.as_view(), name='liste_rappels'),
    path('facturation/rappels_impression', rappels_impression.Liste.as_view(), name='rappels_impression'),
    path('facturation/rappels_email', rappels_email.Liste.as_view(), name='rappels_email'),
    path('facturation/rappels/supprimer/<int:pk>', liste_rappels.Supprimer.as_view(), name='rappels_supprimer'),
    path('facturation/rappels/<str:listepk>', liste_rappels.Supprimer_plusieurs.as_view(), name='rappels_supprimer_plusieurs'),

    # Attestations fiscales
    path('facturation/attestations_fiscales_generation', Verifie_ventilation(attestations_fiscales_generation.View.as_view()), name='attestations_fiscales_generation'),
    path('facturation/attestations_fiscales_generation/<int:idfamille>', attestations_fiscales_generation.View.as_view(), name='attestations_fiscales_generation'),
    path('facturation/liste_attestations_fiscales', liste_attestations_fiscales.Liste.as_view(), name='liste_attestations_fiscales'),
    path('facturation/attestations_fiscales_impression', attestations_fiscales_impression.Liste.as_view(), name='attestations_fiscales_impression'),
    path('facturation/attestations_fiscales_email', attestations_fiscales_email.Liste.as_view(), name='attestations_fiscales_email'),
    path('facturation/attestations_fiscales_email/supprimer/<int:pk>', liste_attestations_fiscales.Supprimer.as_view(), name='attestations_fiscales_supprimer'),
    path('facturation/attestations_fiscales_supprimer_plusieurs/<str:listepk>', liste_attestations_fiscales.Supprimer_plusieurs.as_view(), name='attestations_fiscales_supprimer_plusieurs'),

    # Lots PES
    path('facturation/lots_pes/liste', lots_pes.Liste.as_view(), name='lots_pes_liste'),
    path('facturation/lots_pes/creer', lots_pes.Creer.as_view(), name='lots_pes_creer'),
    path('facturation/lots_pes/ajouter/<int:idmodele>/<int:assistant>', lots_pes.Ajouter.as_view(), name='lots_pes_ajouter'),
    path('facturation/lots_pes/modifier/<int:pk>', lots_pes.Modifier.as_view(), name='lots_pes_modifier'),
    path('facturation/lots_pes/supprimer/<int:pk>', lots_pes.Supprimer.as_view(), name='lots_pes_supprimer'),
    path('facturation/lots_pes/consulter/<int:pk>', lots_pes.Consulter.as_view(), name='lots_pes_consulter'),
    path('facturation/lots_pes/pieces/ajouter/<int:idlot>', lots_pes_factures.Liste.as_view(), name='lots_pes_ajouter_piece'),
    path('facturation/lots_pes/pieces/modifier/<int:idlot>/<int:pk>', lots_pes.Modifier_piece.as_view(), name='lots_pes_modifier_piece'),
    path('facturation/lots_pes/pieces/supprimer/<int:idlot>/<int:pk>', lots_pes.Supprimer_piece.as_view(), name='lots_pes_supprimer_piece'),
    path('facturation/lots_pes/pieces/supprimer_plusieurs/<int:idlot>/<str:listepk>', lots_pes.Supprimer_plusieurs_pieces.as_view(), name='lots_pes_supprimer_plusieurs_pieces'),

    # Lots prélèvements
    path('facturation/lots_prelevements/liste', lots_prelevements.Liste.as_view(), name='lots_prelevements_liste'),
    path('facturation/lots_prelevements/creer', lots_prelevements.Creer.as_view(), name='lots_prelevements_creer'),
    path('facturation/lots_prelevements/ajouter/<int:idmodele>/<int:assistant>', lots_prelevements.Ajouter.as_view(), name='lots_prelevements_ajouter'),
    path('facturation/lots_prelevements/modifier/<int:pk>', lots_prelevements.Modifier.as_view(), name='lots_prelevements_modifier'),
    path('facturation/lots_prelevements/supprimer/<int:pk>', lots_prelevements.Supprimer.as_view(), name='lots_prelevements_supprimer'),
    path('facturation/lots_prelevements/consulter/<int:pk>', lots_prelevements.Consulter.as_view(), name='lots_prelevements_consulter'),
    path('facturation/lots_prelevements/pieces/ajouter/<int:idlot>', lots_prelevements_factures.Liste.as_view(), name='lots_prelevements_ajouter_piece'),
    path('facturation/lots_prelevements/pieces/ajouter_manuel/<int:idlot>', lots_prelevements.Ajouter_piece_manuelle.as_view(), name='lots_prelevements_ajouter_piece_manuelle'),
    path('facturation/lots_prelevements/pieces/modifier/<int:idlot>/<int:pk>', lots_prelevements.Modifier_piece.as_view(), name='lots_prelevements_modifier_piece'),
    path('facturation/lots_prelevements/pieces/supprimer/<int:idlot>/<int:pk>', lots_prelevements.Supprimer_piece.as_view(), name='lots_prelevements_supprimer_piece'),
    path('facturation/lots_prelevements/pieces/supprimer_plusieurs/<int:idlot>/<str:listepk>', lots_prelevements.Supprimer_plusieurs_pieces.as_view(), name='lots_prelevements_supprimer_plusieurs_pieces'),

    # Tarifs
    path('facturation/liste_tarifs', liste_tarifs.View.as_view(), name='liste_tarifs'),

    # Prestations
    path('facturation/liste_prestations', liste_prestations.Liste.as_view(), name='liste_prestations'),
    path('facturation/prestations_supprimer_plusieurs/<str:listepk>', liste_prestations.Supprimer_plusieurs.as_view(), name='prestations_supprimer_plusieurs'),
    path('facturation/liste_soldes', liste_soldes.View.as_view(), name='liste_soldes'),
    path('facturation/synthese_prestations', synthese_prestations.View.as_view(), name='synthese_prestations'),
    path('facturation/edition_prestations', edition_prestations.View.as_view(), name='edition_prestations'),
    path('facturation/recalculer_prestations', recalculer_prestations.View.as_view(), name='recalculer_prestations'),
    path('facturation/saisie_lot_forfaits_credits', saisie_lot_forfaits_credits.View.as_view(), name='saisie_lot_forfaits_credits'),

    # Déductions
    path('facturation/liste_deductions', liste_deductions.Liste.as_view(), name='liste_deductions'),
    path('facturation/synthese_deductions', synthese_deductions.View.as_view(), name='synthese_deductions'),

    # Aides
    path('facturation/aides/liste', liste_aides.Liste.as_view(), name='aides_liste'),

    # Impayés
    path('facturation/synthese_impayes', Verifie_ventilation(synthese_impayes.View.as_view()), name='synthese_impayes'),
    path('facturation/solder_impayes', solder_impayes.View.as_view(), name='solder_impayes'),

    # Export des écritures
    path('facturation/export_ecritures_cloe', export_ecritures_cloe.View.as_view(), name='export_ecritures_cloe'),
    path('facturation/export_ecritures_cwe', export_ecritures_cwe.View.as_view(), name='export_ecritures_cwe'),

    # AJAX
    path('facturation/modifier_lot_factures', secure_ajax(factures_generation.Modifier_lot_factures), name='ajax_modifier_lot_factures'),
    path('facturation/recherche_factures', secure_ajax(factures_generation.Recherche_factures), name='ajax_recherche_factures'),
    path('facturation/generation_factures', secure_ajax(factures_generation.Generation_factures), name='ajax_generation_factures'),
    path('facturation/generation_factures_previsualisation', secure_ajax(factures_generation.Previsualisation_pdf), name='ajax_generation_factures_previsualisation'),
    path('facturation/generation_factures_numero', secure_ajax(factures_generation.Get_prochain_numero), name='ajax_generation_factures_numero'),
    path('facturation/modifier_lot_rappels', secure_ajax(rappels_generation.Modifier_lot_rappels), name='ajax_modifier_lot_rappels'),
    path('facturation/recherche_rappels', secure_ajax(rappels_generation.Recherche_rappels), name='ajax_recherche_rappels'),
    path('facturation/generation_rappels', secure_ajax(rappels_generation.Generation_rappels), name='ajax_generation_rappels'),
    path('facturation/factures_impression_pdf', secure_ajax(factures_impression.Impression_pdf), name='ajax_factures_impression_pdf'),
    path('facturation/factures_email_pdf', secure_ajax(factures_email.Impression_pdf), name='ajax_factures_email_pdf'),
    path('facturation/edition_recap_factures/generer_pdf', secure_ajax(edition_recap_factures.Generer_pdf), name='ajax_edition_recap_factures_generer_pdf'),
    path('facturation/rappels_impression_pdf', secure_ajax(rappels_impression.Impression_pdf), name='ajax_rappels_impression_pdf'),
    path('facturation/rappels_email_pdf', secure_ajax(rappels_email.Impression_pdf), name='ajax_rappels_email_pdf'),
    path('facturation/lots_pes_exporter', secure_ajax(lots_pes.Exporter), name='ajax_lots_pes_exporter'),
    path('facturation/lots_pes_impression_pdf', secure_ajax(lots_pes.Impression_pdf), name='ajax_lots_pes_impression_pdf'),
    path('facturation/lots_pes_actions', secure_ajax(lots_pes.Actions), name='ajax_lots_pes_actions'),
    path('facturation/lots_prelevements_exporter', secure_ajax(lots_prelevements.Exporter), name='ajax_lots_prelevements_exporter'),
    path('facturation/lots_prelevements_impression_pdf', secure_ajax(lots_prelevements.Impression_pdf), name='ajax_lots_prelevements_impression_pdf'),
    path('facturation/lots_prelevements_actions', secure_ajax(lots_prelevements.Actions), name='ajax_lots_prelevements_actions'),
    path('facturation/ajax_recalculer_prestations', secure_ajax(recalculer_prestations.Recalculer), name='ajax_recalculer_prestations'),
    path('facturation/edition_prestations/generer_pdf', secure_ajax(edition_prestations.Generer_pdf), name='ajax_edition_prestations_generer_pdf'),
    path('facturation/modifier_lot_attestations_fiscales', secure_ajax(attestations_fiscales_generation.Modifier_lot_attestations_fiscales), name='ajax_modifier_lot_attestations_fiscales'),
    path('facturation/ajuster_attestations_fiscales', secure_ajax(attestations_fiscales_generation.Ajuster_attestations_fiscales), name='ajax_ajuster_attestations_fiscales'),
    path('facturation/recherche_attestations_fiscales', secure_ajax(attestations_fiscales_generation.Recherche_attestations_fiscales), name='ajax_recherche_attestations_fiscales'),
    path('facturation/generation_attestations_fiscales', secure_ajax(attestations_fiscales_generation.Generation_attestations_fiscales), name='ajax_generation_attestations_fiscales'),
    path('facturation/attestations_fiscales_impression_pdf', secure_ajax(attestations_fiscales_impression.Impression_pdf), name='ajax_attestations_fiscales_impression_pdf'),
    path('facturation/attestations_fiscales_email_pdf', secure_ajax(attestations_fiscales_email.Impression_pdf), name='ajax_attestations_fiscales_email_pdf'),
    path('facturation/ajax_solder_impayes', secure_ajax(solder_impayes.Solder), name='ajax_solder_impayes'),
    path('facturation/ajax_factures_modifier', secure_ajax(factures_modifier.Appliquer), name='ajax_factures_modifier'),
    path('facturation/export_ecritures_cloe/exporter', secure_ajax(export_ecritures_cloe.Exporter), name='ajax_export_ecritures_cloe_exporter'),
    path('facturation/export_ecritures_cwe/exporter', secure_ajax(export_ecritures_cwe.Exporter), name='ajax_export_ecritures_cwe_exporter'),
    path('facturation/ajax_saisie_lot_forfaits_credits_get_tarifs', secure_ajax(saisie_lot_forfaits_credits.Get_tarifs), name='ajax_saisie_lot_forfaits_credits_get_tarifs'),
    path('facturation/ajax_saisie_lot_forfaits_credits_appliquer', secure_ajax(saisie_lot_forfaits_credits.Appliquer), name='ajax_saisie_lot_forfaits_credits_appliquer'),

]
