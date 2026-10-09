# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.models import Famille
from django.views.generic.detail import DetailView
from fiche_famille.views.famille import Onglet
from core.views import menu_infos


class View(Onglet, DetailView):
    template_name = "fiche_famille/famille_outils.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['onglet_actif'] = "outils"
        idfamille = self.kwargs.get("idfamille", None)

        def Item(titre="", url_name="", icone="file-text-o", nature="a", description=""):
            return {"titre": titre, "url": reverse_lazy(url_name, kwargs={"idfamille": idfamille}), "icone": icone, "nature": nature, "description": description}

        context['description_outils'] = "Générer des documents, communiquer avec la famille et consulter son suivi."
        context['items_menu'] = [
            {"titre": "Attestations et devis", "icone": "certificate", "items": [
                Item("Générer une attestation de présence", "famille_attestations_ajouter", "file-text-o", "a", "Créer une attestation de présence sur une période."),
                Item("Liste des attestations générées", "famille_attestations_liste", "list", "l", "Retrouver et rééditer les attestations de présence."),
                Item("Générer un devis", "famille_devis_ajouter", "calculator", "a", "Chiffrer des consommations à venir pour la famille."),
                Item("Liste des devis générés", "famille_devis_liste", "list", "l", "Retrouver et rééditer les devis de la famille."),
                Item("Générer une attestation fiscale", "attestations_fiscales_generation", "certificate", "a", "Créer l'attestation pour la déclaration d'impôts."),
                Item("Liste des attestations fiscales générées", "famille_attestations_fiscales_liste", "list", "l", "Retrouver les attestations fiscales de la famille."),
            ]},
            {"titre": "Facturation", "icone": "eur", "items": [
                Item("Editer un relevé des prestations", "famille_releve_prestations", "print", "e", "Imprimer le détail des prestations et règlements."),
                Item("Générer une lettre de rappel", "rappels_generation", "bell-o", "a", "Créer une lettre de rappel des impayés de la famille."),
                Item("Liste des lettres de rappel générées", "famille_rappels_liste", "list", "l", "Retrouver les rappels envoyés à la famille."),
            ]},
            {"titre": "Communication", "icone": "envelope-o", "items": [
                Item("Envoyer un Email", "famille_emails_ajouter", "envelope-o", "e", "Écrire un email à la famille."),
                Item("Envoyer un SMS", "famille_sms_ajouter", "mobile", "e", "Écrire un SMS à la famille."),
                Item("Messagerie", "famille_messagerie_portail", "comments-o", "a", "Échanger des messages avec la famille sur le portail."),
            ]},
            {"titre": "Suivi de la famille", "icone": "eye", "items": [
                Item("Liste détaillée des consommations", "famille_liste_consommations", "list-ul", "l", "Consulter toutes les consommations de la famille."),
                Item("Liste des formulaires remplis", "famille_formulaires_liste", "check-square-o", "l", "Consulter les formulaires remplis sur le portail."),
                Item("Historique", "famille_historique", "history", "l", "Retrouver les actions effectuées sur cette fiche."),
            ]},
            {"titre": "Données de la famille", "icone": "database", "items": [
                Item("Edition des fiches de renseignements", "famille_edition_renseignements", "file-text", "e", "Imprimer les fiches de renseignements en PDF."),
                Item("Export XML", "famille_export_xml", "file-code-o", "e", "Exporter les données de la famille (demande RGPD...)."),
            ]},
        ]

        # Légende : seules les natures utilisées sur la page sont affichées
        natures_utilisees = {item["nature"] for rubrique in context['items_menu'] for item in rubrique["items"]}
        context['natures'] = {code: label for code, label in menu_infos.NATURES.items() if code in natures_utilisees}
        context['affichage_condense'] = bool(context.get("options_interface", {}).get("menu_affichage_condense", False))
        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])


