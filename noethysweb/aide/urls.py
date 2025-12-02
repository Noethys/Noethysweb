# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from aide.views import aide_accueil


urlpatterns = [

    # Aide
    path('aide/accueil', aide_accueil.View.as_view(), name="aide_accueil"),

]
