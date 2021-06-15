# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.models import Famille
from django.views.generic.detail import DetailView
from fiche_famille.views.famille import Onglet
from fiche_famille.utils import utils_export_xml


class View(Onglet, DetailView):
    template_name = "fiche_famille/famille_export_xml.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Export XML"
        context['box_introduction'] = "Vous pouvez exporter ici toutes les données de la famille au format XML."
        context['onglet_actif'] = "outils"

        export = utils_export_xml.Export(famille=context['famille'])
        chemin_fichier = export.Enregistrer()
        context['chemin_fichier'] = chemin_fichier
        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])


