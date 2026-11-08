# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Famille
from fiche_famille.forms.famille_caisse import Formulaire
from fiche_famille.views.famille import Onglet



class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"
    objet_singulier = "la caisse"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Caisse"
        context['box_introduction'] = "Consultez ci-dessous les informations de cette rubrique. Cliquez sur le bouton Modifier pour les mettre à jour."
        if not self.request.user.has_perm("core.famille_caisse_modifier"):
            context['box_introduction'] = "Vous pouvez consulter ces informations mais vous n'avez pas l'autorisation de les modifier. Adressez-vous à un administrateur si besoin."
        context['onglet_actif'] = "caisse"
        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Consulter, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez la caisse d'allocations de la famille (CAF, MSA...), le numéro d'allocataire et le titulaire du dossier, ainsi que les autorisations de consultation des données (CAFPRO, API Particulier)."
        return context

    def test_func_page(self):
        return self.request.user.has_perm("core.famille_caisse_modifier")

    def get_success_url(self):
        return reverse_lazy("famille_caisse", kwargs={'idfamille': self.kwargs.get('idfamille', None)})
