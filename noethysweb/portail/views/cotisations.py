# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
from django.http import Http404
from core.models import Rattachement
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from cotisations.utils import utils_cotisations_manquantes
from core.models import Cotisation
from portail.views.base import CustomView


class View(CustomView, TemplateView):
    menu_code = "portail_cotisations"
    template_name = "portail/cotisations.html"

    def get_object(self):
        """Récupérer l'objet famille ou individu selon l'utilisateur"""
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            return self.request.user.individu
        else:
            raise Http404("Utilisateur non reconnu.")

    def get_famille_object(self):
        """Récupérer les familles de l'individu si applicable"""
        if hasattr(self.request.user, 'famille'):
            return [self.request.user.famille]
        elif hasattr(self.request.user, 'individu'):
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            familles = [rattachement.famille for rattachement in rattachements if rattachement.famille and rattachement.titulaire == 1]
            return familles if familles else None
        return None

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Adhésions")
        familles = self.get_famille_object()
        context['familles'] = familles
        # Initialiser la liste pour stocker toutes les cotisations
        cotisations_combinees = []

        if familles:
            for famille in familles:
                # Adhésions à fournir
                context['cotisations_fournir'] = utils_cotisations_manquantes.Get_cotisations_manquantes(
                    famille=famille, exclure_individus=famille.individus_masques.all())

                # Liste des dernières adhésions pour la famille en cours
                cotisations_famille = Cotisation.objects.select_related("prestation", "individu").filter(
                    famille=famille).order_by("date_debut")

                # Ajouter les cotisations de cette famille à la liste combinée
                cotisations_combinees.extend(cotisations_famille)

        # Ajouter la liste combinée des cotisations au contexte
        context['liste_cotisations'] = cotisations_combinees

        return context
