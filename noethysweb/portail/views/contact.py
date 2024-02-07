# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from core.models import Structure, PortailMessage, Inscription, Activite
from django.db.models import Q, Count


class View(CustomView, TemplateView):
    menu_code = "portail_contact"
    template_name = "portail/contact.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Contact")

        # Récupération des activités avec inscription
        inscriptions = Inscription.objects.filter(famille=self.request.user.famille)
        activites_avec_inscription = list(set(inscription.activite for inscription in inscriptions))

        # Filtrer les structures liées aux activités avec inscription
        liste_structures = Structure.objects.filter(activite__in=activites_avec_inscription, messagerie_active=True).distinct().order_by("nom")

        # Structures avec messagerie
        context['liste_structures_messagerie'] = [structure for structure in liste_structures if structure.messagerie_active]

        # Structures avec coordonnées
        context['liste_structures_coords'] = [structure for structure in liste_structures if structure.afficher_coords]

        # Importation du nombre de messages non lus (regroupement par structure)
        context['dict_messages_non_lus'] = {valeur["structure"]: valeur["nbre"] for valeur in PortailMessage.objects.values("structure").filter(famille=self.request.user.famille, utilisateur__isnull=False, date_lecture__isnull=True).annotate(nbre=Count('pk'))}

        return context
