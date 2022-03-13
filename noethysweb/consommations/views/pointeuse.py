# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import render
from consommations.views import gestionnaire


class View(gestionnaire.View):
    menu_code = "pointeuse_conso"
    template_name = "consommations/pointeuse.html"
    mode_grille = "pointeuse"

    def post(self, request, *args, **kwargs):
        # Si requête de MAJ
        if request.POST.get("type_submit") == "MAJ" or request.POST.get("donnees_ajouter_individu"):
            context = self.get_context_data(**kwargs)
            return render(request, self.template_name, context)
        return HttpResponseRedirect(reverse_lazy("consommations_toc"))

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Pointeuse en temps réel"
        return context
