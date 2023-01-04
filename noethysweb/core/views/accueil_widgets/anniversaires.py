# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.core.cache import cache
from core.views import accueil_widget
from core.models import Individu
from core.utils import utils_texte


class Widget(accueil_widget.Widget):
    code = "anniversaires"
    label = "Anniversaires du jour"

    def init_context_data(self):
        self.context['anniversaires_aujourdhui'] = self.Get_anniversaires()

    def Get_anniversaires(self, demain=False):
        """ Récupère les anniversaires """
        texte_anniversaires = cache.get("texte_anniversaires_demain" if demain else "texte_anniversaires")
        if not texte_anniversaires:
            date_jour = datetime.date.today()
            if demain:
                date_jour += datetime.timedelta(days=1)
            individus = Individu.objects.filter(date_naiss__isnull=False, inscription__isnull=False).distinct()
            liste_textes = []
            for individu in individus:
                if individu.date_naiss.month == date_jour.month and individu.date_naiss.day == date_jour.day:
                    liste_textes.append("%s %s (%d ans)" % (individu.prenom, individu.nom, individu.Get_age(today=date_jour)))
            if liste_textes:
                texte_anniversaires = "Joyeux anniversaire à %s." % utils_texte.Convert_liste_to_texte_virgules(liste_textes)
            else:
                texte_anniversaires = "Aucun anniversaire à fêter."
            cache.set("texte_anniversaires_demain" if demain else "texte_anniversaires", texte_anniversaires, timeout=3600)
        return texte_anniversaires
