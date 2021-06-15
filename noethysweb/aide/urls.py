# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import include, path
from core.views import toc


urlpatterns = [

    # Table des matières
    path('aide/', toc.Toc.as_view(menu_code="aide_toc"), name='aide_toc'),


]
