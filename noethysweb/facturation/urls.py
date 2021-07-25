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
                                rappels_impression, rappels_email, lots_pes, lots_pes_factures

urlpatterns = [

    # Table des matières
    path('facturation/', toc.Toc.as_view(menu_code="facturation_toc"), name='facturation_toc'),

    # Factures
    path('facturation/factures_generation', Verifie_ventilation(factures_generation.View.as_view()), name='factures_generation'),
    path('facturation/factures_generation/<int:idfamille>', factures_generation.View.as_view(), name='factures_generation'),
    path('facturation/liste_factures', liste_factures.Liste.as_view(), name='liste_factures'),
    path('facturation/factures_impression', Verifie_ventilation(factures_impression.Liste.as_view()), name='factures_impression'),
    path('facturation/factures_email', Verifie_ventilation(factures_email.Liste.as_view()), name='factures_email'),

    # Rappels
    path('facturation/rappels_generation', Verifie_ventilation(rappels_generation.View.as_view()), name='rappels_generation'),
    path('facturation/rappels_generation/<int:idfamille>', rappels_generation.View.as_view(), name='rappels_generation'),
    path('facturation/liste_rappels', liste_rappels.Liste.as_view(), name='liste_rappels'),
    path('facturation/rappels_impression', Verifie_ventilation(rappels_impression.Liste.as_view()), name='rappels_impression'),
    path('facturation/rappels_email', Verifie_ventilation(rappels_email.Liste.as_view()), name='rappels_email'),

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


    # Tarifs
    path('facturation/liste_tarifs', liste_tarifs.View.as_view(), name='liste_tarifs'),

    # Prestations
    path('facturation/liste_prestations', liste_prestations.Liste.as_view(), name='liste_prestations'),
    path('facturation/prestations_supprimer_plusieurs/<str:listepk>', liste_prestations.Supprimer_plusieurs.as_view(), name='prestations_supprimer_plusieurs'),
    path('facturation/liste_deductions', liste_deductions.Liste.as_view(), name='liste_deductions'),
    path('facturation/liste_soldes', Verifie_ventilation(liste_soldes.Liste.as_view()), name='liste_soldes'),
    path('facturation/synthese_prestations', synthese_prestations.View.as_view(), name='synthese_prestations'),

    # Impayés
    path('facturation/synthese_impayes', Verifie_ventilation(synthese_impayes.View.as_view()), name='synthese_impayes'),

    # AJAX
    path('facturation/modifier_lot_factures', secure_ajax(factures_generation.Modifier_lot_factures), name='ajax_modifier_lot_factures'),
    path('facturation/recherche_factures', secure_ajax(factures_generation.Recherche_factures), name='ajax_recherche_factures'),
    path('facturation/generation_factures', secure_ajax(factures_generation.Generation_factures), name='ajax_generation_factures'),
    path('facturation/modifier_lot_rappels', secure_ajax(rappels_generation.Modifier_lot_rappels), name='ajax_modifier_lot_rappels'),
    path('facturation/recherche_rappels', secure_ajax(rappels_generation.Recherche_rappels), name='ajax_recherche_rappels'),
    path('facturation/generation_rappels', secure_ajax(rappels_generation.Generation_rappels), name='ajax_generation_rappels'),
    path('facturation/factures_impression_pdf', secure_ajax(factures_impression.Impression_pdf), name='ajax_factures_impression_pdf'),
    path('facturation/factures_email_pdf', secure_ajax(factures_email.Impression_pdf), name='ajax_factures_email_pdf'),
    path('facturation/rappels_impression_pdf', secure_ajax(rappels_impression.Impression_pdf), name='ajax_rappels_impression_pdf'),
    path('facturation/rappels_email_pdf', secure_ajax(rappels_email.Impression_pdf), name='ajax_rappels_email_pdf'),
    path('facturation/lots_pes_exporter', secure_ajax(lots_pes.Exporter), name='ajax_lots_pes_exporter'),

]
