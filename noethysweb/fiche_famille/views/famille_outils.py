# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.models import Famille
from django.views.generic.detail import DetailView
from fiche_famille.views.famille import Onglet


class View(Onglet, DetailView):
    template_name = "fiche_famille/famille_outils.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['onglet_actif'] = "outils"
        context['items_menu'] = [
            [
                {"titre": "Attestations de présence", "items": [
                    {"titre": "Générer une attestation de présence", "url": reverse_lazy("famille_attestations_ajouter", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                    {"titre": "Liste des attestations générées", "url": reverse_lazy("famille_attestations_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                ]},
                {"titre": "Devis", "items": [
                    {"titre": "Générer un devis", "url": reverse_lazy("famille_devis_ajouter", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                    {"titre": "Liste des devis générés", "url": reverse_lazy("famille_devis_ajouter", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                ]},
                {"titre": "Lettres de rappels", "items": [
                    {"titre": "Générer une lettre de rappel", "url": reverse_lazy("rappels_generation", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                    {"titre": "Liste des lettres de rappel générées", "url": reverse_lazy("famille_rappels_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                ]},
            ],
            [
                {"titre": "Historique", "items": [
                    {"titre": "Historique", "url": reverse_lazy("famille_historique", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                    {"titre": "Export XML", "url": reverse_lazy("famille_export_xml", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                ]},
                {"titre": "Email", "items": [
                    {"titre": "Envoyer un Email", "url": reverse_lazy("famille_emails_ajouter", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                ]},
                {"titre": "Portail", "items": [
                    {"titre": "Messagerie", "url": reverse_lazy("famille_messagerie_portail", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "file-text-o"},
                ]},
            ],

        ]
        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])


