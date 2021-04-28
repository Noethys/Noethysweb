# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os
from django.conf import settings


def GetTempRep():
    # Création du répertoire media s'il n'existe pas
    if not os.path.isdir(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    # Création du répertoire temp s'il n'existe pas
    rep_temp = settings.MEDIA_ROOT + "/temp"
    if not os.path.isdir(rep_temp):
        os.mkdir(rep_temp)
    return rep_temp
