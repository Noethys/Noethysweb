# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import path
from core.views import toc
from core.decorators import secure_ajax
from plugins.exemple.views import liste_reglements_especes, informations_diverses

urlpatterns = [

    # Table des matières [OBLIGATOIRE] : Remplacez exemple par le nom du plugin
    path("exemple/", toc.Toc.as_view(menu_code="exemple_toc"), name="exemple_toc"),

    # Urls du plugin
    path("exemple/liste_reglements_especes", liste_reglements_especes.Liste.as_view(), name="liste_reglements_especes"),
    path("exemple/informations_diverses", informations_diverses.View.as_view(), name="informations_diverses"),

]
