#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, sys
logger = logging.getLogger(__name__)
from django.core.management import call_command


def Test():
    """ Test de cron """
    logger.debug("Lancement du Test_cron")
    logger.debug("%s : Lancement du TEST cron" % datetime.datetime.now())
    logger.debug("Version de python : %s" % sys.version)
    logger.debug("Executable de python : %s" % sys.executable)
    logger.debug("Fin du TEST cron")


def Sauvegarder_db():
    """ Sauvegarde de la base de données """
    logger.debug("%s : Lancement de dbbackup" % datetime.datetime.now())
    from core.utils import utils_gnupg
    utils_gnupg.Importation_cles()
    call_command("dbbackup", "--encrypt", verbosity=3)
    logger.debug("Fin de la sauvegarde db")


def Sauvegarder_media():
    """ Sauvegarde du répertoire media """
    logger.debug("%s : Lancement de mediabackup" % datetime.datetime.now())
    from core.utils import utils_gnupg
    utils_gnupg.Importation_cles()
    call_command("mediabackup", "--encrypt", verbosity=3)
    logger.debug("Fin de la sauvegarde media")
