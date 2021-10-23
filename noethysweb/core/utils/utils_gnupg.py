# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, glob
logger = logging.getLogger(__name__)
from django.conf import settings


def Importation_cles():
    """ Importation de clés présentes dans le répertoire noethysweb """
    for nom_fichier in glob.glob(os.path.join(settings.BASE_DIR, "noethysweb/*.asc")):
        with open(nom_fichier, "r") as fichier:
            texte = fichier.read()
            import gnupg
            gpg = gnupg.GPG()
            import_result = gpg.import_keys(texte)
            logger.debug("Résultat importation key gnuppg : %s" % import_result.results)
