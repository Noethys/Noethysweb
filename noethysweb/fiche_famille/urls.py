# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.decorators import secure_ajax
from fiche_famille.views import famille, famille_questionnaire, famille_notes, famille_ajouter, famille_pieces, famille_cotisations, famille_caisse, famille_aides, famille_quotients, famille_divers, \
                            famille_prestations, famille_reglements, famille_consommations, famille_factures, famille_voir_facture, famille_voir_cotisation, famille_abo_factures_email, \
                            famille_abo_recus_email, famille_abo_depots_email, famille_outils, famille_attestations, famille_devis, famille_historique, famille_export_xml, famille_sms, \
                            famille_voir_rappel, famille_rappels, famille_portail, famille_emails, reglement_recu, famille_messagerie_portail, famille_mandats, famille_voir_mandat, famille_prestations_modele, \
                            famille_attestations_fiscales, famille_voir_attestation_fiscale, famille_locations, famille_voir_location, famille_remboursement, famille_factures_consulter, famille_factures_selection, \
                            famille_edition_renseignements, reglement_recu_auto, famille_formulaires

urlpatterns = [

    # # Individus
    path('individus/individus/ajouter/<int:idfamille>', famille_ajouter.Ajouter_individu.as_view(), name='individu_ajouter'),
    path('individus/individus/supprimer/<int:idfamille>/<int:idindividu>', famille_ajouter.Supprimer_individu.as_view(), name='individu_supprimer'),
    path('individus/individus/detacher/<int:idfamille>/<int:idindividu>', famille_ajouter.Detacher_individu.as_view(), name='individu_detacher'),

    # Familles
    path('individus/familles/liste', famille.Liste.as_view(), name='famille_liste'),
    path('individus/familles/ajouter', famille_ajouter.Creer_famille.as_view(), name='famille_ajouter'),
    path('individus/familles/supprimer/<int:idfamille>', famille.Supprimer_famille.as_view(), name='famille_supprimer'),
    path('individus/familles/resume/<int:idfamille>', famille.Resume.as_view(), name='famille_resume'),

    path('individus/familles/questionnaire/<int:idfamille>', famille_questionnaire.Consulter.as_view(), name='famille_questionnaire'),
    path('individus/familles/questionnaire/modifier/<int:idfamille>', famille_questionnaire.Modifier.as_view(), name='famille_questionnaire_modifier'),

    path('individus/familles/notes/ajouter/<int:idfamille>', famille_notes.Ajouter.as_view(), name='famille_notes_ajouter'),
    path('individus/familles/notes/modifier/<int:idfamille>/<int:pk>', famille_notes.Modifier.as_view(), name='famille_notes_modifier'),
    path('individus/familles/notes/supprimer/<int:idfamille>/<int:pk>', famille_notes.Supprimer.as_view(), name='famille_notes_supprimer'),

    path('individus/familles/pieces/liste/<int:idfamille>', famille_pieces.Liste.as_view(), name='famille_pieces_liste'),
    path('individus/familles/pieces/ajouter/<int:idfamille>', famille_pieces.Ajouter.as_view(), name='famille_pieces_ajouter'),
    path('individus/familles/pieces/modifier/<int:idfamille>/<int:pk>', famille_pieces.Modifier.as_view(), name='famille_pieces_modifier'),
    path('individus/familles/pieces/supprimer/<int:idfamille>/<int:pk>', famille_pieces.Supprimer.as_view(), name='famille_pieces_supprimer'),
    path('individus/familles/pieces/supprimer_plusieurs/<int:idfamille>/<str:listepk>', famille_pieces.Supprimer_plusieurs.as_view(), name='famille_pieces_supprimer_plusieurs'),
    path('individus/familles/pieces/saisie_rapide/<int:idfamille>/<int:idtype_piece>/<int:idindividu>', famille_pieces.Saisie_rapide.as_view(), name='famille_pieces_saisie_rapide'),

    path('individus/familles/locations/liste/<int:idfamille>', famille_locations.Liste.as_view(), name='famille_locations_liste'),
    path('individus/familles/locations/ajouter/<int:idfamille>', famille_locations.Ajouter.as_view(), name='famille_locations_ajouter'),
    path('individus/familles/locations/modifier/<int:idfamille>/<int:pk>', famille_locations.Modifier.as_view(), name='famille_locations_modifier'),
    path('individus/familles/locations/supprimer/<int:idfamille>/<int:pk>', famille_locations.Supprimer.as_view(), name='famille_locations_supprimer'),
    path('individus/familles/locations/supprimer_plusieurs/<int:idfamille>/<str:listepk>', famille_locations.Supprimer_plusieurs.as_view(), name='famille_locations_supprimer_plusieurs'),
    path('individus/familles/locations/voir/<int:idfamille>/<int:idlocation>', famille_voir_location.View.as_view(), name='famille_voir_location'),

    path('individus/familles/cotisations/liste/<int:idfamille>', famille_cotisations.Liste.as_view(), name='famille_cotisations_liste'),
    path('individus/familles/cotisations/ajouter/<int:idfamille>', famille_cotisations.Ajouter.as_view(), name='famille_cotisations_ajouter'),
    path('individus/familles/cotisations/modifier/<int:idfamille>/<int:pk>', famille_cotisations.Modifier.as_view(), name='famille_cotisations_modifier'),
    path('individus/familles/cotisations/supprimer/<int:idfamille>/<int:pk>', famille_cotisations.Supprimer.as_view(), name='famille_cotisations_supprimer'),
    path('individus/familles/cotisations/supprimer_plusieurs/<int:idfamille>/<str:listepk>', famille_cotisations.Supprimer_plusieurs.as_view(), name='famille_cotisations_supprimer_plusieurs'),
    path('individus/familles/cotisations/voir/<int:idfamille>/<int:idcotisation>', famille_voir_cotisation.View.as_view(), name='famille_voir_cotisation'),
    path('individus/familles/cotisations/ajouter/<int:idfamille>/<int:idtype_cotisation>/<int:idindividu>', famille_cotisations.Ajouter.as_view(), name='famille_cotisations_saisie_rapide'),

    path('individus/familles/caisse/<int:idfamille>', famille_caisse.Consulter.as_view(), name='famille_caisse'),
    path('individus/familles/caisse/modifier/<int:idfamille>', famille_caisse.Modifier.as_view(), name='famille_caisse_modifier'),

    path('individus/familles/aides/liste/<int:idfamille>', famille_aides.Liste.as_view(), name='famille_aides_liste'),
    path('individus/familles/aides/selection_activite/<int:idfamille>', famille_aides.Selection_activite.as_view(), name='famille_aides_ajouter'),
    path('individus/familles/aides/ajouter/<int:idfamille>/<int:idactivite>/<int:idmodele>', famille_aides.Ajouter.as_view(), name='famille_aides_configurer'),
    path('individus/familles/aides/modifier/<int:idfamille>/<int:pk>', famille_aides.Modifier.as_view(), name='famille_aides_modifier'),
    path('individus/familles/aides/supprimer/<int:idfamille>/<int:pk>', famille_aides.Supprimer.as_view(), name='famille_aides_supprimer'),

    path('individus/familles/quotients/liste/<int:idfamille>', famille_quotients.Liste.as_view(), name='famille_quotients_liste'),
    path('individus/familles/quotients/ajouter/<int:idfamille>', famille_quotients.Ajouter.as_view(), name='famille_quotients_ajouter'),
    path('individus/familles/quotients/modifier/<int:idfamille>/<int:pk>', famille_quotients.Modifier.as_view(), name='famille_quotients_modifier'),
    path('individus/familles/quotients/supprimer/<int:idfamille>/<int:pk>', famille_quotients.Supprimer.as_view(), name='famille_quotients_supprimer'),

    path('individus/familles/prestations/liste/<int:idfamille>', famille_prestations.Liste.as_view(), name='famille_prestations_liste'),
    path('individus/familles/prestations/ajouter/<int:idfamille>', famille_prestations.Ajouter.as_view(), name='famille_prestations_ajouter'),
    path('individus/familles/prestations/selection_modele/<int:idfamille>', famille_prestations_modele.Selection_modele.as_view(), name='famille_prestations_selection_modele'),
    path('individus/familles/prestations/ajouter_modele/<int:idfamille>/<int:idmodele>', famille_prestations_modele.Ajouter.as_view(), name='famille_prestations_ajouter_modele'),
    path('individus/familles/prestations/modifier/<int:idfamille>/<int:pk>', famille_prestations.Modifier.as_view(), name='famille_prestations_modifier'),
    path('individus/familles/prestations/supprimer/<int:idfamille>/<int:pk>', famille_prestations.Supprimer.as_view(), name='famille_prestations_supprimer'),
    path('individus/familles/prestations/supprimer_plusieurs/<int:idfamille>/<str:listepk>', famille_prestations.Supprimer_plusieurs.as_view(), name='famille_prestations_supprimer_plusieurs'),

    path('individus/familles/factures/liste/<int:idfamille>', famille_factures.Liste.as_view(), name='famille_factures_liste'),
    path('individus/familles/factures/ajouter/<int:idfamille>', famille_factures.Ajouter.as_view(), name='famille_factures_ajouter'),
    path('individus/familles/factures/modifier/<int:idfamille>/<int:pk>', famille_factures_consulter.Modifier.as_view(), name='famille_factures_modifier'),
    path('individus/familles/factures/consulter/<int:idfamille>/<int:pk>', famille_factures_consulter.Consulter.as_view(), name='famille_factures_consulter'),
    path('individus/familles/factures/supprimer_prestations/<int:idfamille>/<int:idfacture>/<int:pk>', famille_factures_consulter.Supprimer_prestation.as_view(), name='famille_factures_supprimer_prestation'),
    path('individus/familles/factures/supprimer_plusieurs_prestations/<int:idfamille>/<int:idfacture>/<str:listepk>', famille_factures_consulter.Supprimer_plusieurs_prestations.as_view(), name='famille_factures_supprimer_plusieurs_prestations'),
    path('individus/familles/factures/supprimer/<int:idfamille>/<int:pk>', famille_factures.Supprimer.as_view(), name='famille_factures_supprimer'),
    path('individus/familles/factures/supprimer_plusieurs/<int:idfamille>/<str:listepk>', famille_factures.Supprimer_plusieurs.as_view(), name='famille_factures_supprimer_plusieurs'),
    path('individus/familles/factures/annuler/<int:idfamille>/<int:pk>', famille_factures.Annuler.as_view(), name='famille_factures_annuler'),
    path('individus/familles/factures/annuler_plusieurs/<int:idfamille>/<str:listepk>', famille_factures.Annuler_plusieurs.as_view(), name='famille_factures_annuler_plusieurs'),
    path('individus/familles/factures/ajouter_prestations/<int:idfamille>/<int:pk>', famille_factures_selection.Liste.as_view(), name='famille_factures_selection'),
    path('individus/familles/factures/voir/<int:idfamille>/<int:idfacture>', famille_voir_facture.View.as_view(), name='famille_voir_facture'),
    path('individus/familles/factures/abo_factures_email/<int:idfamille>', famille_abo_factures_email.Modifier.as_view(), name='famille_abo_factures_email'),

    path('individus/familles/reglements/liste/<int:idfamille>', famille_reglements.Liste.as_view(), name='famille_reglements_liste'),
    path('individus/familles/reglements/ajouter/<int:idfamille>', famille_reglements.Ajouter.as_view(), name='famille_reglements_ajouter'),
    path('individus/familles/reglements/modifier/<int:idfamille>/<int:pk>', famille_reglements.Modifier.as_view(), name='famille_reglements_modifier'),
    path('individus/familles/reglements/supprimer/<int:idfamille>/<int:pk>', famille_reglements.Supprimer.as_view(), name='famille_reglements_supprimer'),
    path('individus/familles/reglements/supprimer_plusieurs/<int:idfamille>/<str:listepk>', famille_reglements.Supprimer_plusieurs.as_view(), name='famille_reglements_supprimer_plusieurs'),
    path('individus/familles/reglements/abo_recus_email/<int:idfamille>', famille_abo_recus_email.Modifier.as_view(), name='famille_abo_recus_email'),
    path('individus/familles/reglements/abo_depots_email/<int:idfamille>', famille_abo_depots_email.Modifier.as_view(), name='famille_abo_depots_email'),
    path('individus/familles/reglements/recu_auto/<int:idfamille>/<int:idreglement>', reglement_recu_auto.View.as_view(), name='reglement_recu_auto'),

    path('individus/familles/recus_reglements/liste/<int:idfamille>', reglement_recu.Liste.as_view(), name='famille_recus_liste'),
    path('individus/familles/recus_reglements/ajouter/<int:idfamille>/<int:idreglement>', reglement_recu.Ajouter.as_view(), name='famille_recus_ajouter'),
    path('individus/familles/recus_reglements/modifier/<int:idfamille>/<int:pk>', reglement_recu.Modifier.as_view(), name='famille_recus_modifier'),
    path('individus/familles/recus_reglements/supprimer/<int:idfamille>/<int:pk>', reglement_recu.Supprimer.as_view(), name='famille_recus_supprimer'),

    path('individus/familles/mandats/liste/<int:idfamille>', famille_mandats.Liste.as_view(), name='famille_mandats_liste'),
    path('individus/familles/mandats/ajouter/<int:idfamille>', famille_mandats.Ajouter.as_view(), name='famille_mandats_ajouter'),
    path('individus/familles/mandats/modifier/<int:idfamille>/<int:pk>', famille_mandats.Modifier.as_view(), name='famille_mandats_modifier'),
    path('individus/familles/mandats/supprimer/<int:idfamille>/<int:pk>', famille_mandats.Supprimer.as_view(), name='famille_mandats_supprimer'),
    path('individus/familles/mandats/voir/<int:idfamille>/<int:idmandat>', famille_voir_mandat.View.as_view(), name='famille_voir_mandat'),

    path('individus/familles/remboursement/ajouter/<int:idfamille>', famille_remboursement.Ajouter.as_view(), name='famille_remboursement_ajouter'),

    path('individus/familles/attestations/liste/<int:idfamille>', famille_attestations.Liste.as_view(), name='famille_attestations_liste'),
    path('individus/familles/attestations/ajouter/<int:idfamille>', famille_attestations.Ajouter.as_view(), name='famille_attestations_ajouter'),
    path('individus/familles/attestations/modifier/<int:idfamille>/<int:pk>', famille_attestations.Modifier.as_view(), name='famille_attestations_modifier'),
    path('individus/familles/attestations/supprimer/<int:idfamille>/<int:pk>', famille_attestations.Supprimer.as_view(), name='famille_attestations_supprimer'),

    path('individus/familles/devis/liste/<int:idfamille>', famille_devis.Liste.as_view(), name='famille_devis_liste'),
    path('individus/familles/devis/ajouter/<int:idfamille>', famille_devis.Ajouter.as_view(), name='famille_devis_ajouter'),
    path('individus/familles/devis/modifier/<int:idfamille>/<int:pk>', famille_devis.Modifier.as_view(), name='famille_devis_modifier'),
    path('individus/familles/devis/supprimer/<int:idfamille>/<int:pk>', famille_devis.Supprimer.as_view(), name='famille_devis_supprimer'),

    path('individus/familles/rappels/liste/<int:idfamille>', famille_rappels.Liste.as_view(), name='famille_rappels_liste'),
    path('individus/familles/rappels/supprimer/<int:idfamille>/<int:pk>', famille_rappels.Supprimer.as_view(), name='famille_rappels_supprimer'),
    path('individus/familles/rappels/voir/<int:idfamille>/<int:idrappel>', famille_voir_rappel.View.as_view(), name='famille_voir_rappel'),

    path('individus/familles/attestations_fiscales/liste/<int:idfamille>', famille_attestations_fiscales.Liste.as_view(), name='famille_attestations_fiscales_liste'),
    path('individus/familles/attestations_fiscales/supprimer/<int:idfamille>/<int:pk>', famille_attestations_fiscales.Supprimer.as_view(), name='famille_attestations_fiscales_supprimer'),
    path('individus/familles/attestations_fiscales/voir/<int:idfamille>/<int:idattestation>', famille_voir_attestation_fiscale.View.as_view(), name='famille_voir_attestation_fiscale'),

    path('individus/familles/formulaires/liste/<int:idfamille>', famille_formulaires.Liste.as_view(), name='famille_formulaires_liste'),
    path('individus/familles/formulaires/supprimer/<int:idfamille>/<int:pk>', famille_formulaires.Supprimer.as_view(), name='famille_formulaires_supprimer'),
    path('individus/familles/formulaires/voir/<int:idfamille>/<int:pk>', famille_formulaires.Voir.as_view(), name='famille_voir_formulaire'),

    path('individus/familles/portail/<int:idfamille>', famille_portail.Consulter.as_view(), name='famille_portail'),
    path('individus/familles/portail/modifier/<int:idfamille>', famille_portail.Modifier.as_view(), name='famille_portail_modifier'),

    path('individus/familles/divers/<int:idfamille>', famille_divers.Consulter.as_view(), name='famille_divers'),
    path('individus/familles/divers/modifier/<int:idfamille>', famille_divers.Modifier.as_view(), name='famille_divers_modifier'),

    # Grille des consommations
    path('individus/grille/<int:idfamille>', famille_consommations.Modifier.as_view(), name='famille_consommations'),
    path('individus/grille/<int:idfamille>/<int:idindividu>', famille_consommations.Modifier.as_view(), name='famille_consommations'),

    # Outils
    path('individus/familles/outils/<int:idfamille>', famille_outils.View.as_view(), name='famille_outils'),
    path('individus/familles/historique/<int:idfamille>', famille_historique.Liste.as_view(), name='famille_historique'),
    path('individus/familles/export_xml/<int:idfamille>', famille_export_xml.View.as_view(), name='famille_export_xml'),
    path('individus/familles/edition_renseignements/<int:idfamille>', famille_edition_renseignements.View.as_view(), name='famille_edition_renseignements'),

    # Communication
    path('individus/familles/emails/ajouter/<int:idfamille>', famille_emails.Ajouter.as_view(), name='famille_emails_ajouter'),
    path('individus/familles/sms/ajouter/<int:idfamille>', famille_sms.Ajouter.as_view(), name='famille_sms_ajouter'),

    # Messagerie du portail
    path('individus/familles/messagerie/<int:idfamille>', famille_messagerie_portail.Ajouter.as_view(), name='famille_messagerie_portail'),
    path('individus/familles/messagerie/ajouter/<int:idfamille>/<int:idstructure>', famille_messagerie_portail.Ajouter.as_view(), name='famille_messagerie_portail'),

    # AJAX
    path('individus/get_individus_existants', secure_ajax(famille_ajouter.Get_individus_existants), name='ajax_get_individus_existants'),
    path('individus/definir_titulaire', secure_ajax(famille.Definir_titulaire), name='ajax_definir_titulaire'),
    path('individus/changer_categorie', secure_ajax(famille.Changer_categorie), name='ajax_changer_categorie'),
    path('individus/on_change_type_cotisation', secure_ajax(famille_cotisations.On_change_type_cotisation), name='ajax_on_change_type_cotisation'),
    path('individus/on_change_unite_cotisation', secure_ajax(famille_cotisations.On_change_unite_cotisation), name='ajax_on_change_unite_cotisation'),
    path('individus/modifier_payeur', secure_ajax(famille_reglements.Modifier_payeur), name='ajax_modifier_payeur'),
    path('individus/on_selection_mode_reglement', secure_ajax(famille_reglements.On_selection_mode_reglement), name='ajax_on_selection_mode_reglement'),
    path('individus/get_ventilation', secure_ajax(famille_reglements.Get_ventilation), name='ajax_get_ventilation'),
    path('individus/recu_impression_pdf', secure_ajax(reglement_recu.Impression_pdf), name='ajax_recu_impression_pdf'),
    path('individus/facture_impression_pdf', secure_ajax(famille_voir_facture.Impression_pdf), name='ajax_facture_impression_pdf'),
    path('individus/attestation_impression_pdf', secure_ajax(famille_attestations.Impression_pdf), name='ajax_attestation_impression_pdf'),
    path('individus/facture_mandat_pdf', secure_ajax(famille_voir_mandat.Impression_pdf), name='ajax_mandat_impression_pdf'),
    path('individus/devis_impression_pdf', secure_ajax(famille_devis.Impression_pdf), name='ajax_devis_impression_pdf'),
    path('individus/cotisation_impression_pdf', secure_ajax(famille_voir_cotisation.Impression_pdf), name='ajax_cotisation_impression_pdf'),
    path('individus/rappel_impression_pdf', secure_ajax(famille_voir_rappel.Impression_pdf), name='ajax_rappel_impression_pdf'),
    path('individus/regenerer_identifiant', secure_ajax(famille_portail.Regenerer_identifiant), name='ajax_regenerer_identifiant'),
    path('individus/regenerer_mdp', secure_ajax(famille_portail.Regenerer_mdp), name='ajax_regenerer_mdp'),
    path('individus/codes_internet_impression_pdf', secure_ajax(famille_portail.Envoyer_codes), name='ajax_codes_internet_envoyer'),
    path('individus/ajax_get_tarifs_prestation', secure_ajax(famille_prestations.Get_tarifs), name='ajax_get_tarifs_prestation'),
    path('individus/ajax_get_activites_prestation', secure_ajax(famille_prestations.Get_activites), name='ajax_get_activites_prestation'),
    path('individus/ajax_supprimer_conso_prestation', secure_ajax(famille_prestations.Supprimer_consommation), name='ajax_supprimer_conso_prestation'),
    path('individus/attestation_fiscale_impression_pdf', secure_ajax(famille_voir_attestation_fiscale.Impression_pdf), name='ajax_attestation_fiscale_impression_pdf'),
    path('individus/location_impression_pdf', secure_ajax(famille_voir_location.Impression_pdf), name='ajax_location_impression_pdf'),
    path('individus/location_get_tarif_location', secure_ajax(famille_locations.Get_tarif_location), name='ajax_get_tarif_location'),
    path('individus/famille_edition_renseignements/generer_pdf', secure_ajax(famille_edition_renseignements.Generer_pdf), name='ajax_famille_edition_renseignements_generer_pdf'),
    path('individus/envoi_recu_auto', secure_ajax(reglement_recu_auto.Envoyer_recu_automatiquement), name='ajax_envoi_recu_auto'),

]
