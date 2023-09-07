#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from django.contrib.auth import views as auth_views
from core.views import login, accueil, accueil_configuration, recherche, base, profil_configuration, profil_utilisateur, change_password_utilisateur, select_avec_commandes_advanced
from core.forms import filtre_liste
from core.decorators import secure_ajax
from core.utils import utils_graphique_individus


urlpatterns = [
    path('', accueil.Accueil.as_view(), name='accueil'),
    path('accueil_configuration', accueil_configuration.View.as_view(), name='accueil_configuration'),
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
    path('core/memorise_parametre', secure_ajax(base.Memorise_parametre), name='ajax_memorise_parametre'),
    path('core/memorise_tri_liste', secure_ajax(base.Memorise_tri_liste), name='ajax_memorise_tri_liste'),
    path('core/memorise_hiddens_columns', secure_ajax(base.Memorise_hidden_columns), name='ajax_memorise_hidden_columns'),
    path('core/memorise_page_length', secure_ajax(base.Memorise_page_length), name='ajax_memorise_page_length'),
    # path('core/memorise_structure', secure_ajax(base.Memorise_structure), name='ajax_memorise_structure'),
    path('core/modifier_profil_configuration', secure_ajax(profil_configuration.Modifier_profil_configuration), name='ajax_modifier_profil_configuration'),
    path('core/graphique_individus_get_parametres', secure_ajax(utils_graphique_individus.Get_parametres), name='ajax_graphique_individus_get_parametres'),
    path('core/graphique_individus_set_parametres', secure_ajax(utils_graphique_individus.Set_parametres), name='ajax_graphique_individus_set_parametres'),
    path('core/select_avec_commandes_advanced', secure_ajax(select_avec_commandes_advanced.Modifier), name='ajax_select_avec_commandes_advanced'),
    path('core/purger_filtres_listes', secure_ajax(profil_utilisateur.Purger_filtres_listes), name='ajax_purger_filtres_listes'),

]
