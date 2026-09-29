# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.http import HttpResponse
from django.views.generic import FormView
from core.views.base import CustomView
from core.utils import utils_export_parametrage
from parametrage.forms.activites_controle_ia import Formulaire


class View(CustomView, FormView):
    menu_code = "activites_liste"
    template_name = "parametrage/activites_controle_ia.html"
    form_class = Formulaire

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(View, self).get_form_kwargs(**kwargs)
        form_kwargs["request"] = self.request
        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Gestion des activités"
        context["box_titre"] = "Contrôle IA du paramétrage"
        context["box_introduction"] = "Générez un fichier contenant le paramétrage d'une activité, puis transmettez-le à une IA (Claude, ChatGPT...) avec le prompt ci-dessous " \
                                      "pour obtenir une analyse de cohérence et des suggestions de corrections. <b>Aucune donnée personnelle des familles n'est incluse dans le fichier.</b>"
        context["prompt_ia"] = utils_export_parametrage.PROMPT
        return context

    def form_valid(self, form):
        activite = form.cleaned_data["activite"]
        try:
            contenu = utils_export_parametrage.Get_json(activite, depuis=form.cleaned_data["date_debut"], jusqua=form.cleaned_data["date_fin"],
                                                        tous_les_tarifs=form.cleaned_data["tous_les_tarifs"], noms_responsables=form.cleaned_data["noms_responsables"])
        except ValueError as erreur:
            form.add_error(None, str(erreur))
            return self.form_invalid(form)
        logger.debug("Contrôle IA : export du paramétrage de l'activité %d par %s", activite.pk, self.request.user)
        reponse = HttpResponse(contenu, content_type="application/json; charset=utf-8")
        reponse["Content-Disposition"] = 'attachment; filename="%s"' % utils_export_parametrage.Get_nom_fichier(activite)
        return reponse
