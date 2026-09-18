# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views import crud
from cotisations.forms.liste_adherents import Formulaire


class Page(crud.Page):
    url_liste = "liste_adherents"
    menu_code = "liste_adherents"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context["page_titre"] = "Liste des adhérents"
        context["box_titre"] = "Liste des adhérents"
        context["box_introduction"] = "Sélectionnez l'unité d'adhésion pour laquelle vous souhaitez consulter la liste des individus et des familles adhérentes."
        return context


class Selection(Page, crud.Ajouter):
    template_name = "core/crud/edit.html"
    form_class = Formulaire

    def post(self, request, **kwargs):
        form = self.form_class(request.POST, request=request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        idunite_cotisation = form.cleaned_data["unite_cotisation"].pk
        return HttpResponseRedirect(reverse_lazy("liste_adherents_individus", kwargs={"idunite_cotisation": idunite_cotisation}))
