# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, datetime, codecs, zipfile, requests, subprocess, glob
logger = logging.getLogger(__name__)
from urllib.request import urlopen, urlretrieve
from noethysweb import version
from django.core.management import call_command
from django.conf import settings
from django.core.cache import cache


def Get_update_for_accueil(request=None):
    """ Recherche si une nouvelle version est disponible """
    key_cache = "last_check_update"
    last_check_update = cache.get(key_cache)
    if last_check_update:
        nouvelle_version = last_check_update["nouvelle_version"]
    if not last_check_update:
        nouvelle_version, changelog = Recherche_update()
        cache.set(key_cache, {"nouvelle_version": nouvelle_version}, timeout=60*60)
    return nouvelle_version


def Recherche_update():
    # Lecture de la version disponible en ligne
    url = "https://raw.githubusercontent.com/flambeaux-org/Sacadoc/refs/heads/main/noethysweb/versions.txt"
    logger.debug("Recherche d'une nouvelle version...")
    try:
        data = requests.get(url, timeout=10)
    except requests.exceptions.RequestException:
        logger.debug("Le fichier des versions n'a pas pu être téléchargé sur Github.")
        return False, False
    changelog = data.text

    # Lecture du numéro de version online
    pos_debut_numVersion = changelog.find("n")
    pos_fin_numVersion = changelog.find("(")
    version_online_txt = changelog[pos_debut_numVersion + 1:pos_fin_numVersion].strip()
    version_online_tuple = version.GetVersionTuple(version_online_txt)
    logger.debug("version disponible =" + version_online_txt)

    # Lecture version actuelle
    version_actuelle_txt = version.GetVersion()
    version_actuelle_tuple = version.GetVersionTuple(version_actuelle_txt)
    logger.debug("version actuelle =" + version_actuelle_txt)

    # Comparaison des versions
    if version_online_tuple <= version_actuelle_tuple:
        logger.debug("Pas de nouvelle version disponible")
        return False, changelog

    return version_online_txt, changelog


def backup_database():
    """Crée une sauvegarde de la base de données avec un timestamp dans le nom en utilisant la commande SQLite backup."""
    # Récupération du chemin de la base de données
    databases = settings.DATABASES
    if 'default' not in databases:
        logger.debug("Aucune base de données 'default' trouvée.")
        return False
    
    db_config = databases['default']
    
    # On ne fait la sauvegarde que pour SQLite
    if db_config.get('ENGINE') != 'django.db.backends.sqlite3':
        logger.debug("La sauvegarde automatique n'est supportée que pour SQLite.")
        return False
    
    db_path = db_config.get('NAME')
    if not db_path or not os.path.isfile(db_path):
        logger.debug(f"Fichier de base de données non trouvé: {db_path}")
        return False
    
    # Création du nom de fichier avec timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    db_dir = os.path.dirname(db_path)
    db_filename = os.path.basename(db_path)
    db_name, db_ext = os.path.splitext(db_filename)
    backup_filename = f"{db_name}_backup_{timestamp}{db_ext}"
    backup_path = os.path.join(db_dir, backup_filename)
    
    try:
        logger.debug(f"Sauvegarde de la base de données avec SQLite backup: {db_path} -> {backup_path}")

        # Utilisation de la commande backup de SQLite via CLI
        # Exécution de: sqlite3 db_path ".backup backup_path"
        result = subprocess.run(
            ['sqlite3', db_path, f'.backup {backup_path}'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        if result.returncode != 0:
            logger.error(f"Erreur lors de la sauvegarde SQLite: {result.stderr}")
            return False

        logger.debug("Sauvegarde de la base de données terminée avec succès.")

        # Nettoyage: garder seulement les 5 derniers backups
        cleanup_old_backups(db_dir, db_name, db_ext)

        return backup_path
    except subprocess.TimeoutExpired:
        logger.error("La sauvegarde de la base de données a dépassé le délai d'attente (5 minutes).")
        return False
    except FileNotFoundError:
        logger.error("La commande sqlite3 n'a pas été trouvée. Assurez-vous que SQLite est installé.")
        return False
    except Exception as err:
        logger.error(f"Erreur lors de la sauvegarde de la base de données: {err}")
        return False


def cleanup_old_backups(db_dir, db_name, db_ext, max_backups=5):
    """Supprime les anciens backups en ne gardant que les max_backups plus récents."""
    try:
        # Recherche tous les fichiers de backup
        pattern = os.path.join(db_dir, f"{db_name}_backup_*{db_ext}")
        backup_files = glob.glob(pattern)

        if len(backup_files) <= max_backups:
            logger.debug(f"Nombre de backups ({len(backup_files)}) <= {max_backups}, pas de nettoyage nécessaire.")
            return

        # Trier par date de modification (du plus ancien au plus récent)
        backup_files.sort(key=os.path.getmtime)

        # Supprimer les plus anciens pour ne garder que max_backups
        files_to_delete = backup_files[:-max_backups]

        for file_path in files_to_delete:
            logger.debug(f"Suppression de l'ancien backup: {file_path}")
            os.remove(file_path)

        logger.debug(f"Nettoyage terminé. {len(files_to_delete)} backup(s) supprimé(s).")
    except Exception as err:
        logger.error(f"Erreur lors du nettoyage des anciens backups: {err}")


def Update():
    # Recherche une version disponible
    version_online_txt, changelog = Recherche_update()
    if not version_online_txt:
        return False

    # Téléchargement du zip
    nom_fichier = "Sacadoc-%s.zip" % version_online_txt
    if not os.path.isdir(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    rep_temp = settings.MEDIA_ROOT + "/temp"
    if not os.path.isdir(rep_temp):
        os.mkdir(rep_temp)
    chemin_fichier = os.path.join(rep_temp, nom_fichier)
    try:
        logger.debug("Telechargement de la version %s..." % version_online_txt)
        url_telechargement = "https://github.com/flambeaux-org/Sacadoc/archive/%s.zip" % version_online_txt
        urlretrieve(url_telechargement, chemin_fichier)
    except Exception as err:
        logger.debug("La nouvelle version '%s' n'a pas pu etre telechargee." % version_online_txt)
        logger.debug(err)
        return False

    # Backup de la db
    logger.debug("Sauvegarde de la base de données avant mise à jour...")
    backup_result = backup_database()
    if backup_result:
        logger.debug(f"Sauvegarde créée: {backup_result}")
    else:
        logger.warning("La sauvegarde de la base de données a échoué ou n'est pas supportée.")

    # Dezippage
    logger.debug("Dezippage du zip...")
    zfile = zipfile.ZipFile(chemin_fichier, 'r')
    liste_fichiers = zfile.namelist()

    # Remplacement des fichiers
    prefixe = "Sacadoc-%s/noethysweb/" % version_online_txt
    chemin_dest = os.path.join(settings.BASE_DIR, "")

    logger.debug("Installation des nouveaux fichiers...")
    for i in liste_fichiers:
        d = i.replace(prefixe, "")
        if len(d) > 1 and not d.startswith("Sacadoc-%s" % version_online_txt):
            if i.endswith('/'):
                try:
                    os.makedirs(os.path.join(chemin_dest, d))
                except:
                    pass
            else:
                try:
                    os.makedirs(os.path.join(chemin_dest, os.path.dirname(d)))
                except:
                    pass
                nom_fichier_temp = os.path.join(chemin_dest, d)
                if os.path.isdir(nom_fichier_temp):
                    os.rmdir(nom_fichier_temp)
                data = zfile.read(i)
                fp = open(nom_fichier_temp, "wb")
                fp.write(data)
                fp.close()

    zfile.close()
    os.remove(chemin_fichier)
    logger.debug("Installation terminee.")

    # Efface le numéro de version du cache
    cache.delete('version_application')

    # AutoReloadWSGI
    logger.debug("AutoReloadWSGI...")
    AutoReloadWSGI()

    # Mise à jour du répertoire Static
    logger.debug("Collectstatic...")
    call_command("collectstatic", verbosity=0, interactive=False)

    # Mise à jour de la DB
    logger.debug("Migration DB...")
    call_command("migrate")

    # Mise à jour des permissions
    logger.debug("Mise à jour des permissions...")
    call_command("update_permissions")

    logger.debug("Mise a jour terminee.")
    return True


def AutoReloadWSGI():
    """Reload le serveur en envoyant un SIGHUP à gunicorn ou en modifiant le fichier wsgi.py."""
    if (
        hasattr(settings, "GUNICORN_PIDFILE")
        and settings.GUNICORN_PIDFILE
        and os.path.isfile(settings.GUNICORN_PIDFILE)
    ):
        with open(settings.GUNICORN_PIDFILE) as pidfile:
            gunicorn_pid = int(pidfile.read())
        import signal

        logger.debug(f"Envoi de SIGHUP à {gunicorn_pid} pour reload le code")
        try:
            os.kill(gunicorn_pid, signal.SIGHUP)
        except ProcessLookupError:
            pass
        else:
            return

    nom_fichier = os.path.join(settings.BASE_DIR, "noethysweb/wsgi.py")
    # Lecture du fichier
    with open(nom_fichier, "r") as fichier_wsgi:
        liste_lignes_wsgi = fichier_wsgi.readlines()

    # Modification du fichier
    logger.debug(f"Modification de {nom_fichier} pour que l'autoreload du serveur reload le code")
    with codecs.open(nom_fichier, "w") as fichier_wsgi:
        for ligne in liste_lignes_wsgi:
            if ligne.startswith("# lastupdate"):
                ligne = "# lastupdate = %s" % datetime.datetime.now()
            fichier_wsgi.write(ligne)


if __name__ == '__main__':
    Update()
