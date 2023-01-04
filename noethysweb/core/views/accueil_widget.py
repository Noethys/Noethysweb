# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)


class Widget:
    code = None
    label = None

    def __init__(self, request=None, context=None):
        self.request = request
        self.context = context or {}

    def init_context_data(self):
        pass
