# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from core.models import Collaborateur
from collaborateurs.views.collaborateur import Onglet


class View(Onglet, DetailView):
    template_name = "collaborateurs/collaborateur_outils.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['onglet_actif'] = "outils"
        context['items_menu'] = [
            [
                {"titre": "Historique", "items": [
                    {"titre": "Historique", "url": reverse_lazy("collaborateur_historique", kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)}), "icone": "file-text-o"},
                ]},
                {"titre": "Communication", "items": [
                    {"titre": "Envoyer un Email", "url": reverse_lazy("collaborateur_emails_ajouter", kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)}), "icone": "file-text-o"},
                    {"titre": "Envoyer un SMS", "url": reverse_lazy("collaborateur_sms_ajouter", kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)}), "icone": "file-text-o"},
                ]},
            ],
            [
                {"titre": "Editions", "items": self.Get_editions()},
            ],
        ]
        return context

    def Get_editions(self):
        """ Editions accessibles à l'utilisateur, ouvertes pour ce seul collaborateur """
        from django.urls import reverse
        idcollaborateur = self.kwargs.get("idcollaborateur")
        editions = [("fiches_collaborateurs", "Imprimer la fiche"), ("releves_heures_collaborateurs", "Relevé mensuel d'heures"),
                    ("attestations_conges_collaborateurs", "Relevé de congés"), ("impression_demandes_absences_collaborateurs", "Imprimer des demandes d'absence"),
                    ("etiquettes_collaborateurs", "Etiquette ou badge")]
        return [{"titre": titre, "url": "%s?idcollaborateur=%s" % (reverse(code), idcollaborateur), "icone": "print"}
                for code, titre in editions if self.request.user.has_perm("core.%s" % code)]

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])
