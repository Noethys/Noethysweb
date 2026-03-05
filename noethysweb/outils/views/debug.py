# -*- coding: utf-8 -*-
import os
from django.conf import settings
from django.views.generic import TemplateView
from core.views import crud


class DebugLog(crud.Page, TemplateView):
    template_name = "outils/debug.html"

    def get_context_data(self, **kwargs):
        # Initialisation du contexte via les parents
        context = super(DebugLog, self).get_context_data(**kwargs)

        # Ton code pour lire le log
        log_path = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'debug.log'))

        lignes = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                lignes = f.readlines()[-500:]
                lignes.reverse()
        else:
            lignes = [f"Fichier non trouvé : {log_path}"]

        context['lignes_log'] = lignes
        context['page_titre'] = "Debug Sacadoc"
        return context