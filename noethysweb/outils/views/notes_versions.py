# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView
from django.conf import settings
from outils.utils import utils_update
import os, codecs


class View(CustomView, TemplateView):
    template_name = "outils/notes_versions.html"
    menu_code = "notes_versions"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Notes de versions"
        liste_versions, totaux = utils_update.Analyser_changelog(self.GetChangelog())

        # Regroupement des versions par année
        liste_annees = []
        for dict_version in liste_versions:
            annee = dict_version["date"][-4:] if len(dict_version["date"]) >= 4 else "Autres"
            if not liste_annees or liste_annees[-1]["annee"] != annee:
                liste_annees.append({"annee": annee, "versions": []})
            liste_annees[-1]["versions"].append(dict_version)

        context['liste_annees'] = liste_annees
        context['nbre_versions'] = len(liste_versions)
        context['nbre_changements'] = sum(totaux.values())
        context['totaux'] = totaux
        context['date_premiere_version'] = liste_versions[-1]["date"] if liste_versions else ""
        context['date_derniere_version'] = liste_versions[0]["date"] if liste_versions else ""
        return context

    def GetChangelog(self):
        fichier = codecs.open(os.path.join(settings.BASE_DIR, "versions.txt"), encoding='utf-8', mode="r")
        changelog = fichier.read()
        fichier.close()
        return changelog
