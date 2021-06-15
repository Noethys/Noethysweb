# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Famille
from fiche_famille.forms.famille_abo_factures_email import Formulaire
from fiche_famille.views.famille import Onglet



class Modifier(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_titre'] = "Envoi des factures par Email"
        context['box_introduction'] = "Vous pouvez activer ici le service d'envoi des factures par Email. Sélectionnez une ou plusieurs adresses de destination."
        context['onglet_actif'] = "factures"
        return context

    def get_success_url(self):
        return reverse_lazy("famille_factures_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Modifier, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs
