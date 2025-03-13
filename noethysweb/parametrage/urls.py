#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc
from core.decorators import secure_ajax
from parametrage.views import organisateur, structures, \
    vacances, calendrier, vacances_importation, feries_fixes, feries_variables, feries_generation, \
    comptes_bancaires, modes_reglements, emetteurs, \
    lots_factures, prefixes_factures, regies, messages_factures, \
    types_pieces, regimes, caisses, types_quotients, categories_travail, secteurs, types_sieste, \
    categories_informations, types_maladies, types_vaccins, medecins, \
    niveaux_scolaires, ecoles, classes, types_cotisations, unites_cotisations, \
    restaurateurs, menus_categories, menus_legendes, notes_categories, listes_diffusion, \
    types_groupes_activites, activites, activites_generalites, activites_responsables, activites_agrements, activites_groupes, \
    activites_renseignements, activites_unites_conso, activites_unites_remplissage, activites_calendrier, \
    activites_ouvertures, activites_evenements, activites_evenements_tarifs, activites_categories_tarifs, activites_noms_tarifs, \
    activites_tarifs, activites_portail_parametres, activites_portail_periodes, \
    modeles_documents, modeles_emails, modeles_sms, modeles_rappels, signatures_emails, \
    questionnaires, adresses_mail, activites_assistant, activites_assistant_sejour, activites_assistant_cantine, \
    activites_assistant_sorties, activites_assistant_stage, activites_assistant_annuelle, \
    portail_parametres, types_regimes_alimentaires, assureurs, categories_compte_internet, modeles_pes, \
    types_consentements, unites_consentements, articles, images_articles, albums, images_fond, portail_documents, portail_parametres_renseignements, \
    configurations_sms, perceptions, modeles_prelevements, taches_recurrentes, modeles_prestations, \
    categories_produits, produits, produits_tarifs, postes_analytiques, comptes_comptables, categories_comptables, tiers, budgets, \
    types_qualifications_collaborateurs, types_pieces_collaborateurs, types_evenements_collaborateurs, types_postes_collaborateurs, \
    modeles_plannings_collaborateurs, groupes_collaborateurs, modeles_aides, transports, compagnies, lignes, lieux, arrets, modeles_impressions, \
    modeles_word, releves_bancaires, sondages, achats_categories, achats_fournisseurs, modeles_commandes, modeles_commandes_colonnes, \
    activites_evenements_categories, activites_import_export, parametres_generaux


urlpatterns = [

    # Table des matières
    path('parametrage/', toc.Toc.as_view(menu_code="parametrage_toc"), name='parametrage_toc'),

    # Organisateur
    path('parametrage/organisateur/ajouter', organisateur.Ajouter.as_view(), name='organisateur_ajouter'),
    path('parametrage/organisateur/modifier/<int:pk>', organisateur.Modifier.as_view(), name='organisateur_modifier'),

    # Paramètres généraux
    path('parametrage/parametres_generaux/', parametres_generaux.Modifier.as_view(), name='parametres_generaux'),
    # Structures
    path('parametrage/structures/liste', structures.Liste.as_view(), name='structures_liste'),
    path('parametrage/structures/ajouter', structures.Ajouter.as_view(), name='structures_ajouter'),
    path('parametrage/structures/modifier/<int:pk>', structures.Modifier.as_view(), name='structures_modifier'),
    path('parametrage/structures/supprimer/<int:pk>', structures.Supprimer.as_view(), name='structures_supprimer'),

    # Groupes d'activités
    path('parametrage/types_groupes_activites/liste', types_groupes_activites.Liste.as_view(), name='types_groupes_activites_liste'),
    path('parametrage/types_groupes_activites/ajouter', types_groupes_activites.Ajouter.as_view(), name='types_groupes_activites_ajouter'),
    path('parametrage/types_groupes_activites/modifier/<int:pk>', types_groupes_activites.Modifier.as_view(), name='types_groupes_activites_modifier'),
    path('parametrage/types_groupes_activites/supprimer/<int:pk>', types_groupes_activites.Supprimer.as_view(), name='types_groupes_activites_supprimer'),

    # Activites
    path('parametrage/activites/liste', activites.Liste.as_view(), name='activites_liste'),
    path('parametrage/activites/ajouter', activites.Ajouter.as_view(), name='activites_ajouter'),
    path('parametrage/activites/supprimer/<int:idactivite>', activites.Supprimer.as_view(), name='activites_supprimer'),
    path('parametrage/activites/resume/<int:idactivite>', activites.Resume.as_view(), name='activites_resume'),
    path('parametrage/activites/dupliquer/<int:pk>', activites.Dupliquer.as_view(), name='activites_dupliquer'),
    path('parametrage/activites/import_export', activites_import_export.View.as_view(), name='activites_import_export'),

    path('parametrage/activites/generalites/<int:idactivite>', activites_generalites.Consulter.as_view(), name='activites_generalites'),
    path('parametrage/activites/generalites/modifier/<int:idactivite>', activites_generalites.Modifier.as_view(), name='activites_generalites_modifier'),

    path('parametrage/activites/responsables/liste/<int:idactivite>', activites_responsables.Liste.as_view(), name='activites_responsables_liste'),
    path('parametrage/activites/responsables/ajouter/<int:idactivite>', activites_responsables.Ajouter.as_view(), name='activites_responsables_ajouter'),
    path('parametrage/activites/responsables/modifier/<int:idactivite>/<int:pk>', activites_responsables.Modifier.as_view(), name='activites_responsables_modifier'),
    path('parametrage/activites/responsables/supprimer/<int:idactivite>/<int:pk>', activites_responsables.Supprimer.as_view(), name='activites_responsables_supprimer'),

    path('parametrage/activites/agrements/liste/<int:idactivite>', activites_agrements.Liste.as_view(), name='activites_agrements_liste'),
    path('parametrage/activites/agrements/ajouter/<int:idactivite>', activites_agrements.Ajouter.as_view(), name='activites_agrements_ajouter'),
    path('parametrage/activites/agrements/modifier/<int:idactivite>/<int:pk>', activites_agrements.Modifier.as_view(), name='activites_agrements_modifier'),
    path('parametrage/activites/agrements/supprimer/<int:idactivite>/<int:pk>', activites_agrements.Supprimer.as_view(), name='activites_agrements_supprimer'),

    path('parametrage/activites/groupes/liste/<int:idactivite>', activites_groupes.Liste.as_view(), name='activites_groupes_liste'),
    path('parametrage/activites/groupes/ajouter/<int:idactivite>', activites_groupes.Ajouter.as_view(), name='activites_groupes_ajouter'),
    path('parametrage/activites/groupes/modifier/<int:idactivite>/<int:pk>', activites_groupes.Modifier.as_view(), name='activites_groupes_modifier'),
    path('parametrage/activites/groupes/supprimer/<int:idactivite>/<int:pk>', activites_groupes.Supprimer.as_view(), name='activites_groupes_supprimer'),

    path('parametrage/activites/renseignements/<int:idactivite>', activites_renseignements.Consulter.as_view(), name='activites_renseignements'),
    path('parametrage/activites/renseignements/modifier/<int:idactivite>', activites_renseignements.Modifier.as_view(), name='activites_renseignements_modifier'),

    path('parametrage/activites/unites_conso/liste/<int:idactivite>', activites_unites_conso.Liste.as_view(), name='activites_unites_conso_liste'),
    path('parametrage/activites/unites_conso/ajouter/<int:idactivite>', activites_unites_conso.Ajouter.as_view(), name='activites_unites_conso_ajouter'),
    path('parametrage/activites/unites_conso/modifier/<int:idactivite>/<int:pk>', activites_unites_conso.Modifier.as_view(), name='activites_unites_conso_modifier'),
    path('parametrage/activites/unites_conso/supprimer/<int:idactivite>/<int:pk>', activites_unites_conso.Supprimer.as_view(), name='activites_unites_conso_supprimer'),

    path('parametrage/activites/unites_remplissage/liste/<int:idactivite>', activites_unites_remplissage.Liste.as_view(), name='activites_unites_remplissage_liste'),
    path('parametrage/activites/unites_remplissage/ajouter/<int:idactivite>', activites_unites_remplissage.Ajouter.as_view(), name='activites_unites_remplissage_ajouter'),
    path('parametrage/activites/unites_remplissage/modifier/<int:idactivite>/<int:pk>', activites_unites_remplissage.Modifier.as_view(), name='activites_unites_remplissage_modifier'),
    path('parametrage/activites/unites_remplissage/supprimer/<int:idactivite>/<int:pk>', activites_unites_remplissage.Supprimer.as_view(), name='activites_unites_remplissage_supprimer'),

    path('parametrage/activites/calendrier/<int:idactivite>', activites_calendrier.View.as_view(), name='activites_calendrier'),
    path('parametrage/activites/ouvertures/<int:idactivite>', activites_ouvertures.Modifier.as_view(), name='activites_ouvertures'),

    path('parametrage/activites/evenements/liste/<int:idactivite>', activites_evenements.Liste.as_view(), name='activites_evenements_liste'),
    path('parametrage/activites/evenements/ajouter/<int:idactivite>', activites_evenements.Ajouter.as_view(), name='activites_evenements_ajouter'),
    path('parametrage/activites/evenements/modifier/<int:idactivite>/<int:pk>', activites_evenements.Modifier.as_view(), name='activites_evenements_modifier'),
    path('parametrage/activites/evenements/supprimer/<int:idactivite>/<int:pk>', activites_evenements.Supprimer.as_view(), name='activites_evenements_supprimer'),

    path('parametrage/activites/tarifs_evenements/liste/<int:idactivite>/<int:evenement>', activites_evenements_tarifs.Liste.as_view(), name='activites_evenements_tarifs_liste'),
    path('parametrage/activites/tarifs_evenements/ajouter/<int:idactivite>/<int:evenement>', activites_evenements_tarifs.Ajouter.as_view(), name='activites_evenements_tarifs_ajouter'),
    path('parametrage/activites/tarifs_evenements/modifier/<int:idactivite>/<int:evenement>/<int:pk>', activites_evenements_tarifs.Modifier.as_view(), name='activites_evenements_tarifs_modifier'),
    path('parametrage/activites/tarifs_evenements/supprimer/<int:idactivite>/<int:evenement>/<int:pk>', activites_evenements_tarifs.Supprimer.as_view(), name='activites_evenements_tarifs_supprimer'),
    path('parametrage/activites/tarifs_evenements/dupliquer/<int:idactivite>/<int:evenement>/<int:pk>', activites_evenements_tarifs.Dupliquer.as_view(), name='activites_evenements_tarifs_dupliquer'),

    path('parametrage/activites/categories_evenements/liste/<int:idactivite>', activites_evenements_categories.Liste.as_view(), name='activites_evenements_categories_liste'),
    path('parametrage/activites/categories_evenements/ajouter/<int:idactivite>', activites_evenements_categories.Ajouter.as_view(), name='activites_evenements_categories_ajouter'),
    path('parametrage/activites/categories_evenements/modifier/<int:idactivite>/<int:pk>', activites_evenements_categories.Modifier.as_view(), name='activites_evenements_categories_modifier'),
    path('parametrage/activites/categories_evenements/supprimer/<int:idactivite>/<int:pk>', activites_evenements_categories.Supprimer.as_view(), name='activites_evenements_categories_supprimer'),

    path('parametrage/activites/categories_tarifs/liste/<int:idactivite>', activites_categories_tarifs.Liste.as_view(), name='activites_categories_tarifs_liste'),
    path('parametrage/activites/categories_tarifs/ajouter/<int:idactivite>', activites_categories_tarifs.Ajouter.as_view(), name='activites_categories_tarifs_ajouter'),
    path('parametrage/activites/categories_tarifs/modifier/<int:idactivite>/<int:pk>', activites_categories_tarifs.Modifier.as_view(), name='activites_categories_tarifs_modifier'),
    path('parametrage/activites/categories_tarifs/supprimer/<int:idactivite>/<int:pk>', activites_categories_tarifs.Supprimer.as_view(), name='activites_categories_tarifs_supprimer'),

    path('parametrage/activites/noms_tarifs/liste/<int:idactivite>', activites_noms_tarifs.Liste.as_view(), name='activites_noms_tarifs_liste'),
    path('parametrage/activites/noms_tarifs/ajouter/<int:idactivite>', activites_noms_tarifs.Ajouter.as_view(), name='activites_noms_tarifs_ajouter'),
    path('parametrage/activites/noms_tarifs/modifier/<int:idactivite>/<int:pk>', activites_noms_tarifs.Modifier.as_view(), name='activites_noms_tarifs_modifier'),
    path('parametrage/activites/noms_tarifs/supprimer/<int:idactivite>/<int:pk>', activites_noms_tarifs.Supprimer.as_view(), name='activites_noms_tarifs_supprimer'),

    path('parametrage/activites/tarifs/liste/<int:idactivite>', activites_tarifs.Liste.as_view(), name='activites_tarifs_liste'),
    path('parametrage/activites/tarifs/liste/<int:idactivite>/<int:categorie>', activites_tarifs.Liste.as_view(), name='activites_tarifs_liste'),
    path('parametrage/activites/tarifs/ajouter/<int:idactivite>/<int:categorie>', activites_tarifs.Ajouter.as_view(), name='activites_tarifs_ajouter'),
    path('parametrage/activites/tarifs/modifier/<int:idactivite>/<int:categorie>/<int:pk>', activites_tarifs.Modifier.as_view(), name='activites_tarifs_modifier'),
    path('parametrage/activites/tarifs/supprimer/<int:idactivite>/<int:categorie>/<int:pk>', activites_tarifs.Supprimer.as_view(), name='activites_tarifs_supprimer'),
    path('parametrage/activites/tarifs/dupliquer/<int:idactivite>/<int:categorie>/<int:pk>', activites_tarifs.Dupliquer.as_view(), name='activites_tarifs_dupliquer'),

    path('parametrage/activites/portail_parametres/<int:idactivite>', activites_portail_parametres.Consulter.as_view(), name='activites_portail_parametres'),
    path('parametrage/activites/portail_parametres/modifier/<int:idactivite>', activites_portail_parametres.Modifier.as_view(), name='activites_portail_parametres_modifier'),

    # path('parametrage/activites/portail_unites/liste/<int:idactivite>', activites_portail_unites.Liste.as_view(), name='activites_portail_unites_liste'),
    # path('parametrage/activites/portail_unites/ajouter/<int:idactivite>', activites_portail_unites.Ajouter.as_view(), name='activites_portail_unites_ajouter'),
    # path('parametrage/activites/portail_unites/modifier/<int:idactivite>/<int:pk>', activites_portail_unites.Modifier.as_view(), name='activites_portail_unites_modifier'),
    # path('parametrage/activites/portail_unites/supprimer/<int:idactivite>/<int:pk>', activites_portail_unites.Supprimer.as_view(), name='activites_portail_unites_supprimer'),

    path('parametrage/activites/portail_periodes/liste/<int:idactivite>', activites_portail_periodes.Liste.as_view(), name='activites_portail_periodes_liste'),
    path('parametrage/activites/portail_periodes/ajouter/<int:idactivite>', activites_portail_periodes.Ajouter.as_view(), name='activites_portail_periodes_ajouter'),
    path('parametrage/activites/portail_periodes/modifier/<int:idactivite>/<int:pk>', activites_portail_periodes.Modifier.as_view(), name='activites_portail_periodes_modifier'),
    path('parametrage/activites/portail_periodes/supprimer/<int:idactivite>/<int:pk>', activites_portail_periodes.Supprimer.as_view(), name='activites_portail_periodes_supprimer'),

    # Assistant de paramétrage
    path('parametrage/activites/assistant/liste', activites_assistant.Liste.as_view(), name='activites_assistant_liste'),
    path('parametrage/activites/assistant/sejour', activites_assistant_sejour.Assistant.as_view(), name='activites_assistant_sejour'),
    path('parametrage/activites/assistant/cantine', activites_assistant_cantine.Assistant.as_view(), name='activites_assistant_cantine'),
    path('parametrage/activites/assistant/sorties', activites_assistant_sorties.Assistant.as_view(), name='activites_assistant_sorties'),
    path('parametrage/activites/assistant/stages', activites_assistant_stage.Assistant.as_view(), name='activites_assistant_stage'),
    path('parametrage/activites/assistant/annuelle', activites_assistant_annuelle.Assistant.as_view(), name='activites_assistant_annuelle'),

    # Types de cotisations
    path('parametrage/types_cotisations/liste', types_cotisations.Liste.as_view(), name='types_cotisations_liste'),
    path('parametrage/types_cotisations/ajouter', types_cotisations.Ajouter.as_view(), name='types_cotisations_ajouter'),
    path('parametrage/types_cotisations/modifier/<int:pk>', types_cotisations.Modifier.as_view(), name='types_cotisations_modifier'),
    path('parametrage/types_cotisations/supprimer/<int:pk>', types_cotisations.Supprimer.as_view(), name='types_cotisations_supprimer'),

    # Unités de cotisations
    path('parametrage/unites_cotisations/liste', unites_cotisations.Liste.as_view(), name='unites_cotisations_liste'),
    path('parametrage/unites_cotisations/liste/<int:categorie>', unites_cotisations.Liste.as_view(), name='unites_cotisations_liste'),
    path('parametrage/unites_cotisations/ajouter/<int:categorie>', unites_cotisations.Ajouter.as_view(), name='unites_cotisations_ajouter'),
    path('parametrage/unites_cotisations/modifier/<int:categorie>/<int:pk>', unites_cotisations.Modifier.as_view(), name='unites_cotisations_modifier'),
    path('parametrage/unites_cotisations/supprimer/<int:categorie>/<int:pk>', unites_cotisations.Supprimer.as_view(), name='unites_cotisations_supprimer'),

    # Comptes bancaires
    path('parametrage/comptes_bancaires/liste', comptes_bancaires.Liste.as_view(), name='comptes_bancaires_liste'),
    path('parametrage/comptes_bancaires/ajouter', comptes_bancaires.Ajouter.as_view(), name='comptes_bancaires_ajouter'),
    path('parametrage/comptes_bancaires/modifier/<int:pk>', comptes_bancaires.Modifier.as_view(), name='comptes_bancaires_modifier'),
    path('parametrage/comptes_bancaires/supprimer/<int:pk>', comptes_bancaires.Supprimer.as_view(), name='comptes_bancaires_supprimer'),

    # Modes de règlements
    path('parametrage/modes_reglements/liste', modes_reglements.Liste.as_view(), name='modes_reglements_liste'),
    path('parametrage/modes_reglements/ajouter', modes_reglements.Ajouter.as_view(), name='modes_reglements_ajouter'),
    path('parametrage/modes_reglements/modifier/<int:pk>', modes_reglements.Modifier.as_view(), name='modes_reglements_modifier'),
    path('parametrage/modes_reglements/supprimer/<int:pk>', modes_reglements.Supprimer.as_view(), name='modes_reglements_supprimer'),

    # Emetteurs
    path('parametrage/emetteurs/liste', emetteurs.Liste.as_view(), name='emetteurs_liste'),
    path('parametrage/emetteurs/ajouter', emetteurs.Ajouter.as_view(), name='emetteurs_ajouter'),
    path('parametrage/emetteurs/modifier/<int:pk>', emetteurs.Modifier.as_view(), name='emetteurs_modifier'),
    path('parametrage/emetteurs/supprimer/<int:pk>', emetteurs.Supprimer.as_view(), name='emetteurs_supprimer'),

    # Postes analytiques
    path('parametrage/postes_analytiques/liste', postes_analytiques.Liste.as_view(), name='postes_analytiques_liste'),
    path('parametrage/postes_analytiques/ajouter', postes_analytiques.Ajouter.as_view(), name='postes_analytiques_ajouter'),
    path('parametrage/postes_analytiques/modifier/<int:pk>', postes_analytiques.Modifier.as_view(), name='postes_analytiques_modifier'),
    path('parametrage/postes_analytiques/supprimer/<int:pk>', postes_analytiques.Supprimer.as_view(), name='postes_analytiques_supprimer'),

    # Comptes comptables
    path('parametrage/comptes_comptables/liste', comptes_comptables.Liste.as_view(), name='comptes_comptables_liste'),
    path('parametrage/comptes_comptables/ajouter', comptes_comptables.Ajouter.as_view(), name='comptes_comptables_ajouter'),
    path('parametrage/comptes_comptables/modifier/<int:pk>', comptes_comptables.Modifier.as_view(), name='comptes_comptables_modifier'),
    path('parametrage/comptes_comptables/supprimer/<int:pk>', comptes_comptables.Supprimer.as_view(), name='comptes_comptables_supprimer'),

    # Catégories comptables
    path('parametrage/categories_comptables/liste', categories_comptables.Liste.as_view(), name='categories_comptables_liste'),
    path('parametrage/categories_comptables/ajouter', categories_comptables.Ajouter.as_view(), name='categories_comptables_ajouter'),
    path('parametrage/categories_comptables/modifier/<int:pk>', categories_comptables.Modifier.as_view(), name='categories_comptables_modifier'),
    path('parametrage/categories_comptables/supprimer/<int:pk>', categories_comptables.Supprimer.as_view(), name='categories_comptables_supprimer'),

    # Tiers
    path('parametrage/tiers/liste', tiers.Liste.as_view(), name='tiers_liste'),
    path('parametrage/tiers/ajouter', tiers.Ajouter.as_view(), name='tiers_ajouter'),
    path('parametrage/tiers/modifier/<int:pk>', tiers.Modifier.as_view(), name='tiers_modifier'),
    path('parametrage/tiers/supprimer/<int:pk>', tiers.Supprimer.as_view(), name='tiers_supprimer'),

    # Budgets
    path('parametrage/budgets/liste', budgets.Liste.as_view(), name='budgets_liste'),
    path('parametrage/budgets/ajouter', budgets.Ajouter.as_view(), name='budgets_ajouter'),
    path('parametrage/budgets/modifier/<int:pk>', budgets.Modifier.as_view(), name='budgets_modifier'),
    path('parametrage/budgets/supprimer/<int:pk>', budgets.Supprimer.as_view(), name='budgets_supprimer'),

    # Relevés bancaires
    path('parametrage/releves_bancaires/liste', releves_bancaires.Liste.as_view(), name='releves_bancaires_liste'),
    path('parametrage/releves_bancaires/ajouter', releves_bancaires.Ajouter.as_view(), name='releves_bancaires_ajouter'),
    path('parametrage/releves_bancaires/modifier/<int:pk>', releves_bancaires.Modifier.as_view(), name='releves_bancaires_modifier'),
    path('parametrage/releves_bancaires/supprimer/<int:pk>', releves_bancaires.Supprimer.as_view(), name='releves_bancaires_supprimer'),

    # Lots de factures
    path('parametrage/lots_factures/liste', lots_factures.Liste.as_view(), name='lots_factures_liste'),
    path('parametrage/lots_factures/ajouter', lots_factures.Ajouter.as_view(), name='lots_factures_ajouter'),
    path('parametrage/lots_factures/modifier/<int:pk>', lots_factures.Modifier.as_view(), name='lots_factures_modifier'),
    path('parametrage/lots_factures/supprimer/<int:pk>', lots_factures.Supprimer.as_view(), name='lots_factures_supprimer'),

    # Préfixes de factures
    path('parametrage/prefixes_factures/liste', prefixes_factures.Liste.as_view(), name='prefixes_factures_liste'),
    path('parametrage/prefixes_factures/ajouter', prefixes_factures.Ajouter.as_view(), name='prefixes_factures_ajouter'),
    path('parametrage/prefixes_factures/modifier/<int:pk>', prefixes_factures.Modifier.as_view(), name='prefixes_factures_modifier'),
    path('parametrage/prefixes_factures/supprimer/<int:pk>', prefixes_factures.Supprimer.as_view(), name='prefixes_factures_supprimer'),

    # Messages de facture
    path('parametrage/messages_factures/liste', messages_factures.Liste.as_view(), name='messages_factures_liste'),
    path('parametrage/messages_factures/ajouter', messages_factures.Ajouter.as_view(), name='messages_factures_ajouter'),
    path('parametrage/messages_factures/modifier/<int:pk>', messages_factures.Modifier.as_view(), name='messages_factures_modifier'),
    path('parametrage/messages_factures/supprimer/<int:pk>', messages_factures.Supprimer.as_view(), name='messages_factures_supprimer'),

    # Régies
    path('parametrage/regies/liste', regies.Liste.as_view(), name='regies_liste'),
    path('parametrage/regies/ajouter', regies.Ajouter.as_view(), name='regies_ajouter'),
    path('parametrage/regies/modifier/<int:pk>', regies.Modifier.as_view(), name='regies_modifier'),
    path('parametrage/regies/supprimer/<int:pk>', regies.Supprimer.as_view(), name='regies_supprimer'),

    # Perceptions
    path('parametrage/perceptions/liste', perceptions.Liste.as_view(), name='perceptions_liste'),
    path('parametrage/perceptions/ajouter', perceptions.Ajouter.as_view(), name='perceptions_ajouter'),
    path('parametrage/perceptions/modifier/<int:pk>', perceptions.Modifier.as_view(), name='perceptions_modifier'),
    path('parametrage/perceptions/supprimer/<int:pk>', perceptions.Supprimer.as_view(), name='perceptions_supprimer'),

    # Modèles de lots PES
    path('parametrage/modeles_pes/liste', modeles_pes.Liste.as_view(), name='modeles_pes_liste'),
    path('parametrage/modeles_pes/creer', modeles_pes.Creer.as_view(), name='modeles_pes_creer'),
    path('parametrage/modeles_pes/ajouter/<str:format>', modeles_pes.Ajouter.as_view(), name='modeles_pes_ajouter'),
    path('parametrage/modeles_pes/modifier/<int:pk>', modeles_pes.Modifier.as_view(), name='modeles_pes_modifier'),
    path('parametrage/modeles_pes/supprimer/<int:pk>', modeles_pes.Supprimer.as_view(), name='modeles_pes_supprimer'),

    # Modèles de prélèvements
    path('parametrage/modeles_prelevements/liste', modeles_prelevements.Liste.as_view(), name='modeles_prelevements_liste'),
    path('parametrage/modeles_prelevements/creer', modeles_prelevements.Creer.as_view(), name='modeles_prelevements_creer'),
    path('parametrage/modeles_prelevements/ajouter/<str:format>', modeles_prelevements.Ajouter.as_view(), name='modeles_prelevements_ajouter'),
    path('parametrage/modeles_prelevements/modifier/<int:pk>', modeles_prelevements.Modifier.as_view(), name='modeles_prelevements_modifier'),
    path('parametrage/modeles_prelevements/supprimer/<int:pk>', modeles_prelevements.Supprimer.as_view(), name='modeles_prelevements_supprimer'),

    # Modèles d'aide
    path('parametrage/modeles_aides/liste', modeles_aides.Liste.as_view(), name='modeles_aides_liste'),
    path('parametrage/modeles_aides/creer', modeles_aides.Creer.as_view(), name='modeles_aides_creer'),
    path('parametrage/modeles_aides/ajouter/<int:activite>', modeles_aides.Ajouter.as_view(), name='modeles_aides_ajouter'),
    path('parametrage/modeles_aides/modifier/<int:pk>', modeles_aides.Modifier.as_view(), name='modeles_aides_modifier'),
    path('parametrage/modeles_aides/supprimer/<int:pk>', modeles_aides.Supprimer.as_view(), name='modeles_aides_supprimer'),

    # Types de pièces
    path('parametrage/types_pieces/liste', types_pieces.Liste.as_view(), name='types_pieces_liste'),
    path('parametrage/types_pieces/ajouter', types_pieces.Ajouter.as_view(), name='types_pieces_ajouter'),
    path('parametrage/types_pieces/modifier/<int:pk>', types_pieces.Modifier.as_view(), name='types_pieces_modifier'),
    path('parametrage/types_pieces/supprimer/<int:pk>', types_pieces.Supprimer.as_view(), name='types_pieces_supprimer'),

    # Régimes
    path('parametrage/regimes/liste', regimes.Liste.as_view(), name='regimes_liste'),
    path('parametrage/regimes/ajouter', regimes.Ajouter.as_view(), name='regimes_ajouter'),
    path('parametrage/regimes/modifier/<int:pk>', regimes.Modifier.as_view(), name='regimes_modifier'),
    path('parametrage/regimes/supprimer/<int:pk>', regimes.Supprimer.as_view(), name='regimes_supprimer'),

    # Caisses
    path('parametrage/caisses/liste', caisses.Liste.as_view(), name='caisses_liste'),
    path('parametrage/caisses/ajouter', caisses.Ajouter.as_view(), name='caisses_ajouter'),
    path('parametrage/caisses/modifier/<int:pk>', caisses.Modifier.as_view(), name='caisses_modifier'),
    path('parametrage/caisses/supprimer/<int:pk>', caisses.Supprimer.as_view(), name='caisses_supprimer'),

    # Types de quotients
    path('parametrage/types_quotients/liste', types_quotients.Liste.as_view(), name='types_quotients_liste'),
    path('parametrage/types_quotients/ajouter', types_quotients.Ajouter.as_view(), name='types_quotients_ajouter'),
    path('parametrage/types_quotients/modifier/<int:pk>', types_quotients.Modifier.as_view(), name='types_quotients_modifier'),
    path('parametrage/types_quotients/supprimer/<int:pk>', types_quotients.Supprimer.as_view(), name='types_quotients_supprimer'),

    # Catégorie professionnelles
    path('parametrage/categories_travail/liste', categories_travail.Liste.as_view(), name='categories_travail_liste'),
    path('parametrage/categories_travail/ajouter', categories_travail.Ajouter.as_view(), name='categories_travail_ajouter'),
    path('parametrage/categories_travail/modifier/<int:pk>', categories_travail.Modifier.as_view(), name='categories_travail_modifier'),
    path('parametrage/categories_travail/supprimer/<int:pk>', categories_travail.Supprimer.as_view(), name='categories_travail_supprimer'),

    # Secteurs géographiques
    path('parametrage/secteurs/liste', secteurs.Liste.as_view(), name='secteurs_liste'),
    path('parametrage/secteurs/ajouter', secteurs.Ajouter.as_view(), name='secteurs_ajouter'),
    path('parametrage/secteurs/modifier/<int:pk>', secteurs.Modifier.as_view(), name='secteurs_modifier'),
    path('parametrage/secteurs/supprimer/<int:pk>', secteurs.Supprimer.as_view(), name='secteurs_supprimer'),

    # Types de sieste
    path('parametrage/types_sieste/liste', types_sieste.Liste.as_view(), name='types_sieste_liste'),
    path('parametrage/types_sieste/ajouter', types_sieste.Ajouter.as_view(), name='types_sieste_ajouter'),
    path('parametrage/types_sieste/modifier/<int:pk>', types_sieste.Modifier.as_view(), name='types_sieste_modifier'),
    path('parametrage/types_sieste/supprimer/<int:pk>', types_sieste.Supprimer.as_view(), name='types_sieste_supprimer'),

    # Types de régimes alimentaires
    path('parametrage/types_regimes_alimentaires/liste', types_regimes_alimentaires.Liste.as_view(), name='types_regimes_alimentaires_liste'),
    path('parametrage/types_regimes_alimentaires/ajouter', types_regimes_alimentaires.Ajouter.as_view(), name='types_regimes_alimentaires_ajouter'),
    path('parametrage/types_regimes_alimentaires/modifier/<int:pk>', types_regimes_alimentaires.Modifier.as_view(), name='types_regimes_alimentaires_modifier'),
    path('parametrage/types_regimes_alimentaires/supprimer/<int:pk>', types_regimes_alimentaires.Supprimer.as_view(), name='types_regimes_alimentaires_supprimer'),

    # Catégories informations
    path('parametrage/categories_informations/liste', categories_informations.Liste.as_view(), name='categories_informations_liste'),
    path('parametrage/categories_informations/ajouter', categories_informations.Ajouter.as_view(), name='categories_informations_ajouter'),
    path('parametrage/categories_informations/modifier/<int:pk>', categories_informations.Modifier.as_view(), name='categories_informations_modifier'),
    path('parametrage/categories_informations/supprimer/<int:pk>', categories_informations.Supprimer.as_view(), name='categories_informations_supprimer'),

    # Types de maladies
    path('parametrage/types_maladies/liste', types_maladies.Liste.as_view(), name='types_maladies_liste'),
    path('parametrage/types_maladies/ajouter', types_maladies.Ajouter.as_view(), name='types_maladies_ajouter'),
    path('parametrage/types_maladies/modifier/<int:pk>', types_maladies.Modifier.as_view(), name='types_maladies_modifier'),
    path('parametrage/types_maladies/supprimer/<int:pk>', types_maladies.Supprimer.as_view(), name='types_maladies_supprimer'),

    # Types de vaccins
    path('parametrage/types_vaccins/liste', types_vaccins.Liste.as_view(), name='types_vaccins_liste'),
    path('parametrage/types_vaccins/ajouter', types_vaccins.Ajouter.as_view(), name='types_vaccins_ajouter'),
    path('parametrage/types_vaccins/modifier/<int:pk>', types_vaccins.Modifier.as_view(), name='types_vaccins_modifier'),
    path('parametrage/types_vaccins/supprimer/<int:pk>', types_vaccins.Supprimer.as_view(), name='types_vaccins_supprimer'),

    # Médecins
    path('parametrage/medecins/liste', medecins.Liste.as_view(), name='medecins_liste'),
    path('parametrage/medecins/ajouter', medecins.Ajouter.as_view(), name='medecins_ajouter'),
    path('parametrage/medecins/modifier/<int:pk>', medecins.Modifier.as_view(),name='medecins_modifier'),
    path('parametrage/medecins/supprimer/<int:pk>', medecins.Supprimer.as_view(),name='medecins_supprimer'),

    # Niveaux scolaires
    path('parametrage/niveaux_scolaires/liste', niveaux_scolaires.Liste.as_view(), name='niveaux_scolaires_liste'),
    path('parametrage/niveaux_scolaires/ajouter', niveaux_scolaires.Ajouter.as_view(), name='niveaux_scolaires_ajouter'),
    path('parametrage/niveaux_scolaires/modifier/<int:pk>', niveaux_scolaires.Modifier.as_view(), name='niveaux_scolaires_modifier'),
    path('parametrage/niveaux_scolaires/supprimer/<int:pk>', niveaux_scolaires.Supprimer.as_view(), name='niveaux_scolaires_supprimer'),

    # Ecoles
    path('parametrage/ecoles/liste', ecoles.Liste.as_view(), name='ecoles_liste'),
    path('parametrage/ecoles/ajouter', ecoles.Ajouter.as_view(), name='ecoles_ajouter'),
    path('parametrage/ecoles/modifier/<int:pk>', ecoles.Modifier.as_view(), name='ecoles_modifier'),
    path('parametrage/ecoles/supprimer/<int:pk>', ecoles.Supprimer.as_view(), name='ecoles_supprimer'),

    # Classes
    path('parametrage/classes/liste', classes.Liste.as_view(), name='classes_liste'),
    path('parametrage/classes/ajouter', classes.Ajouter.as_view(), name='classes_ajouter'),
    path('parametrage/classes/modifier/<int:pk>', classes.Modifier.as_view(), name='classes_modifier'),
    path('parametrage/classes/supprimer/<int:pk>', classes.Supprimer.as_view(), name='classes_supprimer'),
    path('parametrage/classes/supprimer_plusieurs/<str:listepk>', classes.Supprimer_plusieurs.as_view(), name='classes_supprimer_plusieurs'),
    path('parametrage/classes/dupliquer', secure_ajax(classes.Dupliquer), name='ajax_classes_dupliquer'),

    # Restaurateurs
    path('parametrage/restaurateurs/liste', restaurateurs.Liste.as_view(), name='restaurateurs_liste'),
    path('parametrage/restaurateurs/ajouter', restaurateurs.Ajouter.as_view(), name='restaurateurs_ajouter'),
    path('parametrage/restaurateurs/modifier/<int:pk>', restaurateurs.Modifier.as_view(), name='restaurateurs_modifier'),
    path('parametrage/restaurateurs/supprimer/<int:pk>', restaurateurs.Supprimer.as_view(), name='restaurateurs_supprimer'),

    # Catégories de menus
    path('parametrage/menus_categories/liste', menus_categories.Liste.as_view(), name='menus_categories_liste'),
    path('parametrage/menus_categories/ajouter', menus_categories.Ajouter.as_view(), name='menus_categories_ajouter'),
    path('parametrage/menus_categories/modifier/<int:pk>', menus_categories.Modifier.as_view(), name='menus_categories_modifier'),
    path('parametrage/menus_categories/supprimer/<int:pk>', menus_categories.Supprimer.as_view(), name='menus_categories_supprimer'),

    # Légendes de menus
    path('parametrage/menus_legendes/liste', menus_legendes.Liste.as_view(), name='menus_legendes_liste'),
    path('parametrage/menus_legendes/ajouter', menus_legendes.Ajouter.as_view(), name='menus_legendes_ajouter'),
    path('parametrage/menus_legendes/modifier/<int:pk>', menus_legendes.Modifier.as_view(), name='menus_legendes_modifier'),
    path('parametrage/menus_legendes/supprimer/<int:pk>', menus_legendes.Supprimer.as_view(), name='menus_legendes_supprimer'),

    # Modèles de commandes
    path('parametrage/modeles_commandes/liste', modeles_commandes.Liste.as_view(), name='modeles_commandes_liste'),
    path('parametrage/modeles_commandes/ajouter', modeles_commandes.Ajouter.as_view(), name='modeles_commandes_ajouter'),
    path('parametrage/modeles_commandes/modifier/<int:pk>', modeles_commandes.Modifier.as_view(), name='modeles_commandes_modifier'),
    path('parametrage/modeles_commandes/supprimer/<int:pk>', modeles_commandes.Supprimer.as_view(), name='modeles_commandes_supprimer'),

    # Colonnes des modèles de commandes
    path('parametrage/modeles_commandes_colonnes/liste', modeles_commandes_colonnes.Liste.as_view(), name='modeles_commandes_colonnes_liste'),
    path('parametrage/modeles_commandes_colonnes/liste/<int:categorie>', modeles_commandes_colonnes.Liste.as_view(), name='modeles_commandes_colonnes_liste'),
    path('parametrage/modeles_commandes_colonnes/ajouter/<int:categorie>', modeles_commandes_colonnes.Ajouter.as_view(), name='modeles_commandes_colonnes_ajouter'),
    path('parametrage/modeles_commandes_colonnes/modifier/<int:categorie>/<int:pk>', modeles_commandes_colonnes.Modifier.as_view(), name='modeles_commandes_colonnes_modifier'),
    path('parametrage/modeles_commandes_colonnes/supprimer/<int:categorie>/<int:pk>', modeles_commandes_colonnes.Supprimer.as_view(), name='modeles_commandes_colonnes_supprimer'),

    # Catégories de notes
    path('parametrage/notes_categories/liste', notes_categories.Liste.as_view(), name='notes_categories_liste'),
    path('parametrage/notes_categories/ajouter', notes_categories.Ajouter.as_view(), name='notes_categories_ajouter'),
    path('parametrage/notes_categories/modifier/<int:pk>', notes_categories.Modifier.as_view(), name='notes_categories_modifier'),
    path('parametrage/notes_categories/supprimer/<int:pk>', notes_categories.Supprimer.as_view(), name='notes_categories_supprimer'),

    # Tâches récurrentes
    path('parametrage/taches_recurrentes/liste', taches_recurrentes.Liste.as_view(), name='taches_recurrentes_liste'),
    path('parametrage/taches_recurrentes/ajouter', taches_recurrentes.Ajouter.as_view(), name='taches_recurrentes_ajouter'),
    path('parametrage/taches_recurrentes/modifier/<int:pk>', taches_recurrentes.Modifier.as_view(), name='taches_recurrentes_modifier'),
    path('parametrage/taches_recurrentes/supprimer/<int:pk>', taches_recurrentes.Supprimer.as_view(), name='taches_recurrentes_supprimer'),

    # Listes de diffusion
    path('parametrage/listes_diffusion/liste', listes_diffusion.Liste.as_view(), name='listes_diffusion_liste'),
    path('parametrage/listes_diffusion/ajouter', listes_diffusion.Ajouter.as_view(), name='listes_diffusion_ajouter'),
    path('parametrage/listes_diffusion/modifier/<int:pk>', listes_diffusion.Modifier.as_view(), name='listes_diffusion_modifier'),
    path('parametrage/listes_diffusion/supprimer/<int:pk>', listes_diffusion.Supprimer.as_view(), name='listes_diffusion_supprimer'),

    # Périodes de vacances
    path('parametrage/vacances/liste', vacances.Liste.as_view(), name='vacances_liste'),
    path('parametrage/vacances/ajouter', vacances.Ajouter.as_view(), name='vacances_ajouter'),
    path('parametrage/vacances/modifier/<int:pk>', vacances.Modifier.as_view(), name='vacances_modifier'),
    path('parametrage/vacances/supprimer/<int:pk>', vacances.Supprimer.as_view(), name='vacances_supprimer'),

    path('parametrage/vacances_importation/<str:zone>', vacances_importation.View.as_view(), name='vacances_importation'),

    # Jours fériés fixes
    path('parametrage/feries_fixes/liste', feries_fixes.Liste.as_view(), name='feries_fixes_liste'),
    path('parametrage/feries_fixes/ajouter', feries_fixes.Ajouter.as_view(), name='feries_fixes_ajouter'),
    path('parametrage/feries_fixes/modifier/<int:pk>', feries_fixes.Modifier.as_view(), name='feries_fixes_modifier'),
    path('parametrage/feries_fixes/supprimer/<int:pk>', feries_fixes.Supprimer.as_view(), name='feries_fixes_supprimer'),

    # Jours fériés variables
    path('parametrage/feries_variables/liste', feries_variables.Liste.as_view(), name='feries_variables_liste'),
    path('parametrage/feries_variables/ajouter', feries_variables.Ajouter.as_view(), name='feries_variables_ajouter'),
    path('parametrage/feries_variables/modifier/<int:pk>', feries_variables.Modifier.as_view(), name='feries_variables_modifier'),
    path('parametrage/feries_variables/supprimer/<int:pk>', feries_variables.Supprimer.as_view(), name='feries_variables_supprimer'),

    path('parametrage/feries_generation', feries_generation.View.as_view(), name='feries_generation'),

    # Modèles de documents
    path('parametrage/modeles_documents/liste', modeles_documents.Liste.as_view(), name='modeles_documents_liste'),
    path('parametrage/modeles_documents/liste/<str:categorie>', modeles_documents.Liste.as_view(), name='modeles_documents_liste'),
    path('parametrage/modeles_documents/ajouter/<str:nom>/<str:categorie>', modeles_documents.Ajouter.as_view(), name='modeles_documents_ajouter'),
    path('parametrage/modeles_documents/modifier/<str:categorie>/<int:pk>', modeles_documents.Modifier.as_view(), name='modeles_documents_modifier'),
    path('parametrage/modeles_documents/supprimer/<str:categorie>/<int:pk>', modeles_documents.Supprimer.as_view(), name='modeles_documents_supprimer'),
    path('parametrage/modeles_documents/dupliquer/<str:categorie>/<int:pk>', modeles_documents.Dupliquer.as_view(), name='modeles_documents_dupliquer'),
    path('parametrage/modeles_documents/creer/<str:categorie>', modeles_documents.Creer.as_view(), name='modeles_documents_creer'),

    # Modèles d'impressions
    path('parametrage/modeles_impressions/liste', modeles_impressions.Liste.as_view(), name='modeles_impressions_liste'),
    path('parametrage/modeles_impressions/liste/<str:categorie>', modeles_impressions.Liste.as_view(), name='modeles_impressions_liste'),
    path('parametrage/modeles_impressions/ajouter/<str:categorie>', modeles_impressions.Ajouter.as_view(), name='modeles_impressions_ajouter'),
    path('parametrage/modeles_impressions/modifier/<str:categorie>/<int:pk>', modeles_impressions.Modifier.as_view(), name='modeles_impressions_modifier'),
    path('parametrage/modeles_impressions/supprimer/<str:categorie>/<int:pk>', modeles_impressions.Supprimer.as_view(), name='modeles_impressions_supprimer'),
    path('parametrage/modeles_impressions/dupliquer/<str:categorie>/<int:pk>', modeles_impressions.Dupliquer.as_view(), name='modeles_impressions_dupliquer'),

    # Modèles de documents Word
    path('parametrage/modeles_word/liste', modeles_word.Liste.as_view(), name='modeles_word_liste'),
    path('parametrage/modeles_word/liste/<str:categorie>', modeles_word.Liste.as_view(), name='modeles_word_liste'),
    path('parametrage/modeles_word/ajouter/<str:categorie>', modeles_word.Ajouter.as_view(), name='modeles_word_ajouter'),
    path('parametrage/modeles_word/modifier/<str:categorie>/<int:pk>', modeles_word.Modifier.as_view(), name='modeles_word_modifier'),
    path('parametrage/modeles_word/supprimer/<str:categorie>/<int:pk>', modeles_word.Supprimer.as_view(), name='modeles_word_supprimer'),

    # Modèles d'emails
    path('parametrage/modeles_emails/liste', modeles_emails.Liste.as_view(), name='modeles_emails_liste'),
    path('parametrage/modeles_emails/liste/<str:categorie>', modeles_emails.Liste.as_view(), name='modeles_emails_liste'),
    path('parametrage/modeles_emails/ajouter/<str:categorie>', modeles_emails.Ajouter.as_view(), name='modeles_emails_ajouter'),
    path('parametrage/modeles_emails/modifier/<str:categorie>/<int:pk>', modeles_emails.Modifier.as_view(), name='modeles_emails_modifier'),
    path('parametrage/modeles_emails/supprimer/<str:categorie>/<int:pk>', modeles_emails.Supprimer.as_view(), name='modeles_emails_supprimer'),
    path('parametrage/modeles_emails/dupliquer/<str:categorie>/<int:pk>', modeles_emails.Dupliquer.as_view(), name='modeles_emails_dupliquer'),

    # Modèles de SMS
    path('parametrage/modeles_sms/liste', modeles_sms.Liste.as_view(), name='modeles_sms_liste'),
    path('parametrage/modeles_sms/liste/<str:categorie>', modeles_sms.Liste.as_view(), name='modeles_sms_liste'),
    path('parametrage/modeles_sms/ajouter/<str:categorie>', modeles_sms.Ajouter.as_view(), name='modeles_sms_ajouter'),
    path('parametrage/modeles_sms/modifier/<str:categorie>/<int:pk>', modeles_sms.Modifier.as_view(), name='modeles_sms_modifier'),
    path('parametrage/modeles_sms/supprimer/<str:categorie>/<int:pk>', modeles_sms.Supprimer.as_view(), name='modeles_sms_supprimer'),
    path('parametrage/modeles_sms/dupliquer/<str:categorie>/<int:pk>', modeles_sms.Dupliquer.as_view(), name='modeles_sms_dupliquer'),

    # Modèles de lettres de rappel
    path('parametrage/modeles_rappels/liste', modeles_rappels.Liste.as_view(), name='modeles_rappels_liste'),
    path('parametrage/modeles_rappels/ajouter', modeles_rappels.Ajouter.as_view(), name='modeles_rappels_ajouter'),
    path('parametrage/modeles_rappels/modifier/<int:pk>', modeles_rappels.Modifier.as_view(), name='modeles_rappels_modifier'),
    path('parametrage/modeles_rappels/supprimer/<int:pk>', modeles_rappels.Supprimer.as_view(), name='modeles_rappels_supprimer'),
    path('parametrage/modeles_rappels/dupliquer/<int:pk>', modeles_rappels.Dupliquer.as_view(), name='modeles_rappels_dupliquer'),

    # Modèles de prestations
    path('parametrage/modeles_prestations/liste', modeles_prestations.Liste.as_view(), name='modeles_prestations_liste'),
    path('parametrage/modeles_prestations/ajouter', modeles_prestations.Ajouter.as_view(), name='modeles_prestations_ajouter'),
    path('parametrage/modeles_prestations/modifier/<int:pk>', modeles_prestations.Modifier.as_view(), name='modeles_prestations_modifier'),
    path('parametrage/modeles_prestations/supprimer/<int:pk>', modeles_prestations.Supprimer.as_view(), name='modeles_prestations_supprimer'),

    # Questions des questionnaires
    path('parametrage/questions/liste', questionnaires.Liste.as_view(), name='questions_liste'),
    path('parametrage/questions/liste/<str:categorie>', questionnaires.Liste.as_view(), name='questions_liste'),
    path('parametrage/questions/ajouter/<str:categorie>', questionnaires.Ajouter.as_view(), name='questions_ajouter'),
    path('parametrage/questions/modifier/<str:categorie>/<int:pk>', questionnaires.Modifier.as_view(), name='questions_modifier'),
    path('parametrage/questions/supprimer/<str:categorie>/<int:pk>', questionnaires.Supprimer.as_view(), name='questions_supprimer'),

    # Adresses mail
    path('parametrage/adresses_mail/liste', adresses_mail.Liste.as_view(), name='adresses_mail_liste'),
    path('parametrage/adresses_mail/ajouter', adresses_mail.Ajouter.as_view(), name='adresses_mail_ajouter'),
    path('parametrage/adresses_mail/modifier/<int:pk>', adresses_mail.Modifier.as_view(), name='adresses_mail_modifier'),
    path('parametrage/adresses_mail/supprimer/<int:pk>', adresses_mail.Supprimer.as_view(), name='adresses_mail_supprimer'),

    # Signatures d'emails
    path('parametrage/signatures_emails/liste', signatures_emails.Liste.as_view(), name='signatures_emails_liste'),
    path('parametrage/signatures_emails/ajouter', signatures_emails.Ajouter.as_view(), name='signatures_emails_ajouter'),
    path('parametrage/signatures_emails/modifier/<int:pk>', signatures_emails.Modifier.as_view(), name='signatures_emails_modifier'),
    path('parametrage/signatures_emails/supprimer/<int:pk>', signatures_emails.Supprimer.as_view(), name='signatures_emails_supprimer'),
    path('parametrage/signatures_emails/dupliquer/<int:pk>', signatures_emails.Dupliquer.as_view(), name='signatures_emails_dupliquer'),

    # Configurations SMS
    path('parametrage/configurations_sms/liste', configurations_sms.Liste.as_view(), name='configurations_sms_liste'),
    path('parametrage/configurations_sms/ajouter', configurations_sms.Ajouter.as_view(), name='configurations_sms_ajouter'),
    path('parametrage/configurations_sms/modifier/<int:pk>', configurations_sms.Modifier.as_view(), name='configurations_sms_modifier'),
    path('parametrage/configurations_sms/supprimer/<int:pk>', configurations_sms.Supprimer.as_view(), name='configurations_sms_supprimer'),

    # Assureurs
    path('parametrage/assureurs/liste', assureurs.Liste.as_view(), name='assureurs_liste'),
    path('parametrage/assureurs/ajouter', assureurs.Ajouter.as_view(), name='assureurs_ajouter'),
    path('parametrage/assureurs/modifier/<int:pk>', assureurs.Modifier.as_view(), name='assureurs_modifier'),
    path('parametrage/assureurs/supprimer/<int:pk>', assureurs.Supprimer.as_view(), name='assureurs_supprimer'),

    # Catégorie professionnelles
    path('parametrage/categories_compte_internet/liste', categories_compte_internet.Liste.as_view(), name='categories_compte_internet_liste'),
    path('parametrage/categories_compte_internet/ajouter', categories_compte_internet.Ajouter.as_view(), name='categories_compte_internet_ajouter'),
    path('parametrage/categories_compte_internet/modifier/<int:pk>', categories_compte_internet.Modifier.as_view(), name='categories_compte_internet_modifier'),
    path('parametrage/categories_compte_internet/supprimer/<int:pk>', categories_compte_internet.Supprimer.as_view(), name='categories_compte_internet_supprimer'),

    # Portail
    path('parametrage/portail_parametres/modifier', portail_parametres.Modifier.as_view(), name='portail_parametres_modifier'),
    path('parametrage/portail_parametres_renseignements/modifier', portail_parametres_renseignements.Modifier.as_view(), name='portail_parametres_renseignements_modifier'),

    # Types de consentements
    path('parametrage/types_consentements/liste', types_consentements.Liste.as_view(), name='types_consentements_liste'),
    path('parametrage/types_consentements/ajouter', types_consentements.Ajouter.as_view(), name='types_consentements_ajouter'),
    path('parametrage/types_consentements/modifier/<int:pk>', types_consentements.Modifier.as_view(), name='types_consentements_modifier'),
    path('parametrage/types_consentements/supprimer/<int:pk>', types_consentements.Supprimer.as_view(), name='types_consentements_supprimer'),

    # Unités de consentements
    path('parametrage/unites_consentements/liste', unites_consentements.Liste.as_view(), name='unites_consentements_liste'),
    path('parametrage/unites_consentements/liste/<int:categorie>', unites_consentements.Liste.as_view(), name='unites_consentements_liste'),
    path('parametrage/unites_consentements/ajouter/<int:categorie>', unites_consentements.Ajouter.as_view(), name='unites_consentements_ajouter'),
    path('parametrage/unites_consentements/modifier/<int:categorie>/<int:pk>', unites_consentements.Modifier.as_view(), name='unites_consentements_modifier'),
    path('parametrage/unites_consentements/supprimer/<int:categorie>/<int:pk>', unites_consentements.Supprimer.as_view(), name='unites_consentements_supprimer'),

    # Articles
    path('parametrage/articles/liste', articles.Liste.as_view(), name='articles_liste'),
    path('parametrage/articles/ajouter', articles.Ajouter.as_view(), name='articles_ajouter'),
    path('parametrage/articles/modifier/<int:pk>', articles.Modifier.as_view(), name='articles_modifier'),
    path('parametrage/articles/supprimer/<int:pk>', articles.Supprimer.as_view(), name='articles_supprimer'),
    path('parametrage/articles/dupliquer/<int:pk>', articles.Dupliquer.as_view(), name='articles_dupliquer'),
    path('parametrage/articles/apercu/<int:pk>', articles.Apercu.as_view(), name='articles_apercu'),

    # Images d'articles
    path('parametrage/images_articles/liste', images_articles.Liste.as_view(), name='images_articles_liste'),
    path('parametrage/images_articles/ajouter', images_articles.Ajouter.as_view(), name='images_articles_ajouter'),
    path('parametrage/images_articles/modifier/<int:pk>', images_articles.Modifier.as_view(), name='images_articles_modifier'),
    path('parametrage/images_articles/supprimer/<int:pk>', images_articles.Supprimer.as_view(), name='images_articles_supprimer'),

    # Albums photos
    path('parametrage/albums/liste', albums.Liste.as_view(), name='albums_liste'),
    path('parametrage/albums/ajouter', albums.Ajouter.as_view(), name='albums_ajouter'),
    path('parametrage/albums/modifier/<int:pk>', albums.Modifier.as_view(), name='albums_modifier'),
    path('parametrage/albums/supprimer/<int:pk>', albums.Supprimer.as_view(), name='albums_supprimer'),
    path('parametrage/albums/consulter/<int:pk>', albums.Consulter.as_view(), name='albums_consulter'),
    path('parametrage/albums/photos/modifier/<int:idalbum>/<int:pk>', albums.Modifier_photo.as_view(), name='albums_modifier_photo'),
    path('parametrage/albums/photos/supprimer/<int:idalbum>/<int:pk>', albums.Supprimer_photo.as_view(), name='albums_supprimer_photo'),
    path('parametrage/albums/photos/supprimer_plusieurs/<int:idalbum>/<str:listepk>', albums.Supprimer_plusieurs_photos.as_view(), name='albums_supprimer_plusieurs_photos'),

    # Sondages
    path('parametrage/sondages/liste', sondages.Liste.as_view(), name='sondages_liste'),
    path('parametrage/sondages/ajouter', sondages.Ajouter.as_view(), name='sondages_ajouter'),
    path('parametrage/sondages/modifier/<int:pk>', sondages.Modifier.as_view(), name='sondages_modifier'),
    path('parametrage/sondages/supprimer/<int:pk>', sondages.Supprimer.as_view(), name='sondages_supprimer'),
    path('parametrage/sondages/consulter/<int:pk>', sondages.Consulter.as_view(), name='sondages_consulter'),

    # Images de fond
    path('parametrage/images_fond/liste', images_fond.Liste.as_view(), name='images_fond_liste'),
    path('parametrage/images_fond/ajouter', images_fond.Ajouter.as_view(), name='images_fond_ajouter'),
    path('parametrage/images_fond/modifier/<int:pk>', images_fond.Modifier.as_view(), name='images_fond_modifier'),
    path('parametrage/images_fond/supprimer/<int:pk>', images_fond.Supprimer.as_view(), name='images_fond_supprimer'),

    # Articles
    path('parametrage/portail_documents/liste', portail_documents.Liste.as_view(), name='portail_documents_liste'),
    path('parametrage/portail_documents/ajouter', portail_documents.Ajouter.as_view(), name='portail_documents_ajouter'),
    path('parametrage/portail_documents/modifier/<int:pk>', portail_documents.Modifier.as_view(), name='portail_documents_modifier'),
    path('parametrage/portail_documents/supprimer/<int:pk>', portail_documents.Supprimer.as_view(), name='portail_documents_supprimer'),

    # Catégories de produits
    path('parametrage/categories_produits/liste', categories_produits.Liste.as_view(), name='categories_produits_liste'),
    path('parametrage/categories_produits/ajouter', categories_produits.Ajouter.as_view(), name='categories_produits_ajouter'),
    path('parametrage/categories_produits/modifier/<int:pk>', categories_produits.Modifier.as_view(), name='categories_produits_modifier'),
    path('parametrage/categories_produits/supprimer/<int:pk>', categories_produits.Supprimer.as_view(), name='categories_produits_supprimer'),

    # Produits
    path('parametrage/produits/liste', produits.Liste.as_view(), name='produits_liste'),
    path('parametrage/produits/ajouter', produits.Ajouter.as_view(), name='produits_ajouter'),
    path('parametrage/produits/modifier/<int:pk>', produits.Modifier.as_view(), name='produits_modifier'),
    path('parametrage/produits/supprimer/<int:pk>', produits.Supprimer.as_view(), name='produits_supprimer'),

    path('parametrage/produits/tarifs_produits/liste/<int:idproduit>', produits_tarifs.Liste.as_view(), name='produits_tarifs_liste'),
    path('parametrage/produits/tarifs_produits/ajouter/<int:idproduit>', produits_tarifs.Ajouter.as_view(), name='produits_tarifs_ajouter'),
    path('parametrage/produits/tarifs_produits/modifier/<int:idproduit>/<int:pk>', produits_tarifs.Modifier.as_view(), name='produits_tarifs_modifier'),
    path('parametrage/produits/tarifs_produits/supprimer/<int:idproduit>/<int:pk>', produits_tarifs.Supprimer.as_view(), name='produits_tarifs_supprimer'),

    # Types de qualifications collaborateurs
    path('parametrage/types_qualifications_collaborateurs/liste', types_qualifications_collaborateurs.Liste.as_view(), name='types_qualifications_collaborateurs_liste'),
    path('parametrage/types_qualifications_collaborateurs/ajouter', types_qualifications_collaborateurs.Ajouter.as_view(), name='types_qualifications_collaborateurs_ajouter'),
    path('parametrage/types_qualifications_collaborateurs/modifier/<int:pk>', types_qualifications_collaborateurs.Modifier.as_view(), name='types_qualifications_collaborateurs_modifier'),
    path('parametrage/types_qualifications_collaborateurs/supprimer/<int:pk>', types_qualifications_collaborateurs.Supprimer.as_view(), name='types_qualifications_collaborateurs_supprimer'),

    # Types de pièces collaborateurs
    path('parametrage/types_pieces_collaborateurs/liste', types_pieces_collaborateurs.Liste.as_view(), name='types_pieces_collaborateurs_liste'),
    path('parametrage/types_pieces_collaborateurs/ajouter', types_pieces_collaborateurs.Ajouter.as_view(), name='types_pieces_collaborateurs_ajouter'),
    path('parametrage/types_pieces_collaborateurs/modifier/<int:pk>', types_pieces_collaborateurs.Modifier.as_view(), name='types_pieces_collaborateurs_modifier'),
    path('parametrage/types_pieces_collaborateurs/supprimer/<int:pk>', types_pieces_collaborateurs.Supprimer.as_view(), name='types_pieces_collaborateurs_supprimer'),

    # Types d'évènements collaborateurs
    path('parametrage/types_evenements_collaborateurs/liste', types_evenements_collaborateurs.Liste.as_view(), name='types_evenements_collaborateurs_liste'),
    path('parametrage/types_evenements_collaborateurs/ajouter', types_evenements_collaborateurs.Ajouter.as_view(), name='types_evenements_collaborateurs_ajouter'),
    path('parametrage/types_evenements_collaborateurs/modifier/<int:pk>', types_evenements_collaborateurs.Modifier.as_view(), name='types_evenements_collaborateurs_modifier'),
    path('parametrage/types_evenements_collaborateurs/supprimer/<int:pk>', types_evenements_collaborateurs.Supprimer.as_view(), name='types_evenements_collaborateurs_supprimer'),

    # Types de postes collaborateurs
    path('parametrage/types_postes_collaborateurs/liste', types_postes_collaborateurs.Liste.as_view(), name='types_postes_collaborateurs_liste'),
    path('parametrage/types_postes_collaborateurs/ajouter', types_postes_collaborateurs.Ajouter.as_view(), name='types_postes_collaborateurs_ajouter'),
    path('parametrage/types_postes_collaborateurs/modifier/<int:pk>', types_postes_collaborateurs.Modifier.as_view(), name='types_postes_collaborateurs_modifier'),
    path('parametrage/types_postes_collaborateurs/supprimer/<int:pk>', types_postes_collaborateurs.Supprimer.as_view(), name='types_postes_collaborateurs_supprimer'),

    # Modèles de plannings collaborateurs
    path('parametrage/modeles_plannings_collaborateurs/liste', modeles_plannings_collaborateurs.Liste.as_view(), name='modeles_plannings_collaborateurs_liste'),
    path('parametrage/modeles_plannings_collaborateurs/ajouter', modeles_plannings_collaborateurs.Ajouter.as_view(), name='modeles_plannings_collaborateurs_ajouter'),
    path('parametrage/modeles_plannings_collaborateurs/modifier/<int:pk>', modeles_plannings_collaborateurs.Modifier.as_view(), name='modeles_plannings_collaborateurs_modifier'),
    path('parametrage/modeles_plannings_collaborateurs/supprimer/<int:pk>', modeles_plannings_collaborateurs.Supprimer.as_view(), name='modeles_plannings_collaborateurs_supprimer'),

    # Groupes de collaborateurs
    path('parametrage/groupes_collaborateurs/liste', groupes_collaborateurs.Liste.as_view(), name='groupes_collaborateurs_liste'),
    path('parametrage/groupes_collaborateurs/ajouter', groupes_collaborateurs.Ajouter.as_view(), name='groupes_collaborateurs_ajouter'),
    path('parametrage/groupes_collaborateurs/modifier/<int:pk>', groupes_collaborateurs.Modifier.as_view(), name='groupes_collaborateurs_modifier'),
    path('parametrage/groupes_collaborateurs/supprimer/<int:pk>', groupes_collaborateurs.Supprimer.as_view(), name='groupes_collaborateurs_supprimer'),

    # Transports
    path('parametrage/transports', transports.View.as_view(), name='parametrage_transports'),

    # Compagnies
    path('parametrage/transports/compagnies/liste/<str:categorie>', compagnies.Liste.as_view(), name='compagnies_liste'),
    path('parametrage/transports/compagnies/ajouter/<str:categorie>', compagnies.Ajouter.as_view(), name='compagnies_ajouter'),
    path('parametrage/transports/compagnies/modifier/<str:categorie>/<int:pk>', compagnies.Modifier.as_view(), name='compagnies_modifier'),
    path('parametrage/transports/compagnies/supprimer/<str:categorie>/<int:pk>', compagnies.Supprimer.as_view(), name='compagnies_supprimer'),

    # Lignes
    path('parametrage/transports/lignes/liste/<str:categorie>', lignes.Liste.as_view(), name='lignes_liste'),
    path('parametrage/transports/lignes/ajouter/<str:categorie>', lignes.Ajouter.as_view(), name='lignes_ajouter'),
    path('parametrage/transports/lignes/modifier/<str:categorie>/<int:pk>', lignes.Modifier.as_view(), name='lignes_modifier'),
    path('parametrage/transports/lignes/supprimer/<str:categorie>/<int:pk>', lignes.Supprimer.as_view(), name='lignes_supprimer'),

    # Arrêts
    path('parametrage/transports/arrets/liste/<str:categorie>', arrets.Liste.as_view(), name='arrets_liste'),
    path('parametrage/transports/arrets/liste/<str:categorie>/<int:idligne>', arrets.Liste.as_view(), name='arrets_liste'),
    path('parametrage/transports/arrets/ajouter/<str:categorie>/<int:idligne>', arrets.Ajouter.as_view(), name='arrets_ajouter'),
    path('parametrage/transports/arrets/modifier/<str:categorie>/<int:idligne>/<int:pk>', arrets.Modifier.as_view(), name='arrets_modifier'),
    path('parametrage/transports/arrets/supprimer/<str:categorie>/<int:idligne>/<int:pk>', arrets.Supprimer.as_view(), name='arrets_supprimer'),

    # Lieux
    path('parametrage/transports/lieux/liste/<str:categorie>', lieux.Liste.as_view(), name='lieux_liste'),
    path('parametrage/transports/lieux/ajouter/<str:categorie>', lieux.Ajouter.as_view(), name='lieux_ajouter'),
    path('parametrage/transports/lieux/modifier/<str:categorie>/<int:pk>', lieux.Modifier.as_view(), name='lieux_modifier'),
    path('parametrage/transports/lieux/supprimer/<str:categorie>/<int:pk>', lieux.Supprimer.as_view(), name='lieux_supprimer'),

    # Catégories d'achats
    path('parametrage/achats_categories/liste', achats_categories.Liste.as_view(), name='achats_categories_liste'),
    path('parametrage/achats_categories/ajouter', achats_categories.Ajouter.as_view(), name='achats_categories_ajouter'),
    path('parametrage/achats_categories/modifier/<int:pk>', achats_categories.Modifier.as_view(), name='achats_categories_modifier'),
    path('parametrage/achats_categories/supprimer/<int:pk>', achats_categories.Supprimer.as_view(), name='achats_categories_supprimer'),

    # Fournisseurs d'achats
    path('parametrage/achats_fournisseurs/liste', achats_fournisseurs.Liste.as_view(), name='achats_fournisseurs_liste'),
    path('parametrage/achats_fournisseurs/ajouter', achats_fournisseurs.Ajouter.as_view(), name='achats_fournisseurs_ajouter'),
    path('parametrage/achats_fournisseurs/modifier/<int:pk>', achats_fournisseurs.Modifier.as_view(), name='achats_fournisseurs_modifier'),
    path('parametrage/achats_fournisseurs/supprimer/<int:pk>', achats_fournisseurs.Supprimer.as_view(), name='achats_fournisseurs_supprimer'),

    # AJAX
    path('parametrage/get_calendrier', calendrier.Get_calendrier, name='ajax_get_calendrier'),
    path('parametrage/niveaux_scolaires/deplacer_lignes', secure_ajax(niveaux_scolaires.Deplacer.as_view()), name='ajax_deplacer_lignes_niveaux_scolaires'),
    path('parametrage/menus_categories/deplacer_lignes', secure_ajax(menus_categories.Deplacer.as_view()), name='ajax_deplacer_lignes_menus_categories'),
    path('parametrage/activites/groupes/liste/deplacer_lignes', secure_ajax(activites_groupes.Deplacer.as_view()), name='ajax_deplacer_lignes_activites_groupes'),
    path('parametrage/activites/unites_conso/liste/deplacer_lignes', secure_ajax(activites_unites_conso.Deplacer.as_view()), name='ajax_deplacer_lignes_activites_unites_conso'),
    path('parametrage/activites/unites_remplissage/liste/deplacer_lignes', secure_ajax(activites_unites_remplissage.Deplacer.as_view()), name='ajax_deplacer_lignes_activites_unites_remplissage'),
    path('parametrage/get_calendrier_annuel_ouvertures', secure_ajax(activites_calendrier.Get_calendrier_annuel_ouvertures), name='ajax_get_calendrier_annuel_ouvertures'),
    path('parametrage/get_calendrier_ouvertures', secure_ajax(activites_ouvertures.Get_calendrier_ouvertures), name='ajax_get_calendrier_ouvertures'),
    path('parametrage/traitement_lot_ouvertures', secure_ajax(activites_ouvertures.Traitement_lot_ouvertures), name='ajax_traitement_lot_ouvertures'),
    path('parametrage/valider_calendrier_ouvertures', secure_ajax(activites_ouvertures.Valider_calendrier_ouvertures), name='ajax_valider_calendrier_ouvertures'),
    path('parametrage/get_fond_modele', secure_ajax(modeles_documents.Get_fond_modele), name='ajax_get_fond_modele'),
    path('parametrage/export_svg', secure_ajax(modeles_documents.Export_svg), name='ajax_export_svg'),
    path('parametrage/questions/deplacer_lignes', secure_ajax(questionnaires.Deplacer.as_view()), name='ajax_deplacer_lignes_questionnaires'),
    path('parametrage/adresses_mail/envoyer_mail_test', secure_ajax(adresses_mail.Envoyer_mail_test), name='ajax_envoyer_mail_test'),
    path('parametrage/configurations_sms/envoyer_sms_test', secure_ajax(configurations_sms.Envoyer_sms_test), name='ajax_envoyer_sms_test'),
    path('parametrage/albums/importer_photos_album', secure_ajax(albums.Importer_photos_album), name="ajax_importer_photos_album"),
    path('parametrage/modeles_plannings_collaborateurs/get_form_ligne', secure_ajax(modeles_plannings_collaborateurs.Get_form_ligne), name='ajax_modeles_plannings_collaborateurs_form_ligne'),
    path('parametrage/transports/arrets/liste/bus/deplacer_lignes', secure_ajax(arrets.Deplacer.as_view()), name='ajax_deplacer_lignes_arrets_bus'),
    path('parametrage/transports/arrets/liste/car/deplacer_lignes', secure_ajax(arrets.Deplacer.as_view()), name='ajax_deplacer_lignes_arrets_car'),
    path('parametrage/transports/arrets/liste/navette/deplacer_lignes', secure_ajax(arrets.Deplacer.as_view()), name='ajax_deplacer_lignes_arrets_navette'),
    path('parametrage/transports/arrets/liste/metro/deplacer_lignes', secure_ajax(arrets.Deplacer.as_view()), name='ajax_deplacer_lignes_arrets_metro'),
    path('parametrage/transports/arrets/liste/pedibus/deplacer_lignes', secure_ajax(arrets.Deplacer.as_view()), name='ajax_deplacer_lignes_arrets_pedibus'),
    path('parametrage/sondages/get_form_page', secure_ajax(sondages.Get_form_page), name='ajax_sondages_get_form_page'),
    path('parametrage/sondages/valid_form_page', secure_ajax(sondages.Valid_form_page), name='ajax_sondages_valid_form_page'),
    path('parametrage/sondages/supprimer_page', secure_ajax(sondages.Supprimer_page), name='ajax_sondages_supprimer_page'),
    path('parametrage/sondages/get_form_question', secure_ajax(sondages.Get_form_question), name='ajax_sondages_get_form_question'),
    path('parametrage/sondages/valid_form_question', secure_ajax(sondages.Valid_form_question), name='ajax_sondages_valid_form_question'),
    path('parametrage/sondages/supprimer_question', secure_ajax(sondages.Supprimer_question), name='ajax_sondages_supprimer_question'),
    path('parametrage/sondages/reorganiser', secure_ajax(sondages.Reorganiser), name='ajax_sondages_reorganiser'),
    path('parametrage/achats_categories/liste/deplacer_lignes', secure_ajax(achats_categories.Deplacer.as_view()), name='ajax_deplacer_lignes_achats_categories'),
    path('parametrage/modeles_commandes_colonnes/liste/deplacer_lignes', secure_ajax(modeles_commandes_colonnes.Deplacer.as_view()), name='ajax_deplacer_modeles_commandes_colonnes'),
    path('parametrage/questions/get_form_choix', secure_ajax(questionnaires.Get_form_choix), name='ajax_questionnaire_form_choix'),
    path('parametrage/activites/import_export/exporter', secure_ajax(activites_import_export.Executer), name='ajax_activites_import_export_executer'),
]
