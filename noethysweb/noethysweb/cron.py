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
    logger.debug("%s : Lancement de dbbackup..." % datetime.datetime.now())
    from core.utils import utils_gnupg
    utils_gnupg.Importation_cles()
    call_command("dbbackup", "--encrypt", "--clean", verbosity=1)
    logger.debug("Fin de la sauvegarde db")

def Sauvegarder_media():
    """ Sauvegarde du répertoire media """
    logger.debug("%s : Lancement de mediabackup..." % datetime.datetime.now())
    from core.utils import utils_gnupg
    utils_gnupg.Importation_cles()
    call_command("mediabackup", "--encrypt", "--clean", verbosity=3)
    logger.debug("Fin de la sauvegarde media")

def Traiter_attentes():
    logger.debug("%s : Lancement du traitement des attentes..." % datetime.datetime.now())
    from consommations.utils import utils_traitement_attentes
    utils_traitement_attentes.Traiter_attentes(request=None)

def Vider_rep_temp():
    logger.debug("%s : Lancement du vidage du répertoire temp..." % datetime.datetime.now())
    call_command("reset_rep_temp")
    Corriger_anomalies()
    Purge_mdp_expires()
    Purge_auto_historique()
    # Nettoyer répertoire desk dans storage
    from outils.utils import utils_export_desk
    desk = utils_export_desk.Desk()
    desk.Nettoyer_storage()

def Corriger_anomalies():
    logger.debug("%s : Lancement de la correction automatique des anomalies..." % datetime.datetime.now())
    call_command("corrige_anomalies")

def Generer_taches():
    logger.debug("%s : Lancement de la génération des tâches récurrentes..." % datetime.datetime.now())
    call_command("generation_taches")

def Purge_mdp_expires():
    logger.debug("%s : Purge des mots de passe expirés..." % datetime.datetime.now())
    call_command("purge_mdp_expires")

def Purge_auto_historique():
    logger.debug("%s : Purge historique..." % datetime.datetime.now())
    call_command("purge_auto_historique")

def Recalculer_prestations_mois_precedent():
    logger.debug("%s : Recalculer les prestations du mois précédent..." % datetime.datetime.now())
    from dateutil.relativedelta import relativedelta
    call_command("recalculer_prestations", mois=format(datetime.date.today() - relativedelta(months=1), "%Y-%m"))

def Maj_soldes_factures():
    logger.debug("%s : MAJ totaux et soldes des factures..." % datetime.datetime.now())
    call_command("maj_soldes_factures")
