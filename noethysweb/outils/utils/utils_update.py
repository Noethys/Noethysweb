# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, datetime, codecs, zipfile, requests
logger = logging.getLogger(__name__)
from urllib.request import urlopen, urlretrieve
from noethysweb import version
from django.core.management import call_command
from django.conf import settings
from django.core.cache import cache


def Get_update_for_accueil(request=None):
    """ Recherche si une nouvelle version est disponible """
    key_cache = "last_check_update_user%d" % request.user.pk
    last_check_update = cache.get(key_cache)
    if last_check_update:
        nouvelle_version = last_check_update["nouvelle_version"]
        # Si la dernière recherche date de plus d'un jour, on cherche une nouvelle version
        if datetime.now().time() > last_check_update["date"].time():
            last_check_update = None
    if not last_check_update:
        logger.debug("Recherche d'une nouvelle version...")
        nouvelle_version, changelog = Recherche_update()
        cache.set(key_cache, {"date": datetime.datetime.now(), "nouvelle_version": nouvelle_version})
    return nouvelle_version


def Recherche_update():
    # Lecture de la version disponible en ligne
    url = "https://raw.githubusercontent.com/Arthur67190/Noethysweb/master/noethysweb/versions.txt"

    # Ancienne version avec urlopen
    # fichier = urlopen(url, timeout=5)
    # changelog = fichier.read().decode('utf-8')
    # fichier.close()

    # Nouvelle version avec requests
    try:
        data = requests.get(url)
    except:
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


def Update():
    # Recherche une version disponible
    version_online_txt, changelog = Recherche_update()
    if not version_online_txt:
        return False

    # Téléchargement du zip
    nom_fichier = "Noethysweb-%s.zip" % version_online_txt
    if not os.path.isdir(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    rep_temp = settings.MEDIA_ROOT + "/temp"
    if not os.path.isdir(rep_temp):
        os.mkdir(rep_temp)
    chemin_fichier = os.path.join(rep_temp, nom_fichier)
    try:
        logger.debug("Telechargement de la version %s..." % version_online_txt)
        url_telechargement = "https://github.com/Arthur67190/Noethysweb/archive/%s.zip" % version_online_txt
        urlretrieve(url_telechargement, chemin_fichier)
    except Exception as err:
        logger.debug("La nouvelle version '%s' n'a pas pu etre telechargee." % version_online_txt)
        logger.debug(err)
        return False

    # Dezippage
    logger.debug("Dezippage du zip...")
    zfile = zipfile.ZipFile(chemin_fichier, 'r')
    liste_fichiers = zfile.namelist()

    # Remplacement des fichiers
    prefixe = "Noethysweb-%s/noethysweb/" % version_online_txt
    chemin_dest = os.path.join(settings.BASE_DIR, "")

    logger.debug("Installation des nouveaux fichiers...")
    for i in liste_fichiers:
        d = i.replace(prefixe, "")
        if len(d) > 1 and not d.startswith("Noethysweb-%s" % version_online_txt):
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
    nom_fichier = os.path.join(settings.BASE_DIR, "noethysweb/wsgi.py")

    # Ouverture du fichier
    fichier_wsgi = open(nom_fichier, "r")
    liste_lignes_wsgi = fichier_wsgi.readlines()
    fichier_wsgi.close()

    # Modification du fichier
    fichier_wsgi = codecs.open(nom_fichier, 'w')
    for ligne in liste_lignes_wsgi:
        if "lastupdate" in ligne:
            ligne = "# lastupdate = %s" % datetime.datetime.now()
        fichier_wsgi.write(ligne)
    fichier_wsgi.close()


if __name__ == '__main__':
    Update()
