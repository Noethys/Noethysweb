# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from portail.views.base import CustomView
from individus.utils import utils_pieces_manquantes
from core.models import PortailMessage


class Accueil(CustomView, TemplateView):
    template_name = "portail/accueil.html"
    menu_code = "portail_accueil"

    def get_context_data(self, **kwargs):
        context = super(Accueil, self).get_context_data(**kwargs)
        context['page_titre'] = "Accueil"
        context['pieces_manquantes'] = utils_pieces_manquantes.Get_pieces_manquantes(famille=self.request.user.famille, only_invalides=True)
        context['liste_messages_non_lus'] = PortailMessage.objects.filter(famille=self.request.user.famille, utilisateur__isnull=False, date_lecture__isnull=True)
        return context
