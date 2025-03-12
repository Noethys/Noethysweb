# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from outils.views import editeur_emails, editeur_emails_express, historique, update, sauvegarde_creer, statistiques, contacts, \
                        editeur_emails_familles, editeur_emails_individus, editeur_emails_collaborateurs, editeur_emails_contacts, editeur_emails_listes_diffusion, \
                        editeur_emails_saisie_libre, emails, notes_versions, messages_portail, notes, calendrier_annuel, \
                        demandes_portail, liste_conso_sans_presta, statistiques_portail, correcteur, editeur_sms, editeur_sms_familles, \
                        editeur_sms_individus, editeur_sms_collaborateurs, editeur_sms_saisie_libre, sms, utilisateurs_bloques, procedures, editeur_sms_express, taches, \
                        suivi_reservations, commandes, desk_creer, editeur_emails_inscriptions, editeur_emails_activites

urlpatterns = [

    # Table des matières
    path('outils/', toc.Toc.as_view(menu_code="outils_toc"), name='outils_toc'),

    # Statistiques
    path('outils/statistiques', statistiques.View.as_view(), name='statistiques'),
    path('outils/statistiques_portail', statistiques_portail.View.as_view(), name='statistiques_portail'),

    # Carnets de contacts
    path('outils/contacts/liste', contacts.Liste.as_view(), name='contacts_liste'),
    path('outils/contacts/ajouter', contacts.Ajouter.as_view(), name='contacts_ajouter'),
    path('outils/contacts/modifier/<int:pk>', contacts.Modifier.as_view(), name='contacts_modifier'),
    path('outils/contacts/supprimer/<int:pk>', contacts.Supprimer.as_view(), name='contacts_supprimer'),

    # Editeur d'emails
    path('outils/editeur_emails', editeur_emails.Ajouter.as_view(), name='editeur_emails'),
    path('outils/editeur_emails/<int:pk>', editeur_emails.Modifier.as_view(), name='editeur_emails'),
    path('outils/editeur_emails/familles/<int:idmail>', editeur_emails_familles.Liste.as_view(), name='editeur_emails_familles'),
    path('outils/editeur_emails/individus/<int:idmail>', editeur_emails_individus.Liste.as_view(), name='editeur_emails_individus'),
    path('outils/editeur_emails/collaborateurs/<int:idmail>', editeur_emails_collaborateurs.Liste.as_view(), name='editeur_emails_collaborateurs'),
    path('outils/editeur_emails/contacts/<int:idmail>', editeur_emails_contacts.Liste.as_view(), name='editeur_emails_contacts'),
    path('outils/editeur_emails/listes_diffusion/<int:idmail>', editeur_emails_listes_diffusion.Liste.as_view(), name='editeur_emails_listes_diffusion'),
    path('outils/editeur_emails/saisie_libre/<int:idmail>', editeur_emails_saisie_libre.Liste.as_view(), name='editeur_emails_saisie_libre'),
    path('outils/editeur_emails/exporter_excel', secure_ajax(editeur_emails.Exporter_excel), name='ajax_editeur_emails_exporter_excel'),

    path('outils/editeur_emails/inscriptions', editeur_emails_inscriptions.Liste.as_view(), name='editeur_emails_inscriptions'),
    path('outils/editeur_emails/inscriptions_emails_pdf', secure_ajax(editeur_emails_inscriptions.Impression_pdf),name='ajax_inscriptions_emails_pdf'),
    path('outils/editeur_emails/activites', editeur_emails_activites.Liste.as_view(),name='editeur_emails_activites'),
    path('outils/editeur_emails/activites_emails_pdf', secure_ajax(editeur_emails_activites.Impression_pdf),name='ajax_activites_emails_pdf'),
    path('outils/editeur_emails/activites/transferer_activites/', editeur_emails_activites.Transferer_activites, name='transferer_activites'),

    path('outils/emails/liste', emails.Liste.as_view(), name='emails_liste'),
    path('outils/emails/supprimer/<int:pk>', emails.Supprimer.as_view(), name='emails_supprimer'),
    path('outils/emails/supprimer_plusieurs/<str:listepk>', emails.Supprimer_plusieurs.as_view(), name='emails_supprimer_plusieurs'),

    # Editeur de SMS
    path('outils/editeur_sms', editeur_sms.Ajouter.as_view(), name='editeur_sms'),
    path('outils/editeur_sms/<int:pk>', editeur_sms.Modifier.as_view(), name='editeur_sms'),
    path('outils/editeur_sms/familles/<int:idsms>', editeur_sms_familles.Liste.as_view(), name='editeur_sms_familles'),
    path('outils/editeur_sms/individus/<int:idsms>', editeur_sms_individus.Liste.as_view(), name='editeur_sms_individus'),
    path('outils/editeur_sms/collaborateurs/<int:idsms>', editeur_sms_collaborateurs.Liste.as_view(), name='editeur_sms_collaborateurs'),
    path('outils/editeur_sms/saisie_libre/<int:idsms>', editeur_sms_saisie_libre.Liste.as_view(), name='editeur_sms_saisie_libre'),

    path('outils/sms/liste', sms.Liste.as_view(), name='sms_liste'),
    path('outils/sms/supprimer/<int:pk>', sms.Supprimer.as_view(), name='sms_supprimer'),
    path('outils/sms/supprimer_plusieurs/<str:listepk>', sms.Supprimer_plusieurs.as_view(), name='sms_supprimer_plusieurs'),

    path('outils/historique', historique.Liste.as_view(), name='historique'),

    # Maintenance
    path('outils/update', update.View.as_view(), name='update'),
    path('outils/notes_versions', notes_versions.View.as_view(), name='notes_versions'),
    path('outils/utilisateurs_bloques/liste', utilisateurs_bloques.Liste.as_view(), name='utilisateurs_bloques_liste'),
    path('outils/utilisateurs_bloques/supprimer/<int:pk>', utilisateurs_bloques.Supprimer.as_view(), name='utilisateurs_bloques_supprimer'),
    path('outils/utilisateurs_bloques/supprimer_plusieurs/<str:listepk>', utilisateurs_bloques.Supprimer_plusieurs.as_view(), name='utilisateurs_bloques_supprimer_plusieurs'),

    # Calendrier annuel
    path('outils/calendrier_annuel', calendrier_annuel.View.as_view(), name='calendrier_annuel'),

    # Notes
    path('outils/notes/liste', notes.Liste.as_view(), name='notes_liste'),
    path('outils/notes/ajouter', notes.Ajouter.as_view(), name='notes_ajouter'),
    path('outils/notes/modifier/<int:pk>', notes.Modifier.as_view(), name='notes_modifier'),
    path('outils/notes/supprimer/<int:pk>', notes.Supprimer.as_view(), name='notes_supprimer'),

    # Tâches
    path('outils/taches/liste', taches.Liste.as_view(), name='taches_liste'),
    path('outils/taches/ajouter', taches.Ajouter.as_view(), name='taches_ajouter'),
    path('outils/taches/modifier/<int:pk>', taches.Modifier.as_view(), name='taches_modifier'),
    path('outils/taches/supprimer/<int:pk>', taches.Supprimer.as_view(), name='taches_supprimer'),

    # Sauvegarde
    path('outils/sauvegarde/creer', sauvegarde_creer.View.as_view(), name='sauvegarde_creer'),
    path('outils/desk/creer', desk_creer.View.as_view(), name='desk_creer'),

    # Commandes
    path('outils/commandes/liste', commandes.Liste.as_view(), name='commandes_liste'),
    path('outils/commandes/ajouter', commandes.Ajouter.as_view(), name='commandes_ajouter'),
    path('outils/commandes/modifier/<int:pk>', commandes.Modifier.as_view(), name='commandes_modifier'),
    path('outils/commandes/supprimer/<int:pk>', commandes.Supprimer.as_view(), name='commandes_supprimer'),
    path('outils/commandes/consulter/<int:pk>', commandes.Consulter.as_view(), name='commandes_consulter'),
    path('outils/commandes/consulter/<int:pk>/<int:idversion>', commandes.Consulter.as_view(), name='commandes_consulter'),

    # Portail
    path('outils/portail/messages/liste', messages_portail.Liste.as_view(), name='messages_portail_liste'),
    path('outils/portail/messages/supprimer/<int:pk>', messages_portail.Supprimer.as_view(), name='messages_portail_supprimer'),

    path('outils/portail/renseignements/liste', demandes_portail.Liste.as_view(), name='demandes_portail_liste'),

    path('individus/suivi_reservations', suivi_reservations.View.as_view(), name='suivi_reservations'),

    # Dépannage
    path('outils/correcteur', correcteur.View.as_view(), name='correcteur'),
    path('outils/liste_conso_sans_presta', liste_conso_sans_presta.Liste.as_view(), name='liste_conso_sans_presta'),
    path('outils/liste_conso_sans_presta_supprimer_plusieurs/<str:listepk>', liste_conso_sans_presta.Supprimer_plusieurs.as_view(), name='liste_conso_sans_presta_supprimer_plusieurs'),

    # Utilitaires
    path('outils/procedures', procedures.View.as_view(), name='procedures'),

    # AJAX
    path('outils/get_modele_email', secure_ajax(editeur_emails.Get_modele_email), name='ajax_get_modele_email'),
    path('outils/get_signature_email', secure_ajax(editeur_emails.Get_signature_email), name='ajax_get_signature_email'),
    path('outils/get_view_editeur_email', secure_ajax(editeur_emails_express.Get_view_editeur_email), name='ajax_get_view_editeur_email'),
    path('outils/envoyer_email_express', secure_ajax(editeur_emails_express.Envoyer_email), name='ajax_envoyer_email_express'),
    path('outils/get_view_editeur_sms', secure_ajax(editeur_sms_express.Get_view_editeur_sms), name='ajax_get_view_editeur_sms'),
    path('outils/envoyer_sms_express', secure_ajax(editeur_sms_express.Envoyer_sms), name='ajax_envoyer_sms_express'),
    path('outils/get_modele_sms', secure_ajax(editeur_sms.Get_modele_sms), name='ajax_get_modele_sms'),
    path('outils/get_calendrier_annuel', secure_ajax(calendrier_annuel.Get_calendrier_annuel), name='ajax_get_calendrier_annuel'),
    path('outils/portail/demandes/', secure_ajax(demandes_portail.Appliquer_modification), name='ajax_appliquer_modification_portail'),
    path('outils/portail/tout_valider/', secure_ajax(demandes_portail.Tout_valider), name='ajax_tout_valider_portail'),
    path('outils/sauvegarder_db/', secure_ajax(sauvegarde_creer.Sauvegarder_db), name='ajax_sauvegarder_db'),
    path('outils/sauvegarder_media/', secure_ajax(sauvegarde_creer.Sauvegarder_media), name='ajax_sauvegarder_media'),
    path('outils/sauvegarder_liste/', secure_ajax(sauvegarde_creer.Get_liste_sauvegardes), name='ajax_get_liste_sauvegardes'),
    path('outils/get_suivi_reservations', secure_ajax(suivi_reservations.Get_suivi_reservations), name='ajax_get_suivi_reservations'),
    path('outils/reservations_get_form_activites', secure_ajax(suivi_reservations.Get_form_activites), name='ajax_reservations_get_form_activites'),
    path('outils/reservations_get_form_periode', secure_ajax(suivi_reservations.Get_form_periode), name='ajax_reservations_get_form_periode'),
    path('outils/reservations_valider_form_activites', secure_ajax(suivi_reservations.Valider_form_activites), name='ajax_reservations_valider_form_activites'),
    path('outils/reservations_valider_form_periode', secure_ajax(suivi_reservations.Valider_form_periode), name='ajax_reservations_valider_form_periode'),
    path('outils/commandes/generer_pdf', secure_ajax(commandes.Generer_pdf), name='ajax_commandes_generer_pdf'),
    path('outils/desk_creer/', secure_ajax(desk_creer.Generer), name='ajax_desk_generer'),
]
