# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from outils.views import editeur_emails, editeur_emails_express, historique, update, sauvegarde_creer, sauvegarde_restaurer, statistiques, contacts, \
                        editeur_emails_familles, editeur_emails_individus, editeur_emails_contacts, editeur_emails_listes_diffusion, \
                        editeur_emails_saisie_libre, emails, notes_versions

urlpatterns = [

    # Table des matières
    path('outils/', toc.Toc.as_view(menu_code="outils_toc"), name='outils_toc'),

    # Statistiques
    path('outils/statistiques', statistiques.View.as_view(), name='statistiques'),

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
    path('outils/editeur_emails/contacts/<int:idmail>', editeur_emails_contacts.Liste.as_view(), name='editeur_emails_contacts'),
    path('outils/editeur_emails/listes_diffusion/<int:idmail>', editeur_emails_listes_diffusion.Liste.as_view(), name='editeur_emails_listes_diffusion'),
    path('outils/editeur_emails/saisie_libre/<int:idmail>', editeur_emails_saisie_libre.Liste.as_view(), name='editeur_emails_saisie_libre'),

    path('outils/emails/liste', emails.Liste.as_view(), name='emails_liste'),
    path('outils/emails/supprimer/<int:pk>', emails.Supprimer.as_view(), name='emails_supprimer'),
    path('outils/emails/supprimer_plusieurs/<str:listepk>', emails.Supprimer_plusieurs.as_view(), name='emails_supprimer_plusieurs'),


    path('outils/historique', historique.Liste.as_view(), name='historique'),
    path('outils/update', update.View.as_view(), name='update'),
    path('outils/notes_versions', notes_versions.View.as_view(), name='notes_versions'),

    # Sauvegarde
    path('outils/sauvegarde/creer', sauvegarde_creer.View.as_view(), name='sauvegarde_creer'),
    path('outils/sauvegarde/restaurer', sauvegarde_restaurer.View.as_view(), name='sauvegarde_restaurer'),



    # AJAX
    path('outils/get_modele_email', secure_ajax(editeur_emails.Get_modele_email), name='ajax_get_modele_email'),
    path('outils/get_view_editeur_email', secure_ajax(editeur_emails_express.Get_view_editeur_email), name='ajax_get_view_editeur_email'),
    path('outils/envoyer_email_express', secure_ajax(editeur_emails_express.Envoyer_email), name='ajax_envoyer_email_express'),

]
