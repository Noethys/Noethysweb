# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse_lazy
from core.views import crud
from core.models import Consentement, Rattachement
from portail.views.base import CustomView
from portail.forms.approbations import Formulaire


class View(CustomView, crud.Modifier):
    menu_code = "portail_renseignements"
    form_class = Formulaire
    template_name = "portail/renseignements.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Renseignements"
        context['rattachements'] = Rattachement.objects.prefetch_related('individu').filter(famille=self.request.user.famille).order_by("individu__nom", "individu__prenom")
        return context

    def get_object(self):
        return self.request.user.famille

    def get_success_url(self):
        return reverse_lazy("portail_renseignements")

    def form_valid(self, form):
        """ Enregistrement des approbations """
        # Enregistrement des approbations cochées
        nbre_coches = 0
        for code, coche in form.cleaned_data.items():
            if coche:
                if "unite" in code:
                    idunite = int(code.replace("unite_", ""))
                    Consentement.objects.create(famille=self.request.user.famille, unite_consentement_id=idunite)
                    nbre_coches += 1
                if "rattachement" in code:
                    idrattachement = int(code.replace("rattachement_", ""))
                    Rattachement.objects.filter(pk=idrattachement).update(certification_date=datetime.datetime.now())
                    nbre_coches += 1
                if "famille" in code:
                    self.request.user.famille.certification_date = datetime.datetime.now()
                    self.request.user.famille.save()
                    nbre_coches += 1

        # Message de confirmation
        if nbre_coches == 0:
            messages.add_message(self.request, messages.ERROR, "Aucune approbation n'a été cochée")
        elif nbre_coches == 1:
            messages.add_message(self.request, messages.SUCCESS, "L'approbation cochée a bien été enregistrée")
        else:
            messages.add_message(self.request, messages.SUCCESS, "Les %d approbations cochées ont bien été enregistrées" % nbre_coches)
        return HttpResponseRedirect(self.get_success_url())
