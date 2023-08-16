# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from collaborateurs.views import collaborateur, collaborateur_identite, collaborateur_questionnaire, collaborateur_coords, collaborateur_qualifications, \
                                collaborateur_pieces, collaborateur_notes, collaborateur_contrats, collaborateur_evenements, planning_collaborateurs, \
                                collaborateur_appliquer_modele_planning, liste_contrats, collaborateur_outils, collaborateur_historique, \
                                collaborateur_emails, collaborateur_sms, appliquer_modele_planning, collaborateur_groupes, collaborateur_voir_contrat, \
                                fusionner_contrats_word


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
    path('collaborateurs/collaborateurs/historique/<int:idcollaborateur>', collaborateur_historique.Liste.as_view(), name='collaborateur_historique'),
    path('collaborateurs/collaborateurs/emails/ajouter/<int:idcollaborateur>', collaborateur_emails.Ajouter.as_view(), name='collaborateur_emails_ajouter'),
    path('collaborateurs/collaborateurs/sms/ajouter/<int:idcollaborateur>', collaborateur_sms.Ajouter.as_view(), name='collaborateur_sms_ajouter'),

    path('collaborateurs/collaborateurs/notes/ajouter/<int:idcollaborateur>', collaborateur_notes.Ajouter.as_view(), name='collaborateur_notes_ajouter'),
    path('collaborateurs/collaborateurs/notes/modifier/<int:idcollaborateur>/<int:pk>', collaborateur_notes.Modifier.as_view(), name='collaborateur_notes_modifier'),
    path('collaborateurs/collaborateurs/notes/supprimer/<int:idcollaborateur>/<int:pk>', collaborateur_notes.Supprimer.as_view(), name='collaborateur_notes_supprimer'),

    path('collaborateurs/liste_contrats', liste_contrats.Liste.as_view(), name='contrats_liste'),

    path('collaborateurs/fusionner_contrats_word', fusionner_contrats_word.Liste.as_view(), name='fusionner_contrats_word'),

    # Gestion des évènements
    path('collaborateurs/appliquer_modele_planning', appliquer_modele_planning.View.as_view(), name='appliquer_modele_planning'),
    path('collaborateurs/planning_collaborateurs', planning_collaborateurs.View.as_view(), name='planning_collaborateurs'),


    # AJAX
    path('collaborateurs/planning/get_collaborateurs', secure_ajax(planning_collaborateurs.Get_collaborateurs), name='ajax_planning_collaborateurs_get_collaborateurs'),
    path('collaborateurs/planning/get_evenements', secure_ajax(planning_collaborateurs.Get_evenements), name='ajax_planning_collaborateurs_get_evenements'),
    path('collaborateurs/planning/get_form_detail_evenement', secure_ajax(planning_collaborateurs.Get_form_detail_evenement), name='ajax_planning_collaborateurs_get_form_detail_evenement'),
    path('collaborateurs/planning/valid_form_detail_evenement', secure_ajax(planning_collaborateurs.Valid_form_detail_evenement), name='ajax_planning_collaborateurs_valid_form_detail_evenement'),
    path('collaborateurs/planning/modifier_evenement', secure_ajax(planning_collaborateurs.Modifier_evenement), name='ajax_planning_collaborateurs_modifier_evenement'),
    path('collaborateurs/planning/supprimer_evenement', secure_ajax(planning_collaborateurs.Supprimer_evenement), name='ajax_planning_collaborateurs_supprimer_evenement'),
    path('collaborateurs/planning/get_form_appliquer_modele', secure_ajax(planning_collaborateurs.Get_form_appliquer_modele), name='ajax_planning_collaborateurs_get_form_appliquer_modele'),
    path('collaborateurs/planning/valid_form_appliquer_modele', secure_ajax(planning_collaborateurs.Valid_form_appliquer_modele), name='ajax_planning_collaborateurs_valid_form_appliquer_modele'),
    path('collaborateurs/contrats/collaborateur_fusionner_contrat', secure_ajax(collaborateur_voir_contrat.Fusionner), name='ajax_collaborateur_fusionner_contrat'),
    path('collaborateurs/contrats/collaborateur_fusionner_contrats', secure_ajax(fusionner_contrats_word.Fusionner), name='ajax_collaborateur_fusionner_contrats'),

]
