# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, os, importlib
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.conf import settings
from core.views.base import CustomView
from core.utils import utils_parametres


class View(CustomView, TemplateView):
    menu_code = "accueil"
    template_name = "core/accueil/accueil_configuration.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Tableau de bord"
        context['box_titre'] = "Configuration du tableau de bord"
        context['box_introduction'] = "Ajoutez des lignes et faîtes glisser les widgets vers les emplacements de votre choix."
        context['colonnes_disponibles'] = [(12,), (6, 6), (9, 3), (3, 9), (8, 4), (4, 8), (7, 5), (5, 7), (4, 4, 4), (3, 3, 3, 3)]
        context['items_disponibles'] = self.Get_items_disponibles()
        context['config_defaut'] = mark_safe(json.dumps(settings.CONFIG_ACCUEIL_DEFAUT))
        context['config_actuelle'] = mark_safe(context["options_interface"]["configuration_accueil"])
        return context

    def Get_items_disponibles(self):
        dict_items = {}
        for nom_fichier in os.listdir(os.path.join(settings.BASE_DIR, "core/views/accueil_widgets")):
            if not nom_fichier.startswith("__"):
                nom_item = os.path.splitext(os.path.basename(nom_fichier))[0]
                module = importlib.import_module("core.views.accueil_widgets.%s" % nom_item)
                widget = module.Widget()
                dict_items[widget.code] = widget.label
        return dict_items

    def post(self, request, **kwargs):
        valeur = request.POST["resultats"]
        utils_parametres.Set(nom="configuration_accueil", categorie="options_interface", utilisateur=request.user, valeur=valeur)
        cache.delete("options_interface_user%d" % request.user.pk)
        return HttpResponseRedirect(reverse_lazy("accueil"))
