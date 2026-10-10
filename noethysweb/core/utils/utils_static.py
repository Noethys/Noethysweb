# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from functools import lru_cache
from django.contrib.staticfiles.storage import StaticFilesStorage
from noethysweb.version import GetVersion


@lru_cache(maxsize=1)
def Get_cle_version():
    """ Numéro de version utilisé comme clé de cache des fichiers statiques """
    try:
        return GetVersion() or "0"
    except Exception:
        return "0"


class StaticFilesVersionnes(StaticFilesStorage):
    """ Ajoute ?v=<version> aux URL des fichiers statiques pour forcer leur rechargement après une mise à jour """
    def url(self, name):
        url = super().url(name)
        if not name or "?" in url:
            return url
        return "%s?v=%s" % (url, Get_cle_version())
