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
import datetime
from collaborateurs.utils import utils_evenements
from collaborateurs.utils.utils_modeles_planning import Generateur, Get_departs, Repartir, Memoriser_recents


class View(Onglet, TemplateView):
    template_name = "collaborateurs/collaborateur_edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Appliquer un modèle de planning"
        context['box_introduction'] = "Sélectionnez une période d'application et le ou les modèles à appliquer."
        context['onglet_actif'] = "evenements"
        context['idcollaborateur'] = kwargs.get("idcollaborateur")
        context['form'] = kwargs.get("form") or Formulaire(request=self.request)
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
        dates = [date_debut + datetime.timedelta(days=n) for n in range((date_fin - date_debut).days + 1)]
        generateur = Generateur(modeles=modeles, dates=dates, departs=Get_departs(request))
        repartition, messages_restriction = Repartir(modeles=modeles, collaborateurs=[idcollaborateur], date=date_debut, forcer=request.POST.get("forcer_modeles") == "true")
        for message in messages_restriction:
            messages.add_message(self.request, messages.WARNING, message)
        resultats = utils_evenements.Generation_evenements(idcollaborateur=idcollaborateur, modeles=modeles, date_debut=date_debut, date_fin=date_fin, generateur=generateur,
                                                           modeles_autorises={idmodele for idmodele, ids in repartition.items() if idcollaborateur in ids})

        if resultats["resultat"] == "erreur":
            messages.add_message(self.request, messages.ERROR, resultats["message_erreur"])
            return self.render_to_response(self.get_context_data(form=form, idcollaborateur=idcollaborateur))

        if resultats["evenements_refus"]:
            messages.add_message(self.request, messages.ERROR, "%d évènements n'ont pas été générés car ils sont en conflit avec d'autres évènements ou sont hors contrat" % len(resultats["evenements_refus"]))
        if resultats["evenements_valides"]:
            messages.add_message(self.request, messages.SUCCESS, "%d évènements ont été générés" % len(resultats["evenements_valides"]))
            generateur.Memoriser_ancrages()
            Memoriser_recents(request.user, modeles)

        return HttpResponseRedirect(reverse_lazy("collaborateur_evenements_liste", kwargs={"idcollaborateur": idcollaborateur}))
