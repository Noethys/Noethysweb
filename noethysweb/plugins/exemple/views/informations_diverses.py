# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView


class View(CustomView, TemplateView):
    menu_code = "exemple"
    template_name = "exemple/informations_diverses.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Informations diverses"
        context['box_titre'] = "Informations diverses"
        context['box_introduction'] = "Voici un exemple de template personnalisable."
        return context
