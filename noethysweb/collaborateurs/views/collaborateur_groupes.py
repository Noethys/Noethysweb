# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Collaborateur
from collaborateurs.forms.collaborateur_groupes import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Groupes"
        context['box_introduction'] = "Les groupes permettent de classer les collaborateurs (équipe, site, service...). Lorsque des superviseurs sont définis pour un groupe, seuls ces utilisateurs ont accès aux collaborateurs du groupe. Cliquez sur le bouton Modifier pour changer les groupes."
        context['onglet_actif'] = "groupes"
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Sélectionnez le ou les groupes du collaborateur puis cliquez sur le bouton Enregistrer. Les groupes se paramètrent dans Paramétrage > Groupes de collaborateurs."
        return context

    def get_success_url(self):
        return reverse_lazy("collaborateur_groupes", kwargs={'idcollaborateur': self.kwargs['idcollaborateur']})
