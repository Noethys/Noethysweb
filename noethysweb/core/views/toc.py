# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView
from django.conf import settings
from core.views import menu_favoris, menu_infos


class Toc(CustomView, TemplateView):
    template_name = "core/toc.html"

    def get_context_data(self, **kwargs):
        context = super(Toc, self).get_context_data(**kwargs)

        # Recherche le menu actif
        menu_principal = context['menu_principal']
        menu = menu_principal.Find(code=self.menu_code)

        # Mémorise le nom du menu
        context['page_titre'] = menu.titre
        context['mode_demo'] = settings.MODE_DEMO

        # Favoris de l'utilisateur
        codes_favoris = menu_favoris.Get_codes_favoris(context.get("options_interface", {}))
        context['codes_favoris'] = codes_favoris
        context['commandes_favorites'] = menu_favoris.Get_commandes_favorites(menu_principal=menu, codes=codes_favoris) if menu else []
        context['commandes_menu'] = menu.GetCommandes() if menu else []
        context['natures'] = menu_infos.NATURES
        context['affichage_condense'] = bool(context.get("options_interface", {}).get("menu_affichage_condense", False))

        return context
