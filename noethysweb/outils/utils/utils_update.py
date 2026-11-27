# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, datetime, codecs, zipfile, requests, shutil
logger = logging.getLogger(__name__)
from urllib.request import urlopen, urlretrieve
from noethysweb import version
from django.core.management import call_command
from django.conf import settings
from django.core.cache import cache

# Répertoires remplacés intégralement à chaque mise à jour : les fichiers qui n'existent plus
# dans la nouvelle version (anciennes librairies JS, etc.) sont ainsi supprimés.
REPERTOIRES_REMPLACES = ("core/static/lib/",)

# Catégorie des paramètres utilisateur liés à la mise à jour
CATEGORIE_PARAMETRES = "update"


def Get_update_for_accueil(request=None):
    """ Recherche si une nouvelle version est disponible """
    alerte = Get_alerte_accueil(request=request, tenir_compte_masquage=False)
    return alerte["version_disponible"] if alerte else False


def Get_alerte_accueil(request=None, tenir_compte_masquage=True):
    """ Renvoie les informations de l'encart de mise à jour de la page d'accueil (ou None) """
    # Masquage demandé par l'utilisateur pour la journée
    if tenir_compte_masquage:
        from core.utils import utils_parametres
        if utils_parametres.Get(nom="masquer_alerte_jusqu", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur="") == str(datetime.date.today()):
            return None

    # Recherche d'une nouvelle version (une fois par jour et par utilisateur)
    key_cache = "last_check_update_user%d" % request.user.pk
    last_check_update = cache.get(key_cache)
    if last_check_update and ("versions" not in last_check_update or datetime.date.today() > last_check_update["date"].date()):
        last_check_update = None
    if not last_check_update:
        logger.debug("Recherche d'une nouvelle version...")
        nouvelle_version, changelog = Recherche_update()
        versions = []
        if nouvelle_version:
            liste_versions = Analyser_changelog(changelog, version_mini=version.GetVersion())[0]
            versions = [(dict_version["version"], [changement["categorie"] for changement in dict_version["changements"]]) for dict_version in liste_versions]
        last_check_update = {"date": datetime.datetime.now(), "nouvelle_version": nouvelle_version, "versions": versions}
        cache.set(key_cache, last_check_update)

    # Si la version trouvée a été installée depuis la dernière recherche, on n'affiche plus l'alerte
    version_installee = version.GetVersion()
    try:
        tuple_installee = version.GetVersionTuple(version_installee)
        versions = [(num_version, categories) for num_version, categories in last_check_update["versions"] if version.GetVersionTuple(num_version) > tuple_installee]
    except Exception:
        return None
    if not last_check_update["nouvelle_version"] or not versions:
        return None

    # Totaux des changements depuis la version installée
    totaux = {"nouveaute": 0, "amelioration": 0, "correction": 0, "autre": 0}
    for num_version, categories in versions:
        for categorie in categories:
            totaux[categorie] += 1
    return {"version_disponible": last_check_update["nouvelle_version"], "version_installee": version_installee, "nbre_versions": len(versions), "totaux": totaux}


def Masquer_alerte_accueil(request=None):
    """ Masque l'encart de mise à jour de la page d'accueil jusqu'au lendemain """
    from core.utils import utils_parametres
    utils_parametres.Set(nom="masquer_alerte_jusqu", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur=str(datetime.date.today()))


def Recherche_update():
    # Lecture de la version disponible en ligne
    url = "https://raw.githubusercontent.com/Noethys/Noethysweb/master/noethysweb/versions.txt"

    # Ancienne version avec urlopen
    # fichier = urlopen(url, timeout=5)
    # changelog = fichier.read().decode('utf-8')
    # fichier.close()

    # Nouvelle version avec requests
    try:
        data = requests.get(url, timeout=10)
        data.raise_for_status()
    except:
        logger.debug("Le fichier des versions n'a pas pu être téléchargé sur Github.")
        return False, False
    changelog = data.text

    # Lecture du numéro de version online
    pos_debut_numVersion = changelog.find("n")
    pos_fin_numVersion = changelog.find("(")
    version_online_txt = changelog[pos_debut_numVersion + 1:pos_fin_numVersion].strip()
    try:
        version_online_tuple = version.GetVersionTuple(version_online_txt)
    except:
        logger.debug("Erreur dans la recherche d'une nouvelle version")
        return False, changelog
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


CATEGORIES_CHANGELOG = {"Nouveautés": "nouveaute", "Améliorations": "amelioration", "Corrections": "correction"}


def Analyser_changelog(changelog="", version_mini=None, nbre_versions=None):
    """ Découpe le fichier des versions en liste de versions, chacune avec ses changements classés par catégorie.
        version_mini : si renseignée, seules les versions strictement supérieures sont renvoyées.
        nbre_versions : si renseigné, nombre maximal de versions renvoyées (les plus récentes). """
    tuple_mini = version.GetVersionTuple(version_mini) if version_mini else None
    liste_versions = []
    version_courante, categorie = None, "autre"
    for ligne in (changelog or "").splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        if ligne.startswith("Version "):
            # Nouvelle version : "Version 1.3.7.2 (26/11/2026) :"
            num_version = ligne[len("Version "):ligne.find("(")].strip() if "(" in ligne else ligne[len("Version "):].strip(" :")
            date = ligne[ligne.find("(") + 1:ligne.find(")")] if "(" in ligne and ")" in ligne else ""
            try:
                tuple_version = version.GetVersionTuple(num_version)
            except Exception:
                version_courante = None
                continue
            if (tuple_mini and tuple_version <= tuple_mini) or (nbre_versions and len(liste_versions) >= nbre_versions):
                break
            version_courante = {"version": num_version, "date": date, "changements": []}
            liste_versions.append(version_courante)
            categorie = "autre"
        elif version_courante is None:
            continue
        elif ligne in CATEGORIES_CHANGELOG:
            categorie = CATEGORIES_CHANGELOG[ligne]
        elif ligne.startswith("-"):
            texte = ligne[1:].strip()
            module = ""
            if " : " in texte:
                module, texte = texte.split(" : ", 1)
            version_courante["changements"].append({"categorie": categorie, "module": module, "texte": texte})

    # Totaux par catégorie
    totaux = {"nouveaute": 0, "amelioration": 0, "correction": 0, "autre": 0}
    for dict_version in liste_versions:
        for changement in dict_version["changements"]:
            totaux[changement["categorie"]] += 1
    return liste_versions, totaux


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
        url_telechargement = "https://github.com/Noethys/Noethysweb/archive/%s.zip" % version_online_txt
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

    # Mise de côté des répertoires remplacés intégralement (uniquement s'ils sont bien présents dans le zip).
    # Ils sont déplacés hors des répertoires static et restaurés si l'installation échoue.
    sauvegardes = []
    try:
        for index, repertoire in enumerate(REPERTOIRES_REMPLACES):
            if any(nom.startswith(prefixe + repertoire) and not nom.endswith("/") for nom in liste_fichiers):
                chemin_repertoire = os.path.join(chemin_dest, repertoire).rstrip("/")
                if os.path.isdir(chemin_repertoire):
                    chemin_sauvegarde = os.path.join(rep_temp, "ancien_repertoire_%d" % index)
                    shutil.rmtree(chemin_sauvegarde, ignore_errors=True)
                    logger.debug("Mise de cote du repertoire %s..." % repertoire)
                    shutil.move(chemin_repertoire, chemin_sauvegarde)
                    sauvegardes.append((chemin_repertoire, chemin_sauvegarde))
    except Exception as err:
        logger.error("Impossible de mettre de cote les anciens repertoires : %s" % err)
        Restaurer_repertoires(sauvegardes)
        zfile.close()
        os.remove(chemin_fichier)
        return False

    try:
        Installer_fichiers(zfile, liste_fichiers, prefixe, chemin_dest, version_online_txt)
    except Exception as err:
        logger.error("Erreur lors de l'installation des nouveaux fichiers : %s" % err)
        Restaurer_repertoires(sauvegardes)
        zfile.close()
        os.remove(chemin_fichier)
        return False

    # Installation réussie : suppression des anciens répertoires mis de côté
    for chemin_repertoire, chemin_sauvegarde in sauvegardes:
        shutil.rmtree(chemin_sauvegarde, ignore_errors=True)

    zfile.close()
    os.remove(chemin_fichier)
    logger.debug("Installation terminee.")

    # Efface le numéro de version du cache
    cache.delete('version_application')

    # Important : le rechargement WSGI doit être la DERNIERE étape. Modifier wsgi.py redémarre le
    # processus mod_wsgi qui exécute cette mise à jour : s'il est fait avant les migrations, celles-ci
    # sont interrompues en cours de route. Sous MySQL/MariaDB, les créations de tables ne sont pas
    # annulées : la base reste alors dans un état intermédiaire (migration à moitié appliquée).
    resultat = True

    # Mise à jour du répertoire Static
    logger.debug("Collectstatic...")
    try:
        # clear=True : vide le répertoire STATIC_ROOT avant la copie pour supprimer les fichiers obsolètes
        call_command("collectstatic", verbosity=0, interactive=False, clear=True)
    except Exception:
        logger.exception("Erreur lors du collectstatic")
        resultat = False

    # Mise à jour de la DB
    logger.debug("Migration DB...")
    try:
        call_command("migrate", interactive=False)
    except Exception:
        logger.exception("Erreur lors de la migration de la base de donnees : lancez 'python3 manage.py migrate' pour voir le detail")
        resultat = False

    # Mise à jour des permissions
    if resultat:
        logger.debug("Mise à jour des permissions...")
        try:
            call_command("update_permissions")
        except Exception:
            logger.exception("Erreur lors de la mise a jour des permissions")
            resultat = False

    # AutoReloadWSGI : toujours en dernier
    logger.debug("AutoReloadWSGI...")
    AutoReloadWSGI()

    logger.debug("Mise a jour terminee." if resultat else "Mise a jour terminee avec des erreurs.")
    return resultat


def Installer_fichiers(zfile=None, liste_fichiers=[], prefixe="", chemin_dest="", version_online_txt=""):
    """ Copie les fichiers du zip dans le répertoire de l'application """
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



def Restaurer_repertoires(sauvegardes=[]):
    """ Remet en place les répertoires mis de côté si l'installation a échoué """
    for chemin_repertoire, chemin_sauvegarde in sauvegardes:
        try:
            shutil.rmtree(chemin_repertoire, ignore_errors=True)
            shutil.move(chemin_sauvegarde, chemin_repertoire)
            logger.debug("Repertoire %s restaure." % chemin_repertoire)
        except Exception as err:
            logger.error("Impossible de restaurer le repertoire %s : %s" % (chemin_repertoire, err))


def AutoReloadWSGI():
    nom_fichier = os.path.join(settings.BASE_DIR, "noethysweb/wsgi.py")

    # Ouverture du fichier
    fichier_wsgi = open(nom_fichier, "r")
    liste_lignes_wsgi = fichier_wsgi.readlines()
    fichier_wsgi.close()

    # Modification du fichier
    fichier_wsgi = codecs.open(nom_fichier, encoding='utf-8', mode='w')
    for ligne in liste_lignes_wsgi:
        if "lastupdate" in ligne:
            ligne = "# lastupdate = %s" % datetime.datetime.now()
        fichier_wsgi.write(ligne)
    fichier_wsgi.close()


if __name__ == '__main__':
    Update()
