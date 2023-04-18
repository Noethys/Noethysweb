# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.views.generic import TemplateView
from core.views.base import CustomView
from individus.utils import utils_transports


class View(CustomView, TemplateView):
    template_name = "parametrage/transports.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Paramétrage"

        items = []
        for code, dict_temp in utils_transports.CATEGORIES.items():
            parametrage = dict_temp.get("parametrage", {})
            if parametrage:
                item = {"titre": dict_temp["label"], "items": []}
                for code_parametre, dict_parametre in parametrage.items():
                    item["items"].append({"titre": dict_parametre["label_pluriel"].capitalize(), "url": reverse_lazy("%s_liste" % code_parametre, kwargs={"categorie": code}), "icone": "file-text-o"})
                items.append(item)

        context['items_menu'] = [items[len(items)//2:], items[:len(items)//2]]
        return context
