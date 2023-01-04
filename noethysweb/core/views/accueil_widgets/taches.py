# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.models import Tache
from core.views import accueil_widget


class Widget(accueil_widget.Widget):
    code = "taches"
    label = "Tâches"

    def init_context_data(self):
        self.context['taches'] = self.Get_taches()

    def Get_taches(self):
        conditions = Q(date__lte=datetime.date.today()) & (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        return Tache.objects.filter(conditions).order_by("date")
