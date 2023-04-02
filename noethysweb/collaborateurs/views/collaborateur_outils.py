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

        ]
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])
