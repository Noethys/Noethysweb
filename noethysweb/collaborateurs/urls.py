# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from collaborateurs.views import collaborateur, collaborateur_identite, collaborateur_questionnaire, collaborateur_coords, collaborateur_qualifications, \
                                collaborateur_pieces, collaborateur_notes, collaborateur_contrats, collaborateur_evenements, \
                                collaborateur_appliquer_modele_planning, liste_contrats, collaborateur_outils, collaborateur_historique, \
                                collaborateur_emails, collaborateur_sms, appliquer_modele_planning, collaborateur_groupes, collaborateur_voir_contrat, \
                                fusionner_contrats_word, importer_collaborateurs, planning, planning_individuel, statistiques_evenements, conges


urlpatterns = [

    # Table des matières
    path("collaborateurs/", toc.Toc.as_view(menu_code="collaborateurs_toc"), name='collaborateurs_toc'),

    # Collaborateurs
    path('collaborateurs/collaborateurs/liste', collaborateur.Liste.as_view(), name='collaborateur_liste'),
    path('collaborateurs/collaborateurs/ajouter', collaborateur.Ajouter.as_view(), name='collaborateur_ajouter'),
    path('collaborateurs/collaborateurs/supprimer/<int:idcollaborateur>', collaborateur.Supprimer.as_view(), name='collaborateur_supprimer'),
    path('collaborateurs/collaborateurs/resume/<int:idcollaborateur>', collaborateur.Resume.as_view(), name='collaborateur_resume'),

    path('collaborateurs/collaborateurs/identite/<int:idcollaborateur>', collaborateur_identite.Consulter.as_view(), name='collaborateur_identite'),
    path('collaborateurs/collaborateurs/identite/modifier/<int:idcollaborateur>', collaborateur_identite.Modifier.as_view(), name='collaborateur_identite_modifier'),

    path('collaborateurs/collaborateurs/groupes/<int:idcollaborateur>', collaborateur_groupes.Consulter.as_view(), name='collaborateur_groupes'),
    path('collaborateurs/collaborateurs/groupes/modifier/<int:idcollaborateur>', collaborateur_groupes.Modifier.as_view(), name='collaborateur_groupes_modifier'),

    path('collaborateurs/collaborateurs/questionnaire/<int:idcollaborateur>', collaborateur_questionnaire.Consulter.as_view(), name='collaborateur_questionnaire'),
    path('collaborateurs/collaborateurs/questionnaire/modifier/<int:idcollaborateur>', collaborateur_questionnaire.Modifier.as_view(), name='collaborateur_questionnaire_modifier'),

    path('collaborateurs/collaborateurs/coords/<int:idcollaborateur>', collaborateur_coords.Consulter.as_view(), name='collaborateur_coords'),
    path('collaborateurs/collaborateurs/coords/modifier/<int:idcollaborateur>', collaborateur_coords.Modifier.as_view(), name='collaborateur_coords_modifier'),

    path('collaborateurs/collaborateurs/qualifications/<int:idcollaborateur>', collaborateur_qualifications.Consulter.as_view(), name='collaborateur_qualifications'),
    path('collaborateurs/collaborateurs/qualifications/modifier/<int:idcollaborateur>', collaborateur_qualifications.Modifier.as_view(), name='collaborateur_qualifications_modifier'),

    path('collaborateurs/collaborateurs/pieces/liste/<int:idcollaborateur>', collaborateur_pieces.Liste.as_view(), name='collaborateur_pieces_liste'),
    path('collaborateurs/collaborateurs/pieces/ajouter/<int:idcollaborateur>', collaborateur_pieces.Ajouter.as_view(), name='collaborateur_pieces_ajouter'),
    path('collaborateurs/collaborateurs/pieces/modifier/<int:idcollaborateur>/<int:pk>', collaborateur_pieces.Modifier.as_view(), name='collaborateur_pieces_modifier'),
    path('collaborateurs/collaborateurs/pieces/supprimer/<int:idcollaborateur>/<int:pk>', collaborateur_pieces.Supprimer.as_view(), name='collaborateur_pieces_supprimer'),
    path('collaborateurs/collaborateurs/pieces/supprimer_plusieurs/<int:idcollaborateur>/<str:listepk>', collaborateur_pieces.Supprimer_plusieurs.as_view(), name='collaborateur_pieces_supprimer_plusieurs'),
    path('collaborateurs/collaborateurs/pieces/saisie_rapide/<int:idcollaborateur>/<int:idtype_piece>', collaborateur_pieces.Saisie_rapide.as_view(), name='collaborateur_pieces_saisie_rapide'),

    path('collaborateurs/collaborateurs/contrats/liste/<int:idcollaborateur>', collaborateur_contrats.Liste.as_view(), name='collaborateur_contrats_liste'),
    path('collaborateurs/collaborateurs/contrats/ajouter/<int:idcollaborateur>', collaborateur_contrats.Ajouter.as_view(), name='collaborateur_contrats_ajouter'),
    path('collaborateurs/collaborateurs/contrats/modifier/<int:idcollaborateur>/<int:pk>', collaborateur_contrats.Modifier.as_view(), name='collaborateur_contrats_modifier'),
    path('collaborateurs/collaborateurs/contrats/supprimer/<int:idcollaborateur>/<int:pk>', collaborateur_contrats.Supprimer.as_view(), name='collaborateur_contrats_supprimer'),
    path('collaborateurs/collaborateurs/contrats/voir/<int:idcollaborateur>/<int:idcontrat>', collaborateur_voir_contrat.View.as_view(), name='collaborateur_voir_contrat'),

    path('collaborateurs/collaborateurs/evenements/liste/<int:idcollaborateur>', collaborateur_evenements.Liste.as_view(), name='collaborateur_evenements_liste'),
    path('collaborateurs/collaborateurs/evenements/ajouter/<int:idcollaborateur>', collaborateur_evenements.Ajouter.as_view(), name='collaborateur_evenements_ajouter'),
    path('collaborateurs/collaborateurs/evenements/modifier/<int:idcollaborateur>/<int:pk>', collaborateur_evenements.Modifier.as_view(), name='collaborateur_evenements_modifier'),
    path('collaborateurs/collaborateurs/evenements/supprimer/<int:idcollaborateur>/<int:pk>', collaborateur_evenements.Supprimer.as_view(), name='collaborateur_evenements_supprimer'),
    path('collaborateurs/collaborateurs/evenements/supprimer_plusieurs/<int:idcollaborateur>/<str:listepk>', collaborateur_evenements.Supprimer_plusieurs.as_view(), name='collaborateur_evenements_supprimer_plusieurs'),
    path('collaborateurs/collaborateurs/evenements/appliquer_modele/<int:idcollaborateur>', collaborateur_appliquer_modele_planning.View.as_view(), name='collaborateur_appliquer_modele_planning'),

    path('collaborateurs/collaborateurs/outils/<int:idcollaborateur>', collaborateur_outils.View.as_view(), name='collaborateur_outils'),
    path('collaborateurs/collaborateurs/planning/<int:idcollaborateur>', planning_individuel.Onglet_planning.as_view(), name='collaborateur_planning'),
    path('collaborateurs/collaborateurs/conges/<int:idcollaborateur>', conges.Onglet_conges.as_view(), name='collaborateur_conges'),
    path('collaborateurs/collaborateurs/historique/<int:idcollaborateur>', collaborateur_historique.Liste.as_view(), name='collaborateur_historique'),
    path('collaborateurs/collaborateurs/emails/ajouter/<int:idcollaborateur>', collaborateur_emails.Ajouter.as_view(), name='collaborateur_emails_ajouter'),
    path('collaborateurs/collaborateurs/sms/ajouter/<int:idcollaborateur>', collaborateur_sms.Ajouter.as_view(), name='collaborateur_sms_ajouter'),

    path('collaborateurs/collaborateurs/notes/ajouter/<int:idcollaborateur>', collaborateur_notes.Ajouter.as_view(), name='collaborateur_notes_ajouter'),
    path('collaborateurs/collaborateurs/notes/modifier/<int:idcollaborateur>/<int:pk>', collaborateur_notes.Modifier.as_view(), name='collaborateur_notes_modifier'),
    path('collaborateurs/collaborateurs/notes/supprimer/<int:idcollaborateur>/<int:pk>', collaborateur_notes.Supprimer.as_view(), name='collaborateur_notes_supprimer'),

    path('collaborateurs/importer_collaborateurs', importer_collaborateurs.View.as_view(), name='importer_collaborateurs'),

    path('collaborateurs/liste_contrats', liste_contrats.Liste.as_view(), name='contrats_liste'),

    path('collaborateurs/fusionner_contrats_word', fusionner_contrats_word.Liste.as_view(), name='fusionner_contrats_word'),

    # Gestion des évènements
    path('collaborateurs/appliquer_modele_planning', appliquer_modele_planning.View.as_view(), name='appliquer_modele_planning'),
    path('collaborateurs/planning', planning.View.as_view(), name='planning_equipe'),
    path('collaborateurs/planning/ical/<str:token>.ics', planning.Ical, name='planning_equipe_ical'),
    path('collaborateurs/planning_individuel', planning_individuel.View.as_view(), name='planning_individuel'),
    path('collaborateurs/soldes_objectifs', planning_individuel.View_soldes.as_view(), name='soldes_objectifs_collaborateurs'),
    path('collaborateurs/demandes_absences', conges.View_demandes.as_view(), name='demandes_absences_collaborateurs'),
    path('collaborateurs/compteurs_conges', conges.View_compteurs.as_view(), name='compteurs_conges_collaborateurs'),

    # Analyse
    path('collaborateurs/statistiques_evenements', statistiques_evenements.View.as_view(), name='statistiques_evenements_collaborateurs'),


    # AJAX
    path('collaborateurs/planning_equipe/get_donnees', secure_ajax(planning.Get_donnees), name='ajax_planning_equipe_get_donnees'),
    path('collaborateurs/planning_equipe/get_evenements', secure_ajax(planning.Get_evenements), name='ajax_planning_equipe_get_evenements'),
    path('collaborateurs/planning_equipe/get_anomalies', secure_ajax(planning.Get_anomalies), name='ajax_planning_equipe_get_anomalies'),
    path('collaborateurs/planning_equipe/enregistrer', secure_ajax(planning.Enregistrer), name='ajax_planning_equipe_enregistrer'),
    path('collaborateurs/appliquer_modele_planning/get_liste', secure_ajax(appliquer_modele_planning.Get_liste), name='ajax_modeles_planning_get_liste'),
    path('collaborateurs/appliquer_modele_planning/get_frise', secure_ajax(appliquer_modele_planning.Get_frise), name='ajax_modeles_planning_get_frise'),
    path('collaborateurs/planning_equipe/appliquer_modele', secure_ajax(planning.Appliquer_modele), name='ajax_planning_equipe_appliquer_modele'),
    path('collaborateurs/planning_equipe/copier_periode', secure_ajax(planning.Copier_periode), name='ajax_planning_equipe_copier_periode'),
    path('collaborateurs/planning_equipe/enregistrer_note', secure_ajax(planning.Enregistrer_note), name='ajax_planning_equipe_enregistrer_note'),
    path('collaborateurs/planning_equipe/memoriser_affichage', secure_ajax(planning.Memoriser_affichage), name='ajax_planning_equipe_memoriser_affichage'),
    path('collaborateurs/planning_equipe/memoriser_reglages', secure_ajax(planning.Memoriser_reglages), name='ajax_planning_equipe_memoriser_reglages'),
    path('collaborateurs/planning_equipe/imprimer', secure_ajax(planning.Imprimer), name='ajax_planning_equipe_imprimer'),
    path('collaborateurs/planning_equipe/envoyer_emails', secure_ajax(planning.Envoyer_emails), name='ajax_planning_equipe_envoyer_emails'),
    path('collaborateurs/planning_equipe/exporter_recapitulatif', secure_ajax(planning.Exporter_recapitulatif), name='ajax_planning_equipe_exporter_recapitulatif'),
    path('collaborateurs/planning_equipe/get_lien_ical', secure_ajax(planning.Get_lien_ical), name='ajax_planning_equipe_get_lien_ical'),
    path('collaborateurs/planning_individuel/get_donnees', secure_ajax(planning_individuel.Get_donnees), name='ajax_planning_individuel_get_donnees'),
    path('collaborateurs/planning_individuel/get_anomalies', secure_ajax(planning_individuel.Get_anomalies), name='ajax_planning_individuel_get_anomalies'),
    path('collaborateurs/planning_individuel/get_objectif', secure_ajax(planning_individuel.Get_objectif), name='ajax_planning_individuel_get_objectif'),
    path('collaborateurs/planning_individuel/memoriser_preferences', secure_ajax(planning_individuel.Memoriser_preferences), name='ajax_planning_individuel_memoriser_preferences'),
    path('collaborateurs/planning_individuel/enregistrer_parametres', secure_ajax(planning_individuel.Enregistrer_parametres), name='ajax_planning_individuel_enregistrer_parametres'),
    path('collaborateurs/planning_individuel/enregistrer', secure_ajax(planning_individuel.Enregistrer), name='ajax_planning_individuel_enregistrer'),
    path('collaborateurs/planning_individuel/appliquer_modele', secure_ajax(planning_individuel.Appliquer_modele), name='ajax_planning_individuel_appliquer_modele'),
    path('collaborateurs/planning_individuel/enregistrer_ajustement', secure_ajax(planning_individuel.Enregistrer_ajustement), name='ajax_planning_individuel_enregistrer_ajustement'),
    path('collaborateurs/planning_individuel/supprimer_ajustement', secure_ajax(planning_individuel.Supprimer_ajustement), name='ajax_planning_individuel_supprimer_ajustement'),
    path('collaborateurs/planning_individuel/reporter_solde', secure_ajax(planning_individuel.Reporter_solde), name='ajax_planning_individuel_reporter_solde'),
    path('collaborateurs/planning_individuel/imprimer', secure_ajax(planning_individuel.Imprimer), name='ajax_planning_individuel_imprimer'),
    path('collaborateurs/planning_individuel/envoyer_email', secure_ajax(planning_individuel.Envoyer_email), name='ajax_planning_individuel_envoyer_email'),
    path('collaborateurs/planning_individuel/exporter_excel', secure_ajax(planning_individuel.Exporter_excel), name='ajax_planning_individuel_exporter_excel'),
    path('collaborateurs/planning_individuel/get_lien_ical', secure_ajax(planning_individuel.Get_lien_ical), name='ajax_planning_individuel_get_lien_ical'),
    path('collaborateurs/planning_individuel/reporter_soldes', secure_ajax(planning_individuel.Reporter_soldes), name='ajax_planning_individuel_reporter_soldes'),

    # Congés et absences
    path('collaborateurs/conges/get_demandes', secure_ajax(conges.Get_demandes), name='ajax_conges_get_demandes'),
    path('collaborateurs/conges/calculer', secure_ajax(conges.Calculer), name='ajax_conges_calculer'),
    path('collaborateurs/conges/enregistrer_demande', secure_ajax(conges.Enregistrer_demande), name='ajax_conges_enregistrer_demande'),
    path('collaborateurs/conges/apercu', secure_ajax(conges.Apercu), name='ajax_conges_apercu'),
    path('collaborateurs/conges/decider', secure_ajax(conges.Decider), name='ajax_conges_decider'),
    path('collaborateurs/conges/annuler', secure_ajax(conges.Annuler), name='ajax_conges_annuler'),
    path('collaborateurs/conges/get_compteurs', secure_ajax(conges.Get_compteurs), name='ajax_conges_get_compteurs'),
    path('collaborateurs/conges/enregistrer_droits', secure_ajax(conges.Enregistrer_droits), name='ajax_conges_enregistrer_droits'),
    path('collaborateurs/conges/supprimer_droit', secure_ajax(conges.Supprimer_droit), name='ajax_conges_supprimer_droit'),
    path('collaborateurs/contrats/collaborateur_fusionner_contrat', secure_ajax(collaborateur_voir_contrat.Fusionner), name='ajax_collaborateur_fusionner_contrat'),
    path('collaborateurs/contrats/collaborateur_fusionner_contrats', secure_ajax(fusionner_contrats_word.Fusionner), name='ajax_collaborateur_fusionner_contrats'),
    path('collaborateurs/statistiques_evenements/exporter_excel', secure_ajax(statistiques_evenements.Exporter_excel), name='ajax_statistiques_evenements_collaborateurs_exporter_excel'),
    path('collaborateurs/statistiques_evenements/generer_pdf', secure_ajax(statistiques_evenements.Generer_pdf), name='ajax_statistiques_evenements_collaborateurs_generer_pdf'),
    path('collaborateurs/importer_collaborateurs/importer', secure_ajax(importer_collaborateurs.Importer), name='ajax_importer_collaborateurs_importer'),

]
