# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from django.utils.translation import gettext as _


class View(CustomView, TemplateView):
    menu_code = "portail_mentions"
    template_name = "portail/mentions.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Mentions légales")

        # Fusion du texte des conditions légales avec les valeurs organisateur
        texte_conditions = context['parametres_portail'].get("mentions_conditions_generales", "")
        for nom_champ in ("nom", "rue", "cp", "ville"):
            texte_conditions = texte_conditions.replace("{ORGANISATEUR_%s}" % nom_champ.upper(), getattr(context['organisateur'], nom_champ) or "")
        context['texte_conditions'] = texte_conditions

        return context
