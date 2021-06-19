#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import accueil, recherche, base, profil_configuration, profil_utilisateur, change_password_utilisateur
from django.contrib.auth import views as auth_views
from core.forms import filtre_liste
from core.views import login
from core.decorators import secure_ajax


urlpatterns = [
    path('', accueil.Accueil.as_view(), name='accueil'),
    path('connexion', login.LoginViewUtilisateur.as_view(), name='connexion'),
    path('deconnexion', auth_views.LogoutView.as_view(next_page='connexion'), name='deconnexion'),

    # Recherche
    path('core/rechercher', recherche.View.as_view(), name='rechercher'),

    # Profil utilisateur
    path('core/profil', profil_utilisateur.View.as_view(), name='profil_utilisateur'),
    path('core/change_password_utilisateur', change_password_utilisateur.View.as_view(), name='change_password_utilisateur'),

    # AJAX
    path('core/filtre_liste', secure_ajax(filtre_liste.Get_form_filtres), name='ajax_get_form_filtre_liste'),
    path('core/ajouter_filtre_liste', secure_ajax(filtre_liste.Ajouter_filtre), name='ajax_ajouter_filtre_liste'),
    path('core/supprimer_filtre_liste/<int:idfiltre>', filtre_liste.Supprimer_filtre, name='ajax_supprimer_filtre_liste'),
    path('core/memoriser_recherche', secure_ajax(recherche.Memoriser_recherche), name='ajax_memoriser_recherche'),
    path('core/memorise_option', secure_ajax(base.Memorise_option), name='ajax_memorise_option'),
    # path('core/memorise_structure', secure_ajax(base.Memorise_structure), name='ajax_memorise_structure'),
    path('core/modifier_profil_configuration', secure_ajax(profil_configuration.Modifier_profil_configuration), name='ajax_modifier_profil_configuration'),


]

