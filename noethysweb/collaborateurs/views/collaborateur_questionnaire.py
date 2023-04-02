# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from core.models import QuestionnaireReponse
from collaborateurs.forms.collaborateur_questionnaire import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Consulter(Onglet, TemplateView):
    template_name = "collaborateurs/collaborateur_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Questionnaire"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        context['onglet_actif'] = "questionnaire"
        context['form'] = Formulaire(idcollaborateur=self.kwargs["idcollaborateur"], request=self.request, mode=self.mode)
        return context


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez le questionnaire du collaborateur."
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, idcollaborateur=self.kwargs["idcollaborateur"], request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Enregistrement des réponses du questionnaire
        for key, valeur in form.cleaned_data.items():
            if key.startswith("question_"):
                idquestion = int(key.split("_")[1])
                objet, created = QuestionnaireReponse.objects.update_or_create(collaborateur_id=self.kwargs["idcollaborateur"], question_id=idquestion, defaults={'reponse': valeur})

        return HttpResponseRedirect(reverse_lazy("collaborateur_questionnaire", kwargs={"idcollaborateur": self.kwargs["idcollaborateur"]}))
