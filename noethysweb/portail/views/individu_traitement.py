# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import DetailView
from django.utils.translation import gettext as _
from core.models import Traitement, Famille, Individu
from portail.views.fiche import Onglet
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db.models import Q

class Liste(Onglet, DetailView):
    template_name = "portail/individu_traitement.html"
    onglet_actif = "individu_traitement"  # Initialiser ici

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = _("Liste des traitements effectués par l'assistant sanitaire")
        context['box_introduction'] = _("")
        context['onglet_actif'] = self.onglet_actif

        # Récupérer tous les objets TypePiece
        context['traitements'] = self.get_traitements()

        return context

    def get_traitements(self):
        individu = self.get_individu()
        individu_id = individu.pk
        date_actuelle = now()
        date_limite = date_actuelle - timedelta(days=365)
        
        # Filtre sur les traitements des 365 derniers jours
        # ET dont l'activité a une date_traitements_visibles null ou antérieure à maintenant
        return Traitement.objects.filter(
            individu_id=individu_id, 
            date__gte=date_limite
        ).filter(
            Q(activite__date_traitements_visibles__isnull=True) | 
            Q(activite__date_traitements_visibles__lte=date_actuelle)
        ).select_related('activite').order_by('-date')

    def get_object(self):
        return self.get_individu()  # Assurez-vous que cette méthode est bien définie
