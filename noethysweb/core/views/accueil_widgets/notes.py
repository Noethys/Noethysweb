# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.models import Note
from core.views import accueil_widget


class Widget(accueil_widget.Widget):
    code = "notes"
    label = "Notes"

    def init_context_data(self):
        self.context['notes'] = self.Get_notes()

    def Get_notes(self):
        conditions = Q(date_parution__lte=datetime.date.today()) & (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        return Note.objects.select_related('famille', 'individu', 'collaborateur').filter(conditions, afficher_accueil=True).order_by("date_parution")
