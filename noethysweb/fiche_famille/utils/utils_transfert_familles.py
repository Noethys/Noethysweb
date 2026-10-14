# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Export et import de fiches familles (avec leurs fiches individuelles) entre deux bases Noethysweb.

Format : archive 7z chiffrée AES-256 (mot de passe obligatoire) contenant :
    - manifeste.json : format, version, origine, date
    - familles.json : familles, individus, enregistrements liés et paramètres utilisés
    - fichiers/ : photos et documents

Les champs chiffrés en base sont exportés déchiffrés (chaque base a sa propre clé) : c'est pourquoi
l'archive est obligatoirement protégée par un mot de passe.

Ne sont pas transférés : inscriptions, consommations, prestations, factures, règlements, mandats,
comptes du portail et historique.
"""

import base64, datetime, hashlib, io, json, logging, os, stat, tempfile, time, unicodedata, uuid
import py7zr
from cryptography.fernet import Fernet, InvalidToken
from PIL import Image
from django.conf import settings
from django.apps import apps
from django.core.files.base import ContentFile
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from core.models import Famille, Individu, Rattachement, Utilisateur, QuestionnaireReponse, Organisateur
from core.utils import utils_questionnaires
from fiche_famille.utils import utils_internet

logger = logging.getLogger(__name__)

FORMAT = "noethysweb-familles"
VERSION_FORMAT = 1
MDP_LONGUEUR_MIN = 12
TAILLE_MAX_ENVOI = 200 * 1024 * 1024  # Taille maximale du fichier envoyé
TAILLE_MAX_ARCHIVE = 500 * 1024 * 1024  # Taille maximale du contenu décompressé
NBRE_MAX_FICHIERS = 20000

# Extensions acceptées à l'import (aucun fichier interprétable par le navigateur : html, svg, js...)
EXTENSIONS_IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
EXTENSIONS_DOCUMENTS = EXTENSIONS_IMAGES | {".pdf", ".doc", ".docx", ".odt", ".xls", ".xlsx", ".ods", ".txt", ".rtf"}
DUREE_VIE_FICHIER_TEMP = 3600  # secondes
REP_TEMP = os.path.join(tempfile.gettempdir(), "noethysweb_import_familles")

# Paramètres (tables de référence) : clés utilisées pour retrouver l'équivalent dans la base cible
REFERENCES = {
    "Regime": ["nom"],
    "Caisse": ["nom"],
    "Secteur": ["nom"],
    "CategorieTravail": ["nom"],
    "Medecin": ["nom", "prenom"],
    "TypeSieste": ["nom"],
    "ListeDiffusion": ["nom"],
    "RegimeAlimentaire": ["nom"],
    "TypeMaladie": ["nom"],
    "TypeQuotient": ["nom"],
    "Ecole": ["nom"],
    "NiveauScolaire": ["nom"],
    "Classe": ["ecole", "nom", "date_debut", "date_fin"],
    "CategorieInformation": ["nom"],
    "TypeVaccin": ["nom"],
    "Assureur": ["nom"],
    "TypePiece": ["nom"],
    "QuestionnaireGroupe": ["categorie", "nom"],
    "QuestionnaireQuestion": ["categorie", "label"],
    "QuestionnaireChoix": ["question", "label"],
}

# Ordre de traitement des paramètres (un paramètre est traité après ceux dont il dépend)
ORDRE_REFERENCES = ["Regime", "Caisse", "Secteur", "CategorieTravail", "Medecin", "TypeSieste", "ListeDiffusion", "RegimeAlimentaire",
                    "TypeMaladie", "TypeQuotient", "Ecole", "NiveauScolaire", "Classe", "CategorieInformation", "TypeVaccin", "Assureur",
                    "TypePiece", "QuestionnaireGroupe", "QuestionnaireQuestion", "QuestionnaireChoix"]

# Décision par défaut pour un paramètre absent de la base cible
DECISION_DEFAUT = {"TypePiece": "ignorer", "QuestionnaireQuestion": "ignorer"}

LABELS_REFERENCES = {
    "Regime": "Régime social", "Caisse": "Caisse", "Secteur": "Secteur", "CategorieTravail": "Catégorie socio-pro.", "Medecin": "Médecin",
    "TypeSieste": "Type de sieste", "ListeDiffusion": "Liste de diffusion", "RegimeAlimentaire": "Régime alimentaire", "TypeMaladie": "Maladie",
    "TypeQuotient": "Type de quotient", "Ecole": "École", "NiveauScolaire": "Niveau scolaire", "Classe": "Classe",
    "CategorieInformation": "Catégorie d'information", "TypeVaccin": "Vaccin", "Assureur": "Assureur", "TypePiece": "Type de pièce",
    "QuestionnaireGroupe": "Groupe de questions", "QuestionnaireQuestion": "Question", "QuestionnaireChoix": "Choix de question",
}

# Enregistrements liés aux familles et aux individus, dans l'ordre d'import
ENREGISTREMENTS = ["Rattachement", "Lien", "Quotient", "Scolarite", "Information", "Vaccin", "ContactUrgence", "Assurance", "Piece", "QuestionnaireReponse"]

# Libellés du rapport pour les enregistrements non importés faute de paramètre
MOTIFS_IGNORES = {
    "QuestionnaireReponse": "réponses à des questions non importées",
    "Piece": "pièces d'un type non importé",
    "Quotient": "quotients d'un type non importé",
    "Scolarite": "étapes de scolarité d'une école non importée",
    "Vaccin": "vaccins d'un type non importé",
    "Information": "informations personnelles d'une catégorie non importée",
    "Assurance": "assurances d'un assureur non importé",
}

# Champs jamais transférés (comptes du portail, données propres à la base d'origine)
CHAMPS_EXCLUS = {
    "Famille": {"utilisateur", "internet_actif", "internet_identifiant", "internet_mdp", "internet_secquest", "internet_categorie",
                "internet_reservations", "certification_date"},
    "Rattachement": {"certification_date"},
    "Piece": {"auteur"},
    "QuestionnaireReponse": {"collaborateur"},
    "TypePiece": {"structure"},
    "QuestionnaireQuestion": {"structure"},
}

# Champs entiers qui contiennent un ID d'individu
CHAMPS_ID_INDIVIDU = {"Individu": {"adresse_auto"}}


def Normaliser(valeur):
    """ Pour comparer des textes sans tenir compte de la casse, des accents et des espaces """
    if isinstance(valeur, str):
        texte = unicodedata.normalize("NFKD", valeur).encode("ascii", "ignore").decode("ascii")
        return " ".join(texte.upper().split())
    return valeur


def Date_fr(texte="", heure=False):
    """ '2026-10-14' ou '2026-10-14T15:35:00' -> '14/10/2026' (ou '14/10/2026 15:35') """
    if not texte:
        return ""
    try:
        valeur = datetime.datetime.fromisoformat(texte)
    except ValueError:
        return texte
    return valeur.strftime("%d/%m/%Y %H:%M" if heure else "%d/%m/%Y")


def Champs_simples(modele):
    """ Champs exportés par le Serialiseur pour ce modèle (cache par modèle) """
    if modele not in _CACHE_CHAMPS:
        exclus = CHAMPS_EXCLUS.get(modele.__name__, set()) | CHAMPS_ID_INDIVIDU.get(modele.__name__, set())
        _CACHE_CHAMPS[modele] = {
            champ.name: champ for champ in modele._meta.get_fields()
            if champ.concrete and not champ.primary_key and not champ.is_relation and not isinstance(champ, models.FileField)
            and not getattr(champ, "auto_now", False) and not getattr(champ, "auto_now_add", False) and champ.name not in exclus
        }
    return _CACHE_CHAMPS[modele]

_CACHE_CHAMPS = {}


def Image_valide(contenu=b""):
    try:
        with Image.open(io.BytesIO(contenu)) as image:
            image.verify()
        return True
    except Exception:
        return False


def Get_modele(nom):
    return apps.get_model("core", nom)


class Erreur_transfert(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------------------------
#                                                     SÉRIALISATION
# ----------------------------------------------------------------------------------------------------------------------------

class Serialiseur():
    """ Transforme un objet en dictionnaire JSON, en remplaçant les relations par des références portables """

    def __init__(self, fichiers=None):
        self.fichiers = fichiers if fichiers is not None else {}  # chemin dans l'archive -> champ fichier
        self.references = {}  # "Modele:id" -> données du paramètre

    def Ajouter_reference(self, objet):
        if objet is None:
            return None
        cle = "%s:%d" % (type(objet).__name__, objet.pk)
        if cle not in self.references:
            self.references[cle] = None  # Réserve la clé (évite les boucles)
            self.references[cle] = self.Serialiser(objet)
        return cle

    def Serialiser(self, objet):
        nom_modele = type(objet).__name__
        exclus = CHAMPS_EXCLUS.get(nom_modele, set())
        resultat = {"champs": {}, "refs": {}, "familles": {}, "individus": {}, "fichiers": {}, "m2m": {}}
        for champ in objet._meta.get_fields():
            if not champ.concrete or champ.primary_key or champ.name in exclus:
                continue
            if getattr(champ, "auto_now", False) or getattr(champ, "auto_now_add", False):
                continue

            if champ.many_to_many:
                if champ.related_model is Individu:
                    resultat["individus"][champ.name] = [i.pk for i in getattr(objet, champ.name).all()]
                elif champ.related_model.__name__ in REFERENCES:
                    resultat["m2m"][champ.name] = [self.Ajouter_reference(r) for r in getattr(objet, champ.name).all()]
                continue

            if champ.is_relation:
                id_lie = getattr(objet, champ.attname)
                if champ.related_model is Famille:
                    resultat["familles"][champ.name] = id_lie
                elif champ.related_model is Individu:
                    resultat["individus"][champ.name] = id_lie
                elif champ.related_model.__name__ in REFERENCES:
                    resultat["refs"][champ.name] = self.Ajouter_reference(getattr(objet, champ.name)) if id_lie else None
                continue

            if isinstance(champ, models.FileField):
                fichier = getattr(objet, champ.name)
                if fichier and fichier.name:
                    chemin = "fichiers/%s%s" % (uuid.uuid4().hex, os.path.splitext(fichier.name)[1].lower()[:10])
                    self.fichiers[chemin] = fichier
                    resultat["fichiers"][champ.name] = chemin
                continue

            if champ.name in CHAMPS_ID_INDIVIDU.get(nom_modele, set()):
                resultat["individus"][champ.name] = getattr(objet, champ.attname)
                continue

            resultat["champs"][champ.name] = champ.value_from_object(objet)
        return resultat


def Exporter(idfamilles=[], mot_de_passe="", utilisateur=None):
    """ Génère l'archive chiffrée des familles demandées. Renvoie (contenu binaire, statistiques) """
    if not mot_de_passe or len(mot_de_passe) < MDP_LONGUEUR_MIN:
        raise Erreur_transfert("Le mot de passe doit contenir au moins %d caractères." % MDP_LONGUEUR_MIN)

    familles = list(Famille.objects.filter(pk__in=idfamilles).order_by("pk"))
    if not familles:
        raise Erreur_transfert("Aucune famille à exporter.")
    ids_familles = {famille.pk for famille in familles}

    # Individus rattachés aux familles exportées
    ids_individus = set(Rattachement.objects.filter(famille_id__in=ids_familles, individu__isnull=False).values_list("individu_id", flat=True))

    serialiseur = Serialiseur()
    donnees = {"familles": {}, "individus": {}, "enregistrements": {}}
    for famille in familles:
        donnees["familles"][str(famille.pk)] = serialiseur.Serialiser(famille)
    for individu in Individu.objects.filter(pk__in=ids_individus).prefetch_related("listes_diffusion", "regimes_alimentaires", "maladies"):
        donnees["individus"][str(individu.pk)] = serialiseur.Serialiser(individu)

    # Enregistrements liés : rattachés à une famille ou à un individu exporté
    for nom_modele in ENREGISTREMENTS:
        modele = Get_modele(nom_modele)
        condition = models.Q()
        for champ in modele._meta.get_fields():
            if champ.concrete and champ.many_to_one and champ.related_model is Famille:
                condition |= models.Q(**{"%s__in" % champ.attname: ids_familles})
            if champ.concrete and champ.many_to_one and champ.related_model is Individu:
                condition |= models.Q(**{"%s__in" % champ.attname: ids_individus})
        if nom_modele == "QuestionnaireReponse":
            condition &= models.Q(collaborateur__isnull=True)
        donnees["enregistrements"][nom_modele] = [serialiseur.Serialiser(objet) for objet in modele.objects.filter(condition).order_by("pk")]

    donnees["references"] = serialiseur.references

    organisateur = Organisateur.objects.first()
    from noethysweb.version import GetVersion
    manifeste = {
        "format": FORMAT, "version": VERSION_FORMAT, "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "origine": organisateur.nom if organisateur else "", "version_noethysweb": GetVersion(),
        "nbre_familles": len(donnees["familles"]), "nbre_individus": len(donnees["individus"]),
        "utilisateur": str(utilisateur) if utilisateur else "",
    }

    # Création de l'archive chiffrée
    tampon = io.BytesIO()
    nbre_fichiers, fichiers_manquants = 0, 0
    with py7zr.SevenZipFile(tampon, "w", password=mot_de_passe, header_encryption=True) as archive:
        archive.writestr(json.dumps(manifeste, cls=DjangoJSONEncoder, ensure_ascii=False, indent=1).encode("utf-8"), "manifeste.json")
        archive.writestr(json.dumps(donnees, cls=DjangoJSONEncoder, ensure_ascii=False).encode("utf-8"), "familles.json")
        for chemin, fichier in serialiseur.fichiers.items():
            try:
                with fichier.storage.open(fichier.name, "rb") as f:
                    archive.writestr(f.read(), chemin)
                nbre_fichiers += 1
            except Exception as err:
                logger.warning("Export familles : fichier %s introuvable (%s)" % (fichier.name, err))
                fichiers_manquants += 1

    return tampon.getvalue(), {"familles": len(donnees["familles"]), "individus": len(donnees["individus"]),
                               "fichiers": nbre_fichiers, "fichiers_manquants": fichiers_manquants}


# ----------------------------------------------------------------------------------------------------------------------------
#                                                     LECTURE DE L'ARCHIVE
# ----------------------------------------------------------------------------------------------------------------------------

def Purger_fichiers_temp():
    """ Supprime les archives d'import abandonnées """
    if not os.path.isdir(REP_TEMP):
        return
    limite = time.time() - DUREE_VIE_FICHIER_TEMP
    for nom in os.listdir(REP_TEMP):
        chemin = os.path.join(REP_TEMP, nom)
        try:
            if os.path.getmtime(chemin) < limite:
                os.remove(chemin)
        except OSError:
            pass


def Get_fernet():
    cle = hashlib.sha256(("noethysweb-import-familles:" + settings.SECRET_KEY).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(cle))


def Chiffrer_mdp(mot_de_passe=""):
    """ Le mot de passe de l'archive n'est jamais conservé en clair dans la session (stockée en base) """
    return Get_fernet().encrypt(mot_de_passe.encode("utf-8")).decode("ascii")


def Dechiffrer_mdp(jeton=""):
    try:
        return Get_fernet().decrypt(jeton.encode("ascii"), ttl=DUREE_VIE_FICHIER_TEMP).decode("utf-8")
    except (InvalidToken, ValueError, AttributeError):
        raise Erreur_transfert("L'import a expiré. Veuillez recommencer l'import.")


def Get_rep_temp():
    """ Répertoire privé des archives en attente : refusé s'il a été créé par un autre utilisateur système """
    os.makedirs(REP_TEMP, mode=0o700, exist_ok=True)
    infos = os.lstat(REP_TEMP)
    if not stat.S_ISDIR(infos.st_mode) or infos.st_uid != os.getuid() or stat.S_IMODE(infos.st_mode) & 0o077:
        raise Erreur_transfert("Le répertoire temporaire d'import n'est pas sûr (%s). Contactez l'administrateur." % REP_TEMP)
    return REP_TEMP


def Enregistrer_fichier_temp(fichier_envoye):
    """ Mémorise l'archive envoyée (toujours chiffrée) le temps de l'analyse. Renvoie un jeton """
    if fichier_envoye.size > TAILLE_MAX_ENVOI:
        raise Erreur_transfert("Le fichier dépasse la taille maximale autorisée (%d Mo)." % (TAILLE_MAX_ENVOI // 1024 // 1024))
    Purger_fichiers_temp()
    rep = Get_rep_temp()
    jeton = uuid.uuid4().hex
    descripteur = os.open(os.path.join(rep, jeton + ".7z"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descripteur, "wb") as f:
        for morceau in fichier_envoye.chunks():
            f.write(morceau)
    return jeton


def Get_chemin_temp(jeton=""):
    if not jeton or not jeton.isalnum():
        raise Erreur_transfert("Fichier d'import invalide.")
    chemin = os.path.join(Get_rep_temp(), jeton + ".7z")
    if not os.path.isfile(chemin) or os.path.islink(chemin):
        raise Erreur_transfert("Le fichier d'import a expiré. Veuillez recommencer l'import.")
    return chemin


def Supprimer_fichier_temp(jeton=""):
    try:
        os.remove(Get_chemin_temp(jeton))
    except (Erreur_transfert, OSError):
        pass


class Archive():
    """ Lecture d'une archive d'export """

    def __init__(self, chemin="", mot_de_passe=""):
        self.chemin = chemin
        self.mot_de_passe = mot_de_passe
        self.fichiers = {}
        try:
            with py7zr.SevenZipFile(chemin, "r", password=mot_de_passe) as archive:
                infos = archive.list()
                if len(infos) > NBRE_MAX_FICHIERS or any(info.is_symlink for info in infos):
                    raise Erreur_transfert("L'archive contient des éléments non autorisés.")
                noms = [info.filename for info in infos if not info.is_directory]
                taille = sum(info.uncompressed or 0 for info in infos)
                self.Verifier_noms(noms, taille)
                contenu = self.Lire(archive, noms)
        except Erreur_transfert:
            raise
        except Exception as err:
            logger.info("Import familles : lecture impossible (%s)" % err)
            raise Erreur_transfert("Impossible d'ouvrir l'archive : le mot de passe est incorrect ou le fichier n'est pas un export Noethysweb.")

        try:
            self.manifeste = json.loads(contenu.pop("manifeste.json").decode("utf-8"))
            self.donnees = json.loads(contenu.pop("familles.json").decode("utf-8"))
        except (KeyError, ValueError):
            raise Erreur_transfert("Le fichier n'est pas un export de fiches familles Noethysweb.")
        if self.manifeste.get("format") != FORMAT:
            raise Erreur_transfert("Le fichier n'est pas un export de fiches familles Noethysweb.")
        if self.manifeste.get("version", 0) > VERSION_FORMAT:
            raise Erreur_transfert("Ce fichier a été créé par une version plus récente de Noethysweb. Mettez à jour cette base avant de l'importer.")
        self.fichiers = contenu

    def Verifier_noms(self, noms=[], taille=0):
        if taille > TAILLE_MAX_ARCHIVE:
            raise Erreur_transfert("L'archive est trop volumineuse.")
        for nom in noms:
            if nom in ("manifeste.json", "familles.json"):
                continue
            # Uniquement des fichiers à plat dans 'fichiers/', sans chemin relatif
            if not nom.startswith("fichiers/") or "/" in nom[9:] or "\\" in nom or ".." in nom or not nom[9:]:
                raise Erreur_transfert("L'archive contient un fichier inattendu : %s" % nom)

    def Lire(self, archive, noms=[]):
        """ Extrait le contenu en mémoire via un répertoire temporaire privé """
        with tempfile.TemporaryDirectory(prefix="noethysweb_") as rep:
            archive.extractall(path=rep)
            contenu = {}
            for nom in noms:
                chemin = os.path.join(rep, nom)
                if os.path.islink(chemin) or not os.path.isfile(chemin):
                    raise Erreur_transfert("L'archive contient des éléments non autorisés.")
                with open(chemin, "rb") as f:
                    contenu[nom] = f.read()
        return contenu


# ----------------------------------------------------------------------------------------------------------------------------
#                                                     ANALYSE
# ----------------------------------------------------------------------------------------------------------------------------

class Analyse():
    """ Analyse d'une archive : familles, doublons et correspondances des paramètres avec la base cible """

    def __init__(self, archive=None):
        self.archive = archive
        self.donnees = archive.donnees
        self.references = self.donnees.get("references", {})
        self.Calculer_correspondances()
        self.Calculer_utilisations()
        self.Calculer_doublons()

    # --- Paramètres ---

    def Cle_naturelle(self, cle_ref, correspondances):
        """ Clé de recherche d'un paramètre dans la base cible (None si un paramètre parent n'a pas d'équivalent) """
        nom_modele = cle_ref.split(":")[0]
        modele = Get_modele(nom_modele)
        donnees = self.references[cle_ref]
        valeurs = []
        for nom_champ in REFERENCES[nom_modele]:
            if nom_champ in donnees["refs"]:
                parent = donnees["refs"][nom_champ]
                if parent and not correspondances.get(parent):
                    return None
                valeurs.append(correspondances.get(parent) if parent else None)
            else:
                valeur = donnees["champs"].get(nom_champ)
                valeurs.append(Normaliser(modele._meta.get_field(nom_champ).to_python(valeur) if valeur is not None else None))
        return tuple(valeurs)

    def Index_cible(self, nom_modele):
        """ Index des objets de la base cible selon leur clé naturelle """
        modele = Get_modele(nom_modele)
        champs_cle = REFERENCES[nom_modele]
        index = {}
        for objet in modele.objects.all():
            valeurs = []
            for nom_champ in champs_cle:
                champ = modele._meta.get_field(nom_champ)
                valeurs.append(getattr(objet, champ.attname) if champ.is_relation else Normaliser(champ.value_from_object(objet)))
            index.setdefault(tuple(valeurs), objet.pk)
        return index

    def Calculer_correspondances(self):
        """ Recherche automatique de l'équivalent de chaque paramètre dans la base cible """
        self.correspondances = {}  # cle_ref -> pk cible (ou None)
        for nom_modele in ORDRE_REFERENCES:
            cles = [cle for cle in self.references if cle.split(":")[0] == nom_modele]
            if not cles:
                continue
            index = self.Index_cible(nom_modele)
            for cle in cles:
                cle_naturelle = self.Cle_naturelle(cle, self.correspondances)
                self.correspondances[cle] = index.get(cle_naturelle) if cle_naturelle is not None else None

    def Get_label_reference(self, cle_ref):
        nom_modele = cle_ref.split(":")[0]
        donnees = self.references[cle_ref]
        champs = donnees["champs"]
        if nom_modele == "Medecin":
            return " ".join(x for x in (champs.get("nom"), champs.get("prenom")) if x)
        if nom_modele == "Classe":
            ecole = self.references.get(donnees["refs"].get("ecole") or "", {}) or {}
            return "%s (%s)" % (champs.get("nom"), ecole.get("champs", {}).get("nom", ""))
        if nom_modele == "QuestionnaireChoix":
            question = self.references.get(donnees["refs"].get("question") or "", {}) or {}
            return "%s : %s" % (question.get("champs", {}).get("label", ""), champs.get("label"))
        return str(champs.get("label") or champs.get("nom") or cle_ref)

    def Parents_requis(self, cle_ref):
        """ Paramètres parents obligatoires (ex : l'école d'une classe) """
        nom_modele = cle_ref.split(":")[0]
        modele = Get_modele(nom_modele)
        parents = []
        for nom_champ, parent in self.references[cle_ref]["refs"].items():
            if parent and not modele._meta.get_field(nom_champ).null:
                parents.append(parent)
        return parents

    # --- Utilisation des paramètres par famille ---

    def Refs_objet(self, donnees_objet):
        refs = {cle for cle in donnees_objet["refs"].values() if cle}
        for liste in donnees_objet["m2m"].values():
            refs.update(cle for cle in liste if cle)
        return refs

    def Fermeture_refs(self, refs):
        """ Ajoute les paramètres parents (une classe utilise une école, une caisse un régime...) """
        resultat, a_traiter = set(), list(refs)
        while a_traiter:
            cle = a_traiter.pop()
            if cle in resultat or cle not in self.references:
                continue
            resultat.add(cle)
            a_traiter.extend(self.Refs_objet(self.references[cle]))
        return resultat

    def Calculer_utilisations(self):
        """ Membres et paramètres utilisés par chaque famille """
        self.membres = {idf: [] for idf in self.donnees["familles"]}  # idfamille -> [idindividu]
        self.familles_individu = {}  # idindividu -> [idfamille]
        for enreg in self.donnees["enregistrements"].get("Rattachement", []):
            idf, idi = enreg["familles"].get("famille"), enreg["individus"].get("individu")
            if idf is not None and idi is not None and str(idf) in self.membres and str(idi) in self.donnees["individus"]:
                if str(idi) not in self.membres[str(idf)]:
                    self.membres[str(idf)].append(str(idi))
                self.familles_individu.setdefault(str(idi), []).append(str(idf))

        refs_individu = {idi: self.Refs_objet(d) for idi, d in self.donnees["individus"].items()}
        refs_famille = {idf: self.Refs_objet(d) for idf, d in self.donnees["familles"].items()}
        for nom_modele, enregistrements in self.donnees["enregistrements"].items():
            for enreg in enregistrements:
                refs = self.Refs_objet(enreg)
                for idf in enreg["familles"].values():
                    if idf is not None and str(idf) in refs_famille:
                        refs_famille[str(idf)].update(refs)
                for idi in enreg["individus"].values():
                    if isinstance(idi, int) and str(idi) in refs_individu:
                        refs_individu[str(idi)].update(refs)

        self.utilisations = {}  # cle_ref -> set(idfamille)
        for idf, refs in refs_famille.items():
            for idi in self.membres[idf]:
                refs = refs | refs_individu.get(idi, set())
            for cle in self.Fermeture_refs(refs):
                self.utilisations.setdefault(cle, set()).add(idf)

    # --- Doublons ---

    def Calculer_doublons(self):
        """ Individus déjà présents dans la base cible (même nom, prénom et date de naissance) """
        index = {}
        for individu in Individu.objects.only("idindividu", "nom", "prenom", "date_naiss"):
            index.setdefault((Normaliser(individu.nom), Normaliser(individu.prenom), individu.date_naiss), individu.pk)

        self.doublons = {}  # idindividu source -> idindividu cible
        champ_date = Individu._meta.get_field("date_naiss")
        for idi, donnees in self.donnees["individus"].items():
            champs = donnees["champs"]
            date_naiss = champ_date.to_python(champs.get("date_naiss")) if champs.get("date_naiss") else None
            cible = index.get((Normaliser(champs.get("nom")), Normaliser(champs.get("prenom")), date_naiss))
            if cible:
                self.doublons[idi] = cible

        # Rattachement à une famille dans la base cible (pour l'affichage)
        self.familles_doublons = {}
        for idindividu, idfamille in Rattachement.objects.filter(individu_id__in=self.doublons.values()).values_list("individu_id", "famille_id"):
            self.familles_doublons.setdefault(idindividu, idfamille)

    def Famille_deja_presente(self, idf):
        membres = self.membres.get(idf, [])
        return bool(membres) and all(idi in self.doublons for idi in membres)

    # --- Contexte pour l'écran d'analyse ---

    def Get_contexte(self):
        individus = self.donnees["individus"]
        familles = []
        for idf, donnees in self.donnees["familles"].items():
            membres = self.membres[idf]
            nbre_doublons = len([idi for idi in membres if idi in self.doublons])
            if not membres:
                etat = "vide"
            elif nbre_doublons == len(membres):
                etat = "presente"
            elif nbre_doublons:
                etat = "doublons"
            else:
                etat = "nouvelle"
            familles.append({
                "id": idf, "nom": donnees["champs"].get("nom") or "Famille sans nom",
                "membres": ", ".join(individus[idi]["champs"].get("prenom") or individus[idi]["champs"].get("nom") or "" for idi in membres),
                "ville": donnees["champs"].get("ville_resid") or "", "etat": etat, "nbre_doublons": nbre_doublons,
                "coche": etat in ("nouvelle", "doublons"),
            })
        familles.sort(key=lambda f: Normaliser(f["nom"]) or "")

        doublons = []
        for idi, idcible in self.doublons.items():
            champs = individus[idi]["champs"]
            doublons.append({
                "id": idi, "nom": " ".join(x for x in (champs.get("nom"), champs.get("prenom")) if x),
                "date_naiss": Date_fr(champs.get("date_naiss")), "idfamille_cible": self.familles_doublons.get(idcible),
                "familles": self.familles_individu.get(idi, []),
            })
        doublons.sort(key=lambda d: Normaliser(d["nom"]))

        correspondances, automatiques = [], []
        for nom_modele in ORDRE_REFERENCES:
            modele = Get_modele(nom_modele)
            for cle in [c for c in self.references if c.split(":")[0] == nom_modele and c in self.utilisations]:
                ligne = {"cle": cle, "champ": "ref_%s" % cle.replace(":", "_"), "modele": LABELS_REFERENCES[nom_modele],
                         "label": self.Get_label_reference(cle), "familles": sorted(self.utilisations[cle])}
                if self.correspondances.get(cle):
                    ligne["cible"] = str(modele.objects.filter(pk=self.correspondances[cle]).first() or "")
                    automatiques.append(ligne)
                else:
                    ligne["defaut"] = DECISION_DEFAUT.get(nom_modele, "creer")
                    ligne["choix"] = [(objet.pk, str(objet)) for objet in modele.objects.all()[:300]]
                    ligne["parents"] = ["ref_%s" % p.replace(":", "_") for p in self.Parents_requis(cle)]
                    correspondances.append(ligne)

        manifeste = dict(self.archive.manifeste, date_fr=Date_fr(self.archive.manifeste.get("date"), heure=True))
        return {"manifeste": manifeste, "familles": familles, "doublons": doublons,
                "correspondances": correspondances, "correspondances_auto": automatiques,
                "nbre_fichiers": len(self.archive.fichiers)}


# ----------------------------------------------------------------------------------------------------------------------------
#                                                     IMPORT
# ----------------------------------------------------------------------------------------------------------------------------

class Importation():
    """ Import des familles sélectionnées selon les décisions de l'utilisateur """

    def __init__(self, analyse=None, familles=[], decisions_doublons={}, decisions_refs={}, utilisateur=None):
        """ decisions_doublons : {idindividu source: 'ignorer' | 'creer'}
            decisions_refs : {cle_ref: 'creer' | 'ignorer' | pk cible} """
        self.analyse = analyse
        self.donnees = analyse.donnees
        self.fichiers = analyse.archive.fichiers
        self.familles_selection = [str(idf) for idf in familles if str(idf) in self.donnees["familles"]]
        self.decisions_doublons = decisions_doublons
        self.decisions_refs = decisions_refs
        self.utilisateur = utilisateur
        self.map_refs, self.map_familles, self.map_individus = {}, {}, {}
        self.rapport = {"familles": 0, "individus": 0, "individus_ignores": 0, "parametres_crees": [], "avertissements": [], "familles_non_importees": []}
        self.compteurs_ignores = {}

    def Avertir(self, texte):
        self.rapport["avertissements"].append(texte)

    def Ignorer(self, motif):
        self.compteurs_ignores[motif] = self.compteurs_ignores.get(motif, 0) + 1

    # --- Valeurs ---

    def Valeurs(self, modele, donnees):
        """ Champs simples, convertis dans le type du champ.
            Le fichier peut avoir été modifié : seuls les champs que l'export produit sont acceptés. Une clé primaire
            injectée permettrait sinon d'écraser un enregistrement existant de cette base. """
        valeurs = {}
        champs_autorises = Champs_simples(modele)
        for nom_champ, valeur in donnees["champs"].items():
            if nom_champ not in champs_autorises:
                continue
            valeurs[nom_champ] = champs_autorises[nom_champ].to_python(valeur) if valeur is not None else None
        return valeurs

    def Resoudre_refs(self, modele, donnees, libelle=""):
        """ Renvoie (valeurs des clés étrangères, False si un paramètre obligatoire n'a pas d'équivalent) """
        valeurs, complet = {}, True
        for nom_champ, cle in donnees["refs"].items():
            try:
                champ = modele._meta.get_field(nom_champ)
            except Exception:
                continue
            cible = self.map_refs.get(cle) if cle else None
            if cle and not cible and not champ.null:
                complet = False
            valeurs[champ.attname] = cible
        return valeurs, complet

    def Fichiers(self, objet, donnees):
        for nom_champ, chemin in donnees["fichiers"].items():
            try:
                champ = objet._meta.get_field(nom_champ)
            except Exception:
                continue
            if not isinstance(champ, models.FileField) or not isinstance(chemin, str) or chemin not in self.fichiers:
                self.Ignorer("fichiers absents de l'archive")
                continue
            contenu = self.fichiers[chemin]
            extension = os.path.splitext(chemin)[1].lower()
            image = isinstance(champ, models.ImageField)
            if extension not in (EXTENSIONS_IMAGES if image else EXTENSIONS_DOCUMENTS):
                self.Ignorer("fichiers d'un type non autorisé (%s)" % (extension or "sans extension"))
                continue
            if extension in EXTENSIONS_IMAGES and not Image_valide(contenu):
                self.Ignorer("images invalides")
                continue
            getattr(objet, nom_champ).save("fichier" + extension, ContentFile(contenu), save=False)

    # --- Paramètres ---

    def Importer_references(self):
        refs_utiles = set()
        for idf in self.familles_selection:
            refs_utiles.update(cle for cle, familles in self.analyse.utilisations.items() if idf in familles)

        for nom_modele in ORDRE_REFERENCES:
            modele = Get_modele(nom_modele)
            index = None
            for cle in [c for c in self.analyse.references if c.split(":")[0] == nom_modele and c in refs_utiles]:
                donnees = self.analyse.references[cle]
                if self.analyse.correspondances.get(cle):
                    self.map_refs[cle] = self.analyse.correspondances[cle]
                    continue
                decision = self.decisions_refs.get(cle, DECISION_DEFAUT.get(nom_modele, "creer"))
                if decision == "ignorer":
                    continue
                if decision != "creer":
                    # Correspondance manuelle avec un paramètre existant
                    if str(decision).isdigit() and modele.objects.filter(pk=int(decision)).exists():
                        self.map_refs[cle] = int(decision)
                    continue

                # Création : on vérifie d'abord qu'il n'existe pas déjà (parent associé manuellement par exemple)
                if index is None:
                    index = self.analyse.Index_cible(nom_modele)
                cle_naturelle = self.analyse.Cle_naturelle(cle, {k: v for k, v in self.map_refs.items()})
                if cle_naturelle is not None and cle_naturelle in index:
                    self.map_refs[cle] = index[cle_naturelle]
                    continue
                valeurs, complet = self.Resoudre_refs(modele, donnees)
                if not complet:
                    self.Avertir("%s « %s » non créé : un paramètre dont il dépend a été ignoré." % (LABELS_REFERENCES[nom_modele], self.analyse.Get_label_reference(cle)))
                    continue
                objet = modele(**self.Valeurs(modele, donnees), **valeurs)
                objet.save()
                for nom_champ, cles in donnees["m2m"].items():
                    getattr(objet, nom_champ).set([self.map_refs[c] for c in cles if self.map_refs.get(c)])
                self.map_refs[cle] = objet.pk
                if index is not None and cle_naturelle is not None:
                    index[cle_naturelle] = objet.pk
                self.rapport["parametres_crees"].append("%s « %s »" % (LABELS_REFERENCES[nom_modele], self.analyse.Get_label_reference(cle)))

    # --- Individus et familles ---

    def Importer_individus(self):
        a_creer = []
        for idf in self.familles_selection:
            for idi in self.analyse.membres[idf]:
                if idi not in a_creer:
                    a_creer.append(idi)

        for idi in a_creer:
            if idi in self.analyse.doublons and self.decisions_doublons.get(idi, "ignorer") != "creer":
                self.rapport["individus_ignores"] += 1
                continue
            donnees = self.donnees["individus"][idi]
            refs, complet = self.Resoudre_refs(Individu, donnees)
            individu = Individu(**self.Valeurs(Individu, donnees), **refs)
            self.Fichiers(individu, donnees)
            individu.save()
            for nom_champ, cles in donnees["m2m"].items():
                getattr(individu, nom_champ).set([self.map_refs[c] for c in cles if self.map_refs.get(c)])
            self.map_individus[idi] = individu.pk
            self.rapport["individus"] += 1

        # Adresses rattachées à un autre individu
        for idi, idcible in self.map_individus.items():
            adresse_auto = self.donnees["individus"][idi]["individus"].get("adresse_auto")
            if adresse_auto:
                Individu.objects.filter(pk=idcible).update(adresse_auto=self.map_individus.get(str(adresse_auto)))

    def Creer_famille(self, donnees):
        """ Création comme dans l'application, avec un nouveau compte portail.
            Le compte est créé sans mot de passe (même état qu'après la purge des mots de passe expirés) :
            le calcul d'un mot de passe prend environ 0,5 s par famille, ce qui rendrait l'import de
            centaines de familles trop long. Les codes sont à générer ensuite depuis la liste des comptes internet. """
        refs, complet = self.Resoudre_refs(Famille, donnees)
        famille = Famille.objects.create(**self.Valeurs(Famille, donnees), **refs)
        internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=famille.pk)
        famille.internet_identifiant = internet_identifiant
        famille.internet_mdp = None
        utilisateur = Utilisateur(username=internet_identifiant, categorie="famille", force_reset_password=True)
        utilisateur.set_unusable_password()
        utilisateur.save()
        famille.utilisateur = utilisateur
        return famille

    def Importer_familles(self):
        for idf in self.familles_selection:
            donnees = self.donnees["familles"][idf]
            membres = self.analyse.membres[idf]
            if not any(idi in self.map_individus for idi in membres):
                self.rapport["familles_non_importees"].append(donnees["champs"].get("nom") or "Famille sans nom")
                continue
            famille = self.Creer_famille(donnees)
            for nom_champ, idi in donnees["individus"].items():
                if isinstance(idi, list):
                    continue
                setattr(famille, "%s_id" % nom_champ, self.map_individus.get(str(idi)) if idi else None)
            famille.save()
            self.Fichiers(famille, donnees)
            if donnees["individus"].get("individus_masques"):
                famille.individus_masques.set([self.map_individus[str(i)] for i in donnees["individus"]["individus_masques"] if str(i) in self.map_individus])
            self.map_familles[idf] = famille.pk
            self.rapport["familles"] += 1

    # --- Enregistrements liés ---

    def Importer_enregistrements(self):
        reponses = []
        for nom_modele in ENREGISTREMENTS:
            modele = Get_modele(nom_modele)
            a_creer, avec_fichiers = [], []
            for donnees in self.donnees["enregistrements"].get(nom_modele, []):
                proprietaires, valide, au_moins_un = {}, True, False
                for liens, correspondances, exportes in ((donnees["familles"], self.map_familles, self.donnees["familles"]),
                                                         (donnees["individus"], self.map_individus, self.donnees["individus"])):
                    for nom_champ, id_source in liens.items():
                        champ = modele._meta.get_field(nom_champ)
                        cible = correspondances.get(str(id_source)) if id_source is not None else None
                        if cible:
                            au_moins_un = True
                        elif id_source is not None and (str(id_source) in exportes or nom_modele in ("Rattachement", "Lien")):
                            valide = False  # Famille ou individu exporté mais non importé (non coché, doublon ignoré)
                        elif not champ.null:
                            valide = False
                        proprietaires[champ.attname] = cible
                if not valide or not au_moins_un:
                    continue  # Famille ou individu non importé (doublon ignoré, famille non cochée)

                refs, complet = self.Resoudre_refs(modele, donnees)
                if not complet:
                    self.Ignorer(MOTIFS_IGNORES.get(nom_modele, "%s dont un paramètre a été ignoré" % modele._meta.verbose_name_plural.lower()))
                    continue

                if nom_modele == "QuestionnaireReponse":
                    reponses.append((proprietaires, refs, donnees))
                    continue
                objet = modele(**self.Valeurs(modele, donnees), **proprietaires, **refs)
                if donnees["fichiers"]:
                    self.Fichiers(objet, donnees)
                    avec_fichiers.append(objet)
                else:
                    a_creer.append(objet)
            modele.objects.bulk_create(a_creer, batch_size=500)
            for objet in avec_fichiers:
                objet.save()

        # Questionnaires : réponses par défaut (comme à la création d'une fiche), puis réponses importées
        utils_questionnaires.Creation_reponses(categorie="famille", liste_instances=list(Famille.objects.filter(pk__in=self.map_familles.values())))
        utils_questionnaires.Creation_reponses(categorie="individu", liste_instances=list(Individu.objects.filter(pk__in=self.map_individus.values())))
        existantes = {}
        for reponse in QuestionnaireReponse.objects.filter(models.Q(famille_id__in=self.map_familles.values()) | models.Q(individu_id__in=self.map_individus.values())):
            existantes[(reponse.famille_id, reponse.individu_id, reponse.question_id)] = reponse
        a_modifier = []
        for proprietaires, refs, donnees in reponses:
            reponse = existantes.get((proprietaires.get("famille_id"), proprietaires.get("individu_id"), refs.get("question_id")))
            if reponse:
                reponse.reponse = donnees["champs"].get("reponse")
                reponse.choix_id = refs.get("choix_id")
                a_modifier.append(reponse)
        QuestionnaireReponse.objects.bulk_update(a_modifier, ["reponse", "choix"], batch_size=500)

    def Finaliser(self):
        """ Mise à jour du nom et de l'adresse des familles qui ont perdu des membres (doublons ignorés) """
        for idf, idcible in self.map_familles.items():
            if any(idi not in self.map_individus for idi in self.analyse.membres[idf]):
                famille = Famille.objects.get(pk=idcible)
                famille.Maj_infos(maj_code_compta=False)
        for motif, nombre in self.compteurs_ignores.items():
            self.Avertir("%d non importé(s) : %s." % (nombre, motif))
        if self.map_familles:
            self.Avertir("Les comptes du portail des %d familles importées ont été créés sans mot de passe : réinitialisez-les depuis "
                         "Individus > Liste des comptes internet avant d'envoyer les codes aux familles." % len(self.map_familles))

    @transaction.atomic
    def Executer(self):
        """ Tout ou rien : en cas d'erreur, aucune donnée n'est enregistrée """
        self.Importer_references()
        self.Importer_individus()
        self.Importer_familles()
        self.Importer_enregistrements()
        self.Finaliser()
        return self.rapport
