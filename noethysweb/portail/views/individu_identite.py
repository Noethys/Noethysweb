# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from portail.views.fiche import Onglet, ConsulterBase
from portail.forms.individu_identite import Formulaire


class Consulter(Onglet, ConsulterBase):
    form_class = Formulaire
    template_name = "portail/fiche_edit.html"
    mode = "CONSULTATION"
    onglet_actif = "individu_identite"
    categorie = "individu_identite"
    titre_historique = "Modifier l'identité"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Identité"
        context['box_introduction'] = "Cliquez sur le bouton Modifier au bas de la page pour modifier une des informations ci-dessous."
        context['onglet_actif'] = self.onglet_actif
        return context

    def get_object(self):
        return self.get_individu()



class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez les informations concernant l'identité de l'individu et cliquez sur le bouton Enregistrer."
        if not self.get_dict_onglet_actif().validation_auto:
            context['box_introduction'] += " Ces informations devront être validées par l'administrateur de l'application."
        return context

    def get_success_url(self):
        return reverse_lazy("portail_individu_identite", kwargs={'idrattachement': self.kwargs['idrattachement']})
