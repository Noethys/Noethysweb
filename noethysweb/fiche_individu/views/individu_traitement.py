# -*- coding: utf-8 -*-
# Copyright (c) 2019-2021 Ivan LUCAS.
# Noethysweb, application de gestion multi-activités.
# Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import JsonResponse
from datatableview.views import MultipleDatatableView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu, Traitement
from fiche_individu.forms.individu_traitement import Formulaire as FormulaireTraitement
from fiche_individu.views.individu import Onglet
from individus.utils import utils_vaccinations
from datetime import timedelta
from django.utils.timezone import now
from django.views.generic import DetailView
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
class Liste(Onglet, DetailView):
    template_name = "fiche_individu/individu_traitement.html"
    onglet_actif = "traitement"
    model = Individu  # Indique que la vue traite des objets `Individu`

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['box_titre'] = _("Liste des traitements effectués par l'assistant sanitaire")
        context['box_introduction'] = _("Pour ajouter un traitement merci de passer par l'onglet Outils/Assistant sanitaire.")
        context['onglet_actif'] = self.onglet_actif
        context['traitements'] = self.get_traitements()
        context['idfamille'] = self.kwargs.get('idfamille')
        context['idindividu'] = self.kwargs.get('idindividu')
        return context

    def get_traitements(self):
        individu = self.get_object()
        date_actuelle = now()
        date_limite = date_actuelle - timedelta(days=365)
        return Traitement.objects.filter(individu=individu, date__gte=date_limite).order_by('-date')

    def get_object(self):
        individu_id = self.kwargs.get('idindividu')
        if not individu_id:
            raise ValueError(_("L'identifiant de l'individu est requis."))

        return get_object_or_404(Individu, pk=individu_id)
