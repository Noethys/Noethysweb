# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from portail.views import accueil, login
from django.contrib.auth import views as auth_views
from consommations.views import grille
from portail.views import reset_password, change_password, reservations, planning, renseignements, individu_identite, individu_questionnaire, individu_contacts, \
                            individu_regimes_alimentaires, individu_coords, individu_medecin, individu_infos_medicales, individu_assurances, \
                            famille_caisse, profil, profil_password_change, facturation, reglements, mentions, contact, messagerie
from core.decorators import secure_ajax_portail



urlpatterns = [

    # Accueil
    path('', accueil.Accueil.as_view(), name='portail_accueil'),

    # Connexion
    path('connexion', login.LoginViewFamille.as_view(), name='portail_connexion'),
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

    # Renseignements
    path('renseignements', renseignements.View.as_view(), name='portail_renseignements'),

    path('renseignements/famille/caisse', famille_caisse.Consulter.as_view(), name='portail_famille_caisse'),
    path('renseignements/famille/caisse/modifier', famille_caisse.Modifier.as_view(), name='portail_famille_caisse_modifier'),






    path('renseignements/individu/identite/<int:idrattachement>', individu_identite.Consulter.as_view(), name='portail_individu_identite'),
    path('renseignements/individu/identite/modifier/<int:idrattachement>', individu_identite.Modifier.as_view(), name='portail_individu_identite_modifier'),

    path('renseignements/individu/questionnaire/<int:idrattachement>', individu_questionnaire.Consulter.as_view(), name='portail_individu_questionnaire'),
    path('renseignements/individu/questionnaire/modifier/<int:idrattachement>', individu_questionnaire.Modifier.as_view(), name='portail_individu_questionnaire_modifier'),

    path('renseignements/individu/coords/<int:idrattachement>', individu_coords.Consulter.as_view(), name='portail_individu_coords'),
    path('renseignements/individu/coords/modifier/<int:idrattachement>', individu_coords.Modifier.as_view(), name='portail_individu_coords_modifier'),

    path('renseignements/individu/regimes_alimentaires/<int:idrattachement>', individu_regimes_alimentaires.Consulter.as_view(), name='portail_individu_regimes_alimentaires'),
    path('renseignements/individu/regimes_alimentaires/modifier/<int:idrattachement>', individu_regimes_alimentaires.Modifier.as_view(), name='portail_individu_regimes_alimentaires_modifier'),

    path('renseignements/individu/medecin/<int:idrattachement>', individu_medecin.Consulter.as_view(), name='portail_individu_medecin'),
    path('renseignements/individu/medecin/modifier/<int:idrattachement>', individu_medecin.Modifier.as_view(), name='portail_individu_medecin_modifier'),

    path('renseignements/individu/infos_medicales/liste/<int:idrattachement>', individu_infos_medicales.Liste.as_view(), name='portail_individu_infos_medicales'),
    path('renseignements/individu/infos_medicales/ajouter/<int:idrattachement>', individu_infos_medicales.Ajouter.as_view(), name='portail_individu_infos_medicales_ajouter'),
    path('renseignements/individu/infos_medicales/modifier/<int:idrattachement>/<int:idprobleme>', individu_infos_medicales.Modifier.as_view(), name='portail_individu_infos_medicales_modifier'),
    path('renseignements/individu/infos_medicales/supprimer/<int:idrattachement>/<int:idprobleme>', individu_infos_medicales.Supprimer.as_view(), name='portail_individu_infos_medicales_supprimer'),

    path('renseignements/individu/assurances/liste/<int:idrattachement>', individu_assurances.Liste.as_view(), name='portail_individu_assurances'),
    path('renseignements/individu/assurances/ajouter/<int:idrattachement>', individu_assurances.Ajouter.as_view(), name='portail_individu_assurances_ajouter'),
    path('renseignements/individu/assurances/modifier/<int:idrattachement>/<int:idassurance>', individu_assurances.Modifier.as_view(), name='portail_individu_assurances_modifier'),
    path('renseignements/individu/assurances/supprimer/<int:idrattachement>/<int:idassurance>', individu_assurances.Supprimer.as_view(), name='portail_individu_assurances_supprimer'),

    path('renseignements/individu/contacts/liste/<int:idrattachement>', individu_contacts.Liste.as_view(), name='portail_individu_contacts'),
    path('renseignements/individu/contacts/ajouter/<int:idrattachement>', individu_contacts.Ajouter.as_view(), name='portail_individu_contacts_ajouter'),
    path('renseignements/individu/contacts/modifier/<int:idrattachement>/<int:idcontact>', individu_contacts.Modifier.as_view(), name='portail_individu_contacts_modifier'),
    path('renseignements/individu/contacts/supprimer/<int:idrattachement>/<int:idcontact>', individu_contacts.Supprimer.as_view(), name='portail_individu_contacts_supprimer'),

    # Réservations
    path('reservations', reservations.View.as_view(), name='portail_reservations'),
    path('planning/<int:idindividu>/<int:idperiode>', planning.View.as_view(), name='portail_planning'),

    # Facturation
    path('facturation', facturation.View.as_view(), name='portail_facturation'),

    # Règlements
    path('reglements', reglements.View.as_view(), name='portail_reglements'),

    # Contact
    path('contact', contact.View.as_view(), name='portail_contact'),
    path('contact/messagerie/<int:idstructure>', messagerie.Ajouter.as_view(), name='portail_messagerie'),

    # Mentions
    path('mentions', mentions.View.as_view(), name='portail_mentions'),

    # AJAX
    path('facturer', secure_ajax_portail(grille.Facturer), name='portail_ajax_facturer'),

]
