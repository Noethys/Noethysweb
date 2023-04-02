# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from collaborateurs.forms.appliquer_modele_planning import Formulaire
from collaborateurs.utils import utils_evenements


class View(CustomView, TemplateView):
    menu_code = "appliquer_modele_planning"
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Appliquer un modèle de planning"
        context['box_titre'] = "Appliquer un modèle de planning"
        context['box_introduction'] = "Sélectionnez une période d'application, les collaborateurs concernés, et le ou les modèles à appliquer."
        context['form'] = Formulaire()
        return context

    def post(self, request):
        # Validation du formulaire
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Récupération des valeurs du formulaire
        date_debut = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[1])
        modeles = form.cleaned_data["modeles"]
        collaborateurs = form.cleaned_data["collaborateurs"]

        # Génération des évènements
        for collaborateur in collaborateurs:
            resultats = utils_evenements.Generation_evenements(idcollaborateur=collaborateur.pk, modeles=modeles, date_debut=date_debut, date_fin=date_fin)

            if resultats["resultat"] == "erreur":
                messages.add_message(self.request, messages.ERROR, resultats["message_erreur"])
                return self.render_to_response(self.get_context_data(form=form))

            if resultats["evenements_refus"]:
                messages.add_message(self.request, messages.ERROR, "%s : %d évènements n'ont pas été générés car ils sont en conflit avec d'autres évènements ou sont hors contrat" % (collaborateur.Get_nom(), len(resultats["evenements_refus"])))
            if resultats["evenements_valides"]:
                messages.add_message(self.request, messages.SUCCESS, "%s : %d évènements ont été générés" % (collaborateur.Get_nom(), len(resultats["evenements_valides"])))

        return HttpResponseRedirect(reverse_lazy("collaborateurs_toc"))
