# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import TemplateView
from core.utils import utils_dates
from collaborateurs.forms.collaborateur_appliquer_modele_planning import Formulaire
from collaborateurs.views.collaborateur import Onglet
from collaborateurs.utils import utils_evenements


class View(Onglet, TemplateView):
    template_name = "collaborateurs/collaborateur_edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Appliquer un modèle de planning"
        context['box_introduction'] = "Sélectionnez une période d'application et le ou les modèles à appliquer."
        context['onglet_actif'] = "evenements"
        context['idcollaborateur'] = kwargs.get("idcollaborateur")
        context['form'] = Formulaire(request=self.request)
        return context

    def post(self, request, idcollaborateur):
        # Validation du formulaire
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form, idcollaborateur=idcollaborateur))

        # Récupération des valeurs du formulaire
        date_debut = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[1])
        modeles = form.cleaned_data["modeles"]

        # Génération des évènements
        resultats = utils_evenements.Generation_evenements(idcollaborateur=idcollaborateur, modeles=modeles, date_debut=date_debut, date_fin=date_fin)

        if resultats["resultat"] == "erreur":
            messages.add_message(self.request, messages.ERROR, resultats["message_erreur"])
            return self.render_to_response(self.get_context_data(form=form, idcollaborateur=idcollaborateur))

        if resultats["evenements_refus"]:
            messages.add_message(self.request, messages.ERROR, "%d évènements n'ont pas été générés car ils sont en conflit avec d'autres évènements ou sont hors contrat" % len(resultats["evenements_refus"]))
        if resultats["evenements_valides"]:
            messages.add_message(self.request, messages.SUCCESS, "%d évènements ont été générés" % len(resultats["evenements_valides"]))

        return HttpResponseRedirect(reverse_lazy("collaborateur_evenements_liste", kwargs={"idcollaborateur": idcollaborateur}))
