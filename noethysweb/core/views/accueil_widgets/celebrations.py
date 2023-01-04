# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from core.utils import utils_texte
from core.data.data_celebrations import DICT_FETES, DICT_CELEBRATIONS


class Widget(accueil_widget.Widget):
    code = "celebrations"
    label = "Célébrations du jour"

    def init_context_data(self):
        self.context['celebrations'] = self.Get_celebrations()

    def Get_celebrations(self):
        """ Récupère les célébrations du jour """
        date_jour = datetime.date.today()

        # Fêtes
        texte_fetes = ""
        if (date_jour.day, date_jour.month) in DICT_FETES:
            noms = DICT_FETES[(date_jour.day, date_jour.month)]
            texte_fetes = utils_texte.Convert_liste_to_texte_virgules(noms.split(";"))

        # Célébrations
        texte_celebrations = ""
        if (date_jour.day, date_jour.month) in DICT_CELEBRATIONS:
            texte_celebrations = DICT_CELEBRATIONS[(date_jour.day, date_jour.month)]

        # Mix des fêtes et des célébrations
        if texte_fetes and texte_celebrations: return "Nous fêtons aujourd'hui les %s et célébrons %s." % (texte_fetes, texte_celebrations)
        elif texte_fetes and not texte_celebrations: return "Nous fêtons aujourd'hui les %s." % texte_fetes
        elif not texte_fetes and texte_celebrations: return "Nous célébrons aujourd'hui %s." % texte_celebrations
        return "Aucune célébration aujourd'hui."
