# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Individu
from fiche_individu.forms.individu_questionnaire import Formulaire
from fiche_individu.views.individu import Onglet
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from core.models import QuestionnaireQuestion, QuestionnaireReponse


class Modifier(Onglet, TemplateView):
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_titre'] = "Questionnaire"
        context['box_introduction'] = "Renseignez le questionnaire de l'individu."
        context['onglet_actif'] = "questionnaire"
        context['form'] = Formulaire(idfamille=self.kwargs['idfamille'], idindividu=self.kwargs['idindividu'])
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, idfamille=self.kwargs['idfamille'], idindividu=self.kwargs['idindividu'])
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Enregistrement des réponses du questionnaire
        for key, valeur in form.cleaned_data.items():
            if key.startswith("question_"):
                idquestion = int(key.split("_")[1])
                objet, created = QuestionnaireReponse.objects.update_or_create(individu_id=self.kwargs['idindividu'], question_id=idquestion, defaults={'reponse': valeur})

        return HttpResponseRedirect(reverse_lazy("individu_resume", args=(self.kwargs['idfamille'], self.kwargs['idindividu'])))
