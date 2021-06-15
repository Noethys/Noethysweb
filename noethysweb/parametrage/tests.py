# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.test import TestCase
from django.urls import reverse
from core.models import *
from core.tests import Classe_commune


class Parametrage(Classe_commune):

    def test_urls_ajax(self):
        from parametrage.urls import urlpatterns
        for url in urlpatterns:
            if "ajax_" in url.name and "/<" not in url.pattern._route:
                response = self.client.get(reverse(url.name))
                self.assertEqual(response.status_code, 302)
