# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.decorators import secure_ajax
from fiche_individu.views import individu, individu_identite, individu_coords, individu_questionnaire, individu_scolarite, individu_inscriptions, \
                                individu_medical, individu_notes, individu_liens, individu_appliquer_forfait_date, individu_contacts, \
                                individu_regimes_alimentaires, individu_assurances, individu_maladies, individu_transports

urlpatterns = [

    # Individus
    path('individus/individus/liste', individu.Liste.as_view(), name='individu_liste'),
    # path('individus/individus/ajouter/<int:idfamille>', famille_ajouter.Ajouter_individu.as_view(), name='individu_ajouter'),
    # path('individus/individus/supprimer/<int:idfamille>/<int:idindividu>', famille_ajouter.Supprimer_individu.as_view(), name='individu_supprimer'),
    path('individus/individus/resume/<int:idfamille>/<int:idindividu>', individu.Resume.as_view(), name='individu_resume'),

    path('individus/individus/identite/<int:idfamille>/<int:idindividu>', individu_identite.Consulter.as_view(), name='individu_identite'),
    path('individus/individus/identite/modifier/<int:idfamille>/<int:idindividu>', individu_identite.Modifier.as_view(), name='individu_identite_modifier'),

    path('individus/individus/coords/<int:idfamille>/<int:idindividu>', individu_coords.Consulter.as_view(), name='individu_coords'),
    path('individus/individus/coords/modifier/<int:idfamille>/<int:idindividu>', individu_coords.Modifier.as_view(), name='individu_coords_modifier'),

    path('individus/individus/questionnaire/<int:idfamille>/<int:idindividu>', individu_questionnaire.Consulter.as_view(), name='individu_questionnaire'),
    path('individus/individus/questionnaire/modifier/<int:idfamille>/<int:idindividu>', individu_questionnaire.Modifier.as_view(), name='individu_questionnaire_modifier'),

    path('individus/individus/liens/<int:idfamille>/<int:idindividu>', individu_liens.Consulter.as_view(), name='individu_liens'),
    path('individus/individus/liens/modifier/<int:idfamille>/<int:idindividu>', individu_liens.Modifier.as_view(), name='individu_liens_modifier'),

    path('individus/individus/scolarite/liste/<int:idfamille>/<int:idindividu>', individu_scolarite.Liste.as_view(), name='individu_scolarite_liste'),
    path('individus/individus/scolarite/ajouter/<int:idfamille>/<int:idindividu>', individu_scolarite.Ajouter.as_view(), name='individu_scolarite_ajouter'),
    path('individus/individus/scolarite/modifier/<int:idfamille>/<int:idindividu>/<int:pk>', individu_scolarite.Modifier.as_view(), name='individu_scolarite_modifier'),
    path('individus/individus/scolarite/supprimer/<int:idfamille>/<int:idindividu>/<int:pk>', individu_scolarite.Supprimer.as_view(), name='individu_scolarite_supprimer'),

    path('individus/individus/inscriptions/liste/<int:idfamille>/<int:idindividu>', individu_inscriptions.Liste.as_view(), name='individu_inscriptions_liste'),
    path('individus/individus/inscriptions/ajouter/<int:idfamille>/<int:idindividu>', individu_inscriptions.Ajouter.as_view(), name='individu_inscriptions_ajouter'),
    path('individus/individus/inscriptions/ajouter/<int:idfamille>/<int:idindividu>/<int:idactivite>/<int:idgroupe>/<int:idcategorie_tarif>', individu_inscriptions.Ajouter.as_view(), name='individu_inscriptions_ajouter'),
    path('individus/individus/inscriptions/modifier/<int:idfamille>/<int:idindividu>/<int:pk>', individu_inscriptions.Modifier.as_view(), name='individu_inscriptions_modifier'),
    path('individus/individus/inscriptions/supprimer/<int:idfamille>/<int:idindividu>/<int:pk>', individu_inscriptions.Supprimer.as_view(), name='individu_inscriptions_supprimer'),
    path('individus/individus/inscriptions/appliquer_forfait_date/<int:idfamille>/<int:idindividu>', individu_appliquer_forfait_date.View.as_view(), name='individu_appliquer_forfait_date'),

    path('individus/individus/regimes_alimentaires/<int:idfamille>/<int:idindividu>', individu_regimes_alimentaires.Consulter.as_view(), name='individu_regimes_alimentaires'),
    path('individus/individus/regimes_alimentaires/modifier/<int:idfamille>/<int:idindividu>', individu_regimes_alimentaires.Modifier.as_view(), name='individu_regimes_alimentaires_modifier'),

    path('individus/individus/maladies/<int:idfamille>/<int:idindividu>', individu_maladies.Consulter.as_view(), name='individu_maladies'),
    path('individus/individus/maladies/modifier/<int:idfamille>/<int:idindividu>', individu_maladies.Modifier.as_view(), name='individu_maladies_modifier'),

    path('individus/individus/medical/liste/<int:idfamille>/<int:idindividu>', individu_medical.Liste.as_view(), name='individu_medical_liste'),

    path('individus/individus/medical/ajouter_info/<int:idfamille>/<int:idindividu>', individu_medical.Ajouter_information.as_view(), name='individu_informations_ajouter'),
    path('individus/individus/medical/modifier_info/<int:idfamille>/<int:idindividu>/<int:pk>', individu_medical.Modifier_information.as_view(), name='individu_informations_modifier'),
    path('individus/individus/medical/supprimer_info/<int:idfamille>/<int:idindividu>/<int:pk>', individu_medical.Supprimer_information.as_view(), name='individu_informations_supprimer'),

    path('individus/individus/medical/ajouter_vaccin/<int:idfamille>/<int:idindividu>', individu_medical.Ajouter_vaccin.as_view(), name='individu_vaccinations_ajouter'),
    path('individus/individus/medical/modifier_vaccin/<int:idfamille>/<int:idindividu>/<int:pk>', individu_medical.Modifier_vaccin.as_view(), name='individu_vaccinations_modifier'),
    path('individus/individus/medical/supprimer_vaccin/<int:idfamille>/<int:idindividu>/<int:pk>', individu_medical.Supprimer_vaccin.as_view(), name='individu_vaccinations_supprimer'),

    path('individus/individus/contacts/liste/<int:idfamille>/<int:idindividu>', individu_contacts.Liste.as_view(), name='individu_contacts_liste'),
    path('individus/individus/contacts/ajouter/<int:idfamille>/<int:idindividu>', individu_contacts.Ajouter.as_view(), name='individu_contacts_ajouter'),
    path('individus/individus/contacts/modifier/<int:idfamille>/<int:idindividu>/<int:pk>', individu_contacts.Modifier.as_view(), name='individu_contacts_modifier'),
    path('individus/individus/contacts/supprimer/<int:idfamille>/<int:idindividu>/<int:pk>', individu_contacts.Supprimer.as_view(), name='individu_contacts_supprimer'),
    path('individus/individus/contacts/importer/<int:idfamille>/<int:idindividu>', individu_contacts.Importer.as_view(), name='individu_contacts_importer'),

    path('individus/individus/assurances/liste/<int:idfamille>/<int:idindividu>', individu_assurances.Liste.as_view(), name='individu_assurances_liste'),
    path('individus/individus/assurances/ajouter/<int:idfamille>/<int:idindividu>', individu_assurances.Ajouter.as_view(), name='individu_assurances_ajouter'),
    path('individus/individus/assurances/modifier/<int:idfamille>/<int:idindividu>/<int:pk>', individu_assurances.Modifier.as_view(), name='individu_assurances_modifier'),
    path('individus/individus/assurances/supprimer/<int:idfamille>/<int:idindividu>/<int:pk>', individu_assurances.Supprimer.as_view(), name='individu_assurances_supprimer'),
    path('individus/individus/assurances/importer/<int:idfamille>/<int:idindividu>', individu_assurances.Importer.as_view(), name='individu_assurances_importer'),

    path('individus/individus/notes/ajouter/<int:idfamille>/<int:idindividu>', individu_notes.Ajouter.as_view(), name='individu_notes_ajouter'),
    path('individus/individus/notes/modifier/<int:idfamille>/<int:idindividu>/<int:pk>', individu_notes.Modifier.as_view(), name='individu_notes_modifier'),
    path('individus/individus/notes/supprimer/<int:idfamille>/<int:idindividu>/<int:pk>', individu_notes.Supprimer.as_view(), name='individu_notes_supprimer'),

    path('individus/individus/transports/liste/<int:idfamille>/<int:idindividu>', individu_transports.Liste.as_view(), name='individu_transports_liste'),

    path('individus/individus/transports/ajouter_progtransport/<int:idfamille>/<int:idindividu>', individu_transports.Ajouter_progtransport.as_view(), name='individu_progtransports_ajouter'),
    path('individus/individus/transports/modifier_progtransport/<int:idfamille>/<int:idindividu>/<int:pk>', individu_transports.Modifier_progtransport.as_view(), name='individu_progtransports_modifier'),
    path('individus/individus/transports/supprimer_progtransport/<int:idfamille>/<int:idindividu>/<int:pk>', individu_transports.Supprimer_progtransport.as_view(), name='individu_progtransports_supprimer'),

    path('individus/individus/transports/ajouter_transport/<int:idfamille>/<int:idindividu>', individu_transports.Ajouter_transport.as_view(), name='individu_transports_ajouter'),
    path('individus/individus/transports/modifier_transport/<int:idfamille>/<int:idindividu>/<int:pk>', individu_transports.Modifier_transport.as_view(), name='individu_transports_modifier'),
    path('individus/individus/transports/supprimer_transport/<int:idfamille>/<int:idindividu>/<int:pk>', individu_transports.Supprimer_transport.as_view(), name='individu_transports_supprimer'),

    # AJAX
    path('individus/get_classes', secure_ajax(individu_scolarite.Get_classes), name='ajax_get_classes'),
    path('individus/get_niveaux', secure_ajax(individu_scolarite.Get_niveaux), name='ajax_get_niveaux'),
    path('individus/get_groupes', secure_ajax(individu_inscriptions.Get_groupes), name='ajax_get_groupes'),
    path('individus/get_categories_tarifs', secure_ajax(individu_inscriptions.Get_categories_tarifs), name='ajax_get_categories_tarifs'),
    path('individus/select_medecin', secure_ajax(individu_medical.Select_medecin), name='ajax_select_medecin'),
    path('individus/deselect_medecin', secure_ajax(individu_medical.Deselect_medecin), name='ajax_deselect_medecin'),
    path('individus/get_coords_gps', secure_ajax(individu_coords.Get_coords_gps), name='ajax_get_coords_gps'),
    path('individus/ajouter_regime_alimentaire', secure_ajax(individu_regimes_alimentaires.Ajouter_regime_alimentaire), name='ajax_ajouter_regime_alimentaire'),
    path('individus/ajouter_maladie', secure_ajax(individu_maladies.Ajouter_maladie), name='ajax_ajouter_maladie'),
    path('individus/ajouter_assureur', secure_ajax(individu_assurances.Ajouter_assureur), name='ajax_ajouter_assureur'),
    path('individus/get_info_transport', secure_ajax(individu_transports.Get_info_transport), name='ajax_get_info_transport'),

]
