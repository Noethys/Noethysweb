# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from individus.views import liste_pieces_manquantes, liste_pieces_fournies, liste_regimes_caisses, liste_codes_comptables, liste_inscriptions_attente, suivi_inscriptions, \
                            importation_photos, liste_anniversaires, liste_quotients, etiquettes, etiquettes_familles, etiquettes_individus, \
                            inscriptions_scolaires, scolarites, inscriptions_liste, inscriptions_impression, inscriptions_email, liste_comptes_internet, \
                            individus_detaches_liste, liste_mandats, liste_questionnaires_familles, liste_questionnaires_individus, liste_contacts_urgence, \
                            liste_regimes_alimentaires, liste_maladies, liste_informations, individus_doublons_liste, liste_familles_sans_inscriptions, \
                            edition_contacts, edition_renseignements, edition_informations, liste_photos_manquantes, recherche_avancee

urlpatterns = [

    # Table des matières
    path('individus/', toc.Toc.as_view(menu_code="individus_toc"), name='individus_toc'),

    # # Individus
    # path('individus/individus/liste', individu.Liste.as_view(), name='individu_liste'),
    # path('individus/individus/ajouter/<int:idfamille>', famille_ajouter.Ajouter_individu.as_view(), name='individu_ajouter'),
    # path('individus/individus/supprimer/<int:idfamille>/<int:idindividu>', famille_ajouter.Supprimer_individu.as_view(), name='individu_supprimer'),
    # path('individus/individus/resume/<int:idfamille>/<int:idindividu>', individu.Resume.as_view(), name='individu_resume'),

    path('individus/individus_detaches/liste', individus_detaches_liste.Liste.as_view(), name='individus_detaches_liste'),
    path('individus/individus_detaches/supprimer/<int:pk>', individus_detaches_liste.Supprimer.as_view(), name='individus_detaches_supprimer'),
    path('individus/individus_doublons/liste', individus_doublons_liste.Liste.as_view(), name='individus_doublons_liste'),
    path('individus/recherche_avancee', recherche_avancee.View.as_view(), name='individus_recherche_avancee'),

    # Inscriptions
    path('individus/inscriptions', inscriptions_liste.Liste.as_view(), name='inscriptions_liste'),
    path('individus/inscriptions/ajouter', inscriptions_liste.Ajouter.as_view(), name='inscriptions_ajouter'),
    path('individus/inscriptions/modifier/<int:pk>', inscriptions_liste.Modifier.as_view(), name='inscriptions_modifier'),
    path('individus/inscriptions/supprimer/<int:pk>', inscriptions_liste.Supprimer.as_view(), name='inscriptions_supprimer'),
    path('individus/inscriptions/supprimer_plusieurs/<str:listepk>', inscriptions_liste.Supprimer_plusieurs.as_view(), name='inscriptions_supprimer_plusieurs'),

    path('individus/inscriptions_impression', inscriptions_impression.Liste.as_view(), name='inscriptions_impression'),
    path('individus/inscriptions_email', inscriptions_email.Liste.as_view(), name='inscriptions_email'),

    path('individus/liste_inscriptions_attente', liste_inscriptions_attente.View.as_view(etat="attente"), name='liste_inscriptions_attente'),
    path('individus/liste_inscriptions_refus', liste_inscriptions_attente.View.as_view(etat="refus"), name='liste_inscriptions_refus'),
    path('individus/suivi_inscriptions', suivi_inscriptions.View.as_view(), name='suivi_inscriptions'),
    path('individus/liste_familles_sans_inscriptions', liste_familles_sans_inscriptions.Liste.as_view(), name='liste_familles_sans_inscriptions'),

    # Inscriptions scolaires
    path('individus/inscriptions_scolaires', inscriptions_scolaires.Liste.as_view(), name='inscriptions_scolaires_liste'),
    path('individus/inscriptions_scolaires/<int:idclasse>', inscriptions_scolaires.Liste.as_view(), name='inscriptions_scolaires_liste'),
    path('individus/inscriptions_scolaires/ajouter/<int:idclasse>', inscriptions_scolaires.Ajouter.as_view(), name='inscriptions_scolaires_ajouter'),
    path('individus/inscriptions_scolaires/ajouter_plusieurs/<int:idclasse>', inscriptions_scolaires.Ajouter_plusieurs.as_view(), name='inscriptions_scolaires_ajouter_plusieurs'),
    path('individus/inscriptions_scolaires/modifier/<int:idclasse>/<int:pk>', inscriptions_scolaires.Modifier.as_view(), name='inscriptions_scolaires_modifier'),
    path('individus/inscriptions_scolaires/supprimer/<int:idclasse>/<int:pk>', inscriptions_scolaires.Supprimer.as_view(), name='inscriptions_scolaires_supprimer'),

    # Etapes de scolarité
    path('individus/scolarites', scolarites.Liste.as_view(), name='scolarites_liste'),
    path('individus/scolarites/ajouter', scolarites.Ajouter.as_view(), name='scolarites_ajouter'),
    path('individus/scolarites/modifier/<int:pk>', scolarites.Modifier.as_view(), name='scolarites_modifier'),
    path('individus/scolarites/supprimer/<int:pk>', scolarites.Supprimer.as_view(), name='scolarites_supprimer'),

    # Pièces
    path('individus/liste_pieces_manquantes', liste_pieces_manquantes.Liste.as_view(), name='liste_pieces_manquantes'),
    path('individus/liste_pieces_fournies', liste_pieces_fournies.Liste.as_view(), name='liste_pieces_fournies'),
    path('individus/pieces_supprimer_plusieurs/<str:listepk>', liste_pieces_fournies.Supprimer_plusieurs.as_view(), name='pieces_supprimer_plusieurs'),

    # Informations
    path('individus/edition_renseignements', edition_renseignements.View.as_view(), name='edition_renseignements'),

    path('individus/liste_anniversaires', liste_anniversaires.View.as_view(), name='liste_anniversaires'),
    path('individus/liste_regimes_caisses', liste_regimes_caisses.Liste.as_view(), name='liste_regimes_caisses'),
    path('individus/liste_quotients', liste_quotients.Liste.as_view(), name='liste_quotients'),
    path('individus/liste_codes_comptables', liste_codes_comptables.Liste.as_view(), name='liste_codes_comptables'),

    path('individus/mandats/liste', liste_mandats.Liste.as_view(), name='mandats_liste'),
    path('individus/mandats/creer', liste_mandats.Creer.as_view(), name='mandats_creer'),
    path('individus/mandats/ajouter/<int:idfamille>', liste_mandats.Ajouter.as_view(), name='mandats_ajouter'),
    path('individus/mandats/modifier/<int:pk>', liste_mandats.Modifier.as_view(), name='mandats_modifier'),
    path('individus/mandats/supprimer/<int:pk>', liste_mandats.Supprimer.as_view(), name='mandats_supprimer'),

    path('individus/contacts/liste', liste_contacts_urgence.Liste.as_view(), name='contacts_urgence_liste'),
    path('individus/contacts/modifier/<int:pk>', liste_contacts_urgence.Modifier.as_view(), name='contacts_urgence_modifier'),
    path('individus/contacts/supprimer/<int:pk>', liste_contacts_urgence.Supprimer.as_view(), name='contacts_urgence_supprimer'),

    path('individus/edition_contacts', edition_contacts.View.as_view(), name='edition_contacts'),

    path('individus/regimes_alimentaires/liste', liste_regimes_alimentaires.Liste.as_view(), name='regimes_alimentaires_liste'),
    path('individus/regimes_alimentaires/modifier/<int:pk>', liste_regimes_alimentaires.Modifier.as_view(), name='regimes_alimentaires_modifier'),

    path('individus/maladies/liste', liste_maladies.Liste.as_view(), name='maladies_liste'),
    path('individus/maladies/modifier/<int:pk>', liste_maladies.Modifier.as_view(), name='maladies_modifier'),

    path('individus/informations/liste', liste_informations.Liste.as_view(), name='informations_liste'),
    path('individus/informations/modifier/<int:pk>', liste_informations.Modifier.as_view(), name='informations_modifier'),
    path('individus/informations/supprimer/<int:pk>', liste_informations.Supprimer.as_view(), name='informations_supprimer'),

    path('individus/edition_informations', edition_informations.View.as_view(), name='edition_informations'),

    # photos
    path('individus/liste_photos_manquantes', liste_photos_manquantes.Liste.as_view(), name='liste_photos_manquantes'),
    path('individus/importation_photos', importation_photos.View.as_view(), name='importation_photos'),
    path('individus/importation_photos/<str:uuid_lot>', importation_photos.View.as_view(), name='importation_photos'),

    path('individus/liste_comptes_internet', liste_comptes_internet.Liste.as_view(), name='liste_comptes_internet'),

    path('individus/questionnaires/familles/liste', liste_questionnaires_familles.Liste.as_view(), name='questionnaires_familles_liste'),
    path('individus/questionnaires/familles/liste/<str:categorie>', liste_questionnaires_familles.Liste.as_view(), name='questionnaires_familles_liste'),
    path('individus/questionnaires/individus/liste', liste_questionnaires_individus.Liste.as_view(), name='questionnaires_individus_liste'),
    path('individus/questionnaires/individus/liste/<str:categorie>', liste_questionnaires_individus.Liste.as_view(), name='questionnaires_individus_liste'),

    # Impression
    path('individus/etiquettes_individus', etiquettes_individus.Liste.as_view(), name='etiquettes_individus'),
    path('individus/etiquettes_familles', etiquettes_familles.Liste.as_view(), name='etiquettes_familles'),




    # AJAX
    path('individus/get_suivi_inscriptions', secure_ajax(suivi_inscriptions.Get_suivi_inscriptions), name='ajax_get_suivi_inscriptions'),
    path('individus/get_form_activites', secure_ajax(suivi_inscriptions.Get_form_activites), name='ajax_get_form_activites'),
    path('individus/valider_form_activites', secure_ajax(suivi_inscriptions.Valider_form_activites), name='ajax_valider_form_activites'),
    path('individus/importation_photos/analyse/get_individus', secure_ajax(importation_photos.Get_individus), name='ajax_importation_photos_get_individus'),
    path('individus/liste_anniversaires/generer_pdf', secure_ajax(liste_anniversaires.Generer_pdf), name='ajax_liste_anniversaires_generer_pdf'),
    path('individus/etiquettes_impression_pdf', secure_ajax(etiquettes.Impression_pdf), name='ajax_etiquettes_impression_pdf'),
    path('individus/inscriptions_scolaires/get_periodes', secure_ajax(inscriptions_scolaires.Get_periodes), name='ajax_inscriptions_scolaires_get_periodes'),
    path('individus/inscriptions_scolaires/get_classes', secure_ajax(inscriptions_scolaires.Get_classes), name='ajax_inscriptions_scolaires_get_classes'),
    path('individus/inscriptions_scolaires/get_inscrits', secure_ajax(inscriptions_scolaires.Get_inscrits), name='ajax_inscriptions_scolaires_get_inscrits'),
    path('individus/inscriptions_impression_pdf', secure_ajax(inscriptions_impression.Impression_pdf), name='ajax_inscriptions_impression_pdf'),
    path('individus/inscriptions_email_pdf', secure_ajax(inscriptions_email.Impression_pdf), name='ajax_inscriptions_email_pdf'),
    path('individus/comptes_internet_email', secure_ajax(liste_comptes_internet.Envoyer_email), name='ajax_comptes_internet_email'),
    path('individus/comptes_internet_desactiver', secure_ajax(liste_comptes_internet.Desactiver), name='ajax_comptes_internet_desactiver'),
    path('individus/comptes_internet_activer', secure_ajax(liste_comptes_internet.Activer), name='ajax_comptes_internet_activer'),
    path('individus/comptes_internet_reinitialiser_mdp', secure_ajax(liste_comptes_internet.Reinitialiser_mdp), name='ajax_comptes_internet_reinitialiser_mdp'),
    path('individus/comptes_internet_reinitialiser_identifiant', secure_ajax(liste_comptes_internet.Reinitialiser_identifiant), name='ajax_comptes_internet_reinitialiser_identifiant'),
    path('individus/informations/modifier_diffusion/', secure_ajax(liste_informations.Modifier_diffusion), name='ajax_modifier_diffusion_information'),
    path('individus/importer_photos_individus', secure_ajax(importation_photos.Importer_photos_individus), name="ajax_importer_photos_individus"),
    path('individus/edition_contacts/generer_pdf', secure_ajax(edition_contacts.Generer_pdf), name='ajax_edition_contacts_generer_pdf'),
    path('individus/edition_renseignements/generer_pdf', secure_ajax(edition_renseignements.Generer_pdf), name='ajax_edition_renseignements_generer_pdf'),
    path('individus/edition_informations/generer_pdf', secure_ajax(edition_informations.Generer_pdf), name='ajax_edition_informations_generer_pdf'),

]
