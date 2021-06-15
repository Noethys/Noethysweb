# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView
from django.conf import settings
import os, codecs


class View(CustomView, TemplateView):
    template_name = "outils/notes_versions.html"
    menu_code = "notes_versions"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Notes de versions"
        context['box_titre'] = ""
        context['box_introduction'] = "Voici les dernières modifications de Noethysweb :"
        context['changelog'] = self.GetChangelog()
        return context

    def GetChangelog(self):
        fichier = codecs.open(os.path.join(settings.BASE_DIR, "versions.txt"), encoding='utf-8', mode="r")
        changelog = fichier.read()
        fichier.close()
        return changelog
