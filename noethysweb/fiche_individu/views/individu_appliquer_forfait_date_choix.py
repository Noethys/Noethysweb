# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from core.models import Tarif, TarifLigne
from individus.utils import utils_forfaits
from fiche_individu.forms.individu_appliquer_forfait_date_choix import Formulaire
from fiche_individu.views.individu import Onglet


class View(Onglet, TemplateView):
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Choisir le montant d'un forfait"
        context['box_introduction'] = "L'inscription est associée à un forfait avec montant au choix. Veuillez sélectionner le montant à appliquer. Si vous cliquez sur Annuler, le forfait ne sera pas appliqué."
        context['onglet_actif'] = "inscriptions"
        if "form" in kwargs:
            context['form'] = Formulaire(self.request.POST.copy(), idfamille=self.kwargs['idfamille'], idindividu=self.kwargs['idindividu'], tarifs=self.kwargs['tarifs'], request=self.request)
        else:
            context['form'] = Formulaire(idfamille=self.kwargs['idfamille'], idindividu=self.kwargs['idindividu'], tarifs=self.kwargs['tarifs'], request=self.request)
        return context

    def post(self, request, **kwargs):
        # Validation du form
        form = Formulaire(request.POST, idfamille=self.kwargs['idfamille'], idindividu=self.kwargs['idindividu'], tarifs=self.kwargs['tarifs'], request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        dict_tarifs_lignes = {int(key.split("_")[1]): int(valeur) for key, valeur in form.cleaned_data.items()}

        # Application des forfaits
        for idtarif, idligne in dict_tarifs_lignes.items():
            tarif = Tarif.objects.get(pk=idtarif)
            ligne = TarifLigne.objects.select_related("activite").get(pk=idligne)
            f = utils_forfaits.Forfaits(famille=self.kwargs["idfamille"], activites=[ligne.activite_id], individus=[self.kwargs["idindividu"]],
                                        saisie_manuelle=tarif.forfait_saisie_manuelle, saisie_auto=tarif.forfait_saisie_auto)
            choix_montant = (ligne.montant_unique, ligne.label)
            f.Applique_forfait(request=self.request, mode_inscription=False, selection_tarif=idtarif, selection_activite=ligne.activite_id, choix_montant=choix_montant)

        return HttpResponseRedirect(reverse_lazy("individu_inscriptions_liste", args=(self.kwargs['idfamille'], self.kwargs['idindividu'])))
