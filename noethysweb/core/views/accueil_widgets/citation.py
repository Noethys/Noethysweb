# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, random
logger = logging.getLogger(__name__)
from django.core.cache import cache
from core.views import accueil_widget
from core.utils import utils_parametres
from core.data.data_citations import LISTE_CITATIONS


class Widget(accueil_widget.Widget):
    code = "citation"
    label = "Citation du jour"

    def init_context_data(self):
        self.context['citation_texte'], self.context['citation_auteur'] = self.Get_citation()

    def Get_citation(self):
        num_citation = cache.get('num_citation')
        if not num_citation:
            parametre = utils_parametres.Get(nom="num_citation", categorie="page_accueil", valeur="")
            if parametre.startswith(str(datetime.date.today())):
                num_citation = int(parametre.split(";")[1])
            else:
                num_citation = random.randint(0, len(LISTE_CITATIONS) - 1)
                utils_parametres.Set(nom="num_citation", categorie="page_accueil", valeur="%s;%d" % (datetime.date.today(), num_citation))
            cache.set('num_citation', num_citation)
        return LISTE_CITATIONS[num_citation]
