# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from fiche_famille.forms.famille_questionnaire import Formulaire
from fiche_famille.views.famille import Onglet
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from core.models import QuestionnaireQuestion, QuestionnaireReponse


class Consulter(Onglet, TemplateView):
    template_name = "fiche_famille/famille_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Questionnaire"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        if not self.request.user.has_perm("core.famille_questionnaire_modifier"):
            context['box_introduction'] = "Vous n'avez pas l'autorisation de modifier les informations de cette page."
        context['onglet_actif'] = "questionnaire"
        context['form'] = Formulaire(idfamille=self.kwargs['idfamille'], request=self.request, mode=self.mode)
        return context


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez le questionnaire de la famille."
        return context

    def test_func_page(self):
        return self.request.user.has_perm("core.famille_questionnaire_modifier")

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, idfamille=self.kwargs['idfamille'], request=self.request, mode=self.mode)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Enregistrement des réponses du questionnaire
        for key, valeur in form.cleaned_data.items():
            if key.startswith("question_"):
                idquestion = int(key.split("_")[1])
                objet, created = QuestionnaireReponse.objects.update_or_create(famille_id=self.kwargs['idfamille'], question_id=idquestion, defaults={'reponse': valeur})

        return HttpResponseRedirect(reverse_lazy("famille_questionnaire", args=(self.kwargs['idfamille'],)))
