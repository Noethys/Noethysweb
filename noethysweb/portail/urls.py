# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from portail.views import accueil, login
from django.contrib.auth import views as auth_views
from portail.views import reset_password, change_password
from core.decorators import secure_ajax



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


    # AJAX
    # path('outils/get_modele_email', secure_ajax(editeur_emails.Get_modele_email), name='ajax_get_modele_email'),

]
