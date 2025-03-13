# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from portail.views import accueil, login
from django.contrib.auth import views as auth_views
from consommations.views import grille
from portail.views import reset_password, change_password, reservations, planning, renseignements, individu_identite, individu_questionnaire, individu_contacts, \
                            individu_regimes_alimentaires, individu_coords, individu_medecin, individu_informations, individu_assurances, individu_vaccinations, \
                            famille_caisse, profil, profil_password_change, facturation, reglements, mentions, contact, messagerie, individu_maladies, album, documents, \
                            transmettre_piece, activites, inscrire_activite, attente_paiement, cotisations, sondage, famille_questionnaire, famille_parametres, pages_speciales, \
                            famille_quotients
from core.decorators import secure_ajax_portail


urlpatterns = [

    # Accueil
    path('', accueil.Accueil.as_view(), name='portail_accueil'),

    # Connexion
    path('connexion', login.LoginViewGeneric.as_view(), name='portail_connexion'),
    path('deconnexion', auth_views.LogoutView.as_view(next_page='portail_connexion'), name='portail_deconnexion'),

    # Change mot de passe
    path('password_change/', change_password.MyPasswordChangeView.as_view(), name='password_change'),
    path('password_change_done/', change_password.MyPasswordChangeDoneView.as_view(), name='password_change_done'),

    # Mot de passe oublié
    path('reset_password/', reset_password.MyPasswordResetView.as_view(), name='reset_password'),
    path('reset_password_sent/', reset_password.MyPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>', reset_password.MyPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset_password_complete/', reset_password.MyPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Profil
    path('profil', profil.View.as_view(), name='portail_profil'),
    path('profil_password_change', profil_password_change.View.as_view(), name='portail_profil_password_change'),

    # Album photos
    path('album/<str:code>', album.View.as_view(), name='portail_album'),

    # Sondage
    path('sondage/<str:code>', sondage.View_introduction.as_view(), name='portail_sondage'),
    path('sondage/questions/<str:code>', sondage.View_questions.as_view(), name='portail_sondage_questions'),
    path('sondage/questions/<str:code>/<int:idindividu>', sondage.View_questions.as_view(), name='portail_sondage_questions'),
    path('sondage/conclusion/<str:code>', sondage.View_conclusion.as_view(), name='portail_sondage_conclusion'),

    # Renseignements
    path('renseignements', renseignements.View.as_view(), name='portail_renseignements'),

    path('renseignements/famille/caisse', famille_caisse.Consulter.as_view(), name='portail_famille_caisse'),
    path('renseignements/famille/caisse/modifier', famille_caisse.Modifier.as_view(), name='portail_famille_caisse_modifier'),

    path('renseignements/famille/questionnaire', famille_questionnaire.Consulter.as_view(), name='portail_famille_questionnaire'),
    path('renseignements/famille/questionnaire/modifier', famille_questionnaire.Modifier.as_view(), name='portail_famille_questionnaire_modifier'),

    path('renseignements/famille/parametres', famille_parametres.Consulter.as_view(), name='portail_famille_parametres'),
    path('renseignements/famille/parametres/modifier', famille_parametres.Modifier.as_view(), name='portail_famille_parametres_modifier'),

    # path('renseignements/famille/quotients/liste', famille_quotients.Liste.as_view(), name='portail_famille_quotients'),
    # path('renseignements/famille/quotients/ajouter', famille_quotients.Ajouter.as_view(), name='portail_famille_quotients_ajouter'),
    # path('renseignements/famille/quotients/modifier/<int:idquotient>', famille_quotients.Modifier.as_view(), name='portail_famille_quotients_modifier'),
    # path('renseignements/famille/quotients/supprimer/<int:idquotient>', famille_quotients.Supprimer.as_view(), name='portail_famille_quotients_supprimer'),

    path('renseignements/individu/identite/<int:idrattachement>', individu_identite.Consulter.as_view(), name='portail_individu_identite'),
    path('renseignements/individu/identite/modifier/<int:idrattachement>', individu_identite.Modifier.as_view(), name='portail_individu_identite_modifier'),

    path('renseignements/individu/questionnaire/<int:idrattachement>', individu_questionnaire.Consulter.as_view(), name='portail_individu_questionnaire'),
    path('renseignements/individu/questionnaire/modifier/<int:idrattachement>', individu_questionnaire.Modifier.as_view(), name='portail_individu_questionnaire_modifier'),

    path('renseignements/individu/coords/<int:idrattachement>', individu_coords.Consulter.as_view(), name='portail_individu_coords'),
    path('renseignements/individu/coords/modifier/<int:idrattachement>', individu_coords.Modifier.as_view(), name='portail_individu_coords_modifier'),

    path('renseignements/individu/regimes_alimentaires/<int:idrattachement>', individu_regimes_alimentaires.Consulter.as_view(), name='portail_individu_regimes_alimentaires'),
    path('renseignements/individu/regimes_alimentaires/modifier/<int:idrattachement>', individu_regimes_alimentaires.Modifier.as_view(), name='portail_individu_regimes_alimentaires_modifier'),

    path('renseignements/individu/maladies/<int:idrattachement>', individu_maladies.Consulter.as_view(), name='portail_individu_maladies'),
    path('renseignements/individu/maladies/modifier/<int:idrattachement>', individu_maladies.Modifier.as_view(), name='portail_individu_maladies_modifier'),

    path('renseignements/individu/medecin/<int:idrattachement>', individu_medecin.Consulter.as_view(), name='portail_individu_medecin'),
    path('renseignements/individu/medecin/modifier/<int:idrattachement>', individu_medecin.Modifier.as_view(), name='portail_individu_medecin_modifier'),

    path('renseignements/individu/vaccinations/liste/<int:idrattachement>', individu_vaccinations.Liste.as_view(), name='portail_individu_vaccinations'),
    path('renseignements/individu/vaccinations/ajouter/<int:idrattachement>', individu_vaccinations.Ajouter.as_view(), name='portail_individu_vaccinations_ajouter'),
    path('renseignements/individu/vaccinations/modifier/<int:idrattachement>/<int:idvaccin>', individu_vaccinations.Modifier.as_view(), name='portail_individu_vaccinations_modifier'),
    path('renseignements/individu/vaccinations/supprimer/<int:idrattachement>/<int:idvaccin>', individu_vaccinations.Supprimer.as_view(), name='portail_individu_vaccinations_supprimer'),

    path('renseignements/individu/informations/liste/<int:idrattachement>', individu_informations.Liste.as_view(), name='portail_individu_informations'),
    path('renseignements/individu/informations/ajouter/<int:idrattachement>', individu_informations.Ajouter.as_view(), name='portail_individu_informations_ajouter'),
    path('renseignements/individu/informations/modifier/<int:idrattachement>/<int:idinformation>', individu_informations.Modifier.as_view(), name='portail_individu_informations_modifier'),
    path('renseignements/individu/informations/supprimer/<int:idrattachement>/<int:idinformation>', individu_informations.Supprimer.as_view(), name='portail_individu_informations_supprimer'),

    path('renseignements/individu/assurances/liste/<int:idrattachement>', individu_assurances.Liste.as_view(), name='portail_individu_assurances'),
    path('renseignements/individu/assurances/ajouter/<int:idrattachement>', individu_assurances.Ajouter.as_view(), name='portail_individu_assurances_ajouter'),
    path('renseignements/individu/assurances/modifier/<int:idrattachement>/<int:idassurance>', individu_assurances.Modifier.as_view(), name='portail_individu_assurances_modifier'),
    path('renseignements/individu/assurances/supprimer/<int:idrattachement>/<int:idassurance>', individu_assurances.Supprimer.as_view(), name='portail_individu_assurances_supprimer'),
    path('renseignements/individu/assurances/importer/<int:idrattachement>', individu_assurances.Importer.as_view(), name='portail_individu_assurances_importer'),

    path('renseignements/individu/contacts/liste/<int:idrattachement>', individu_contacts.Liste.as_view(), name='portail_individu_contacts'),
    path('renseignements/individu/contacts/ajouter/<int:idrattachement>', individu_contacts.Ajouter.as_view(), name='portail_individu_contacts_ajouter'),
    path('renseignements/individu/contacts/modifier/<int:idrattachement>/<int:idcontact>', individu_contacts.Modifier.as_view(), name='portail_individu_contacts_modifier'),
    path('renseignements/individu/contacts/supprimer/<int:idrattachement>/<int:idcontact>', individu_contacts.Supprimer.as_view(), name='portail_individu_contacts_supprimer'),
    path('renseignements/individu/contacts/importer/<int:idrattachement>', individu_contacts.Importer.as_view(), name='portail_individu_contacts_importer'),

    # Adhésions
    path('cotisations', cotisations.View.as_view(), name='portail_cotisations'),

    # Documents
    path('documents', documents.View.as_view(), name='portail_documents'),
    path('documents/transmettre', transmettre_piece.Ajouter.as_view(), name='portail_transmettre_piece'),
    path('documents/transmettre/get-individus', secure_ajax_portail(transmettre_piece.Get_individus), name='portail_ajax_inscrire_get_individus_by_famille'),

    # Activités
    path('activites', activites.View.as_view(), name='portail_activites'),
    path('activites/inscrire', inscrire_activite.Ajouter.as_view(), name='portail_inscrire_activite'),

    # Réservations
    path('reservations', reservations.View.as_view(), name='portail_reservations'),
    path('planning/<int:idindividu>/<int:idactivite>/<int:idperiode>', planning.View.as_view(), name='portail_planning'),

    # Facturation
    path('facturation', facturation.View.as_view(), name='portail_facturation'),
    path('retour_payzen_cancel', facturation.View_retour_paiement.as_view(etat="cancel"), name='retour_payzen_cancel'),
    path('retour_payzen_error', facturation.View_retour_paiement.as_view(etat="error"), name='retour_payzen_error'),
    path('retour_payzen_refused', facturation.View_retour_paiement.as_view(etat="refused"), name='retour_payzen_refused'),
    path('retour_payzen_success', facturation.View_retour_paiement.as_view(etat="success"), name='retour_payzen_success'),
    path('ipn_payzen', facturation.ipn_payzen, name='ipn_payzen'),
    path('retour_payfip', facturation.retour_payfip, name='retour_payfip'),
    path('attente_paiement', attente_paiement.View.as_view(), name='portail_attente_paiement'),

    # Règlements
    path('reglements', reglements.View.as_view(), name='portail_reglements'),

    # Contact
    path('contact', contact.View.as_view(), name='portail_contact'),
    path('contact/messagerie/<int:idstructure>', messagerie.Ajouter.as_view(), name='portail_messagerie'),

    # Mentions
    path('mentions', mentions.View.as_view(), name='portail_mentions'),

    # Désinscription mails
    path('desinscription/<str:valeur>', pages_speciales.desinscription_emails, name='desinscription'),
    path('confirmation_desinscription/<str:valeur>', pages_speciales.confirmation_desinscription, name='confirmation_desinscription'),

    # AJAX
    path('facturer', secure_ajax_portail(grille.Facturer), name='portail_ajax_facturer'),
    path('facturation/get_detail_facture', secure_ajax_portail(facturation.get_detail_facture), name='portail_ajax_get_detail_facture'),
    path('facturation/imprimer_facture', secure_ajax_portail(facturation.imprimer_facture), name='portail_ajax_imprimer_facture'),
    path('facturation/effectuer_paiement_en_ligne', secure_ajax_portail(facturation.effectuer_paiement_en_ligne), name='portail_ajax_effectuer_paiement_en_ligne'),
    path('reglements/imprimer_recu', secure_ajax_portail(reglements.imprimer_recu), name='portail_ajax_imprimer_recu'),
    path('individus/ajouter_regime_alimentaire', secure_ajax_portail(individu_regimes_alimentaires.Ajouter_regime_alimentaire), name='portail_ajax_ajouter_regime_alimentaire'),
    path('individus/ajouter_maladie', secure_ajax_portail(individu_maladies.Ajouter_maladie), name='portail_ajax_ajouter_maladie'),
    path('individus/ajouter_medecin', secure_ajax_portail(individu_medecin.Ajouter_medecin), name='portail_ajax_ajouter_medecin'),
    path('individus/ajouter_assureur', secure_ajax_portail(individu_assurances.Ajouter_assureur), name='portail_ajax_ajouter_assureur'),
    path('activites/get_form_extra', secure_ajax_portail(inscrire_activite.Get_form_extra), name='portail_ajax_inscrire_get_form_extra'),
    path('activites/validation_form', secure_ajax_portail(inscrire_activite.Valid_form), name='portail_ajax_inscrire_valid_form'),
    path('activites/get-individus', secure_ajax_portail(inscrire_activite.Get_individus), name='portail_ajax_inscrire_get_individus'),

]
