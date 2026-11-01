# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Import/Export des modèles de documents.

Permet aux utilisateurs d'échanger leurs modèles de documents (factures, attestations...) entre
bases de données Noethysweb via un fichier NWD (JSON).

Format du fichier :
{
    "format": "noethysweb_modeles_documents",
    "version": 1,
    "date_export": "2026-11-01T10:00:00",
    "modeles": [
        {"ref": 12, "nom": "...", "categorie": "facture", "largeur": 210, "hauteur": 297, "fond": 3, "objets": [...]},
        {"ref": 3, "nom": "...", "categorie": "fond", "largeur": 210, "hauteur": 297, "fond": null, "objets": [...]},
    ]
}

Sécurité : les fichiers importés proviennent de tiers. Les textes des modèles peuvent contenir des
formules [[...]] dont les calculs sont évalués par eval() lors de la génération des documents
(core/utils/utils_resolveur_formule.py). Toutes les formules sont donc contrôlées à l'import et les
images doivent obligatoirement être embarquées en base64 (aucun chemin de fichier n'est accepté).
"""

import json, os, re, base64, mimetypes, logging, datetime
from uuid import uuid4
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from core.views.base import CustomView
from core.models import ModeleDocument, CHOIX_CATEGORIE_MODELE_DOCUMENT
from core.utils import utils_fichiers
from parametrage.forms.modeles_documents_import_export import Formulaire

logger = logging.getLogger(__name__)

FORMAT_FICHIER = "noethysweb_modeles_documents"
VERSION_FICHIER = 1
TAILLE_MAX_FICHIER = 20 * 1024 * 1024  # 20 Mo
DIMENSION_MAX = 2000  # en mm
NBRE_MAX_MODELES = 200
CATEGORIES_VALIDES = [code for code, label in CHOIX_CATEGORIE_MODELE_DOCUMENT]
DICT_LABELS_CATEGORIES = dict(CHOIX_CATEGORIE_MODELE_DOCUMENT)
MIMES_IMAGES_VALIDES = ("image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp")

# Regex identique à celle de utils_resolveur_formule.ResolveurFormule (formules conditionnelles, non évaluées par eval)
REGEX_FORMULE_CONDITIONNELLE = re.compile(r"[^SI]({.+})(<>|>=|<=|>|<|=)(.*)->(.*)", re.S)
REGEX_FORMULES = re.compile(r"\[\[.*?\]\]", re.S)
REGEX_MOTCLE = re.compile(r"\{[A-Za-z0-9_]+\}")
REGEX_CALCUL_AUTORISE = re.compile(r"^[0-9\s\.,\+\-\*/\(\)%]*$")


class View(CustomView, TemplateView):
    menu_code = "modeles_documents_liste"
    template_name = "parametrage/modeles_documents_import_export.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Modèles de documents"
        context["box_titre"] = "Importer/Exporter des modèles de documents"
        context["box_introduction"] = "Exportez un ou plusieurs modèles de documents dans un fichier NWD, par exemple pour les partager avec d'autres utilisateurs de Noethysweb, ou importez des modèles à partir d'un fichier NWD. Les images et les calques de fond sont inclus dans le fichier. Renseignez les paramètres et cliquez sur le bouton Exécuter."
        if "form" not in kwargs:
            # Présélection des modèles cochés dans la liste des modèles de documents
            selection = [pk for pk in self.request.GET.get("selection", "").split("-") if pk.isdigit()]
            context["form"] = Formulaire(request=self.request, initial={"action": "EXPORTER", "selection_modeles_exportables": selection} if selection else None)
        return context


def Executer(request):
    # Contrôle de la permission (secure_ajax ne vérifie que la catégorie de l'utilisateur)
    if not request.user.has_perm("core.modeles_documents_liste"):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder aux modèles de documents."}, status=401)

    form = Formulaire(request.POST, request.FILES, request=request)
    if not form.is_valid():
        erreurs = [erreur for liste in form.errors.values() for erreur in liste]
        return JsonResponse({"erreur": erreurs[0] if erreurs else "Veuillez compléter les paramètres"}, status=401)
    parametres = form.cleaned_data

    try:
        if parametres["action"] == "EXPORTER":
            return JsonResponse(Exporter(request, parametres))
        else:
            return JsonResponse(Importer(request, parametres))
    except ErreurImport as erreur:
        return JsonResponse({"erreur": str(erreur)}, status=401)


# ------------------------------------------------------------------------------------------------
# EXPORT
# ------------------------------------------------------------------------------------------------

def Get_condition_structure(request):
    return Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True)


def Exporter(request, parametres):
    modeles = list(ModeleDocument.objects.filter(Get_condition_structure(request), pk__in=parametres["selection_modeles_exportables"]))

    # Ajout des calques de fond utilisés par les modèles sélectionnés
    dict_modeles = {modele.pk: modele for modele in modeles}
    for modele in modeles:
        if modele.fond_id and modele.fond_id not in dict_modeles:
            dict_modeles[modele.fond_id] = modele.fond

    avertissements = []
    liste_modeles = []
    for modele in dict_modeles.values():
        objets = json.loads(modele.objets or "[]")
        objets = Embarquer_images(objets, nom_modele=modele.nom, avertissements=avertissements)
        liste_modeles.append({
            "ref": modele.pk,
            "nom": modele.nom,
            "categorie": modele.categorie,
            "largeur": modele.largeur,
            "hauteur": modele.hauteur,
            "fond": modele.fond_id if modele.fond_id in dict_modeles else None,
            "objets": objets,
        })

    donnees = {
        "format": FORMAT_FICHIER,
        "version": VERSION_FICHIER,
        "date_export": datetime.datetime.now().isoformat(timespec="seconds"),
        "modeles": liste_modeles,
    }

    # Création du fichier dans un sous-répertoire unique (évite les collisions entre utilisateurs)
    nom_rep = str(uuid4())
    rep_export = os.path.join(utils_fichiers.GetTempRep(), nom_rep)
    os.makedirs(rep_export, exist_ok=True)
    nom_fichier = "modeles_documents.nwd" if len(modeles) > 1 else "%s.nwd" % Nettoyer_nom_fichier(modeles[0].nom)
    with open(os.path.join(rep_export, nom_fichier), "w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)

    url_fichier = os.path.join(settings.MEDIA_URL, "temp", nom_rep, nom_fichier)
    return {"resultat": "ok", "action": "EXPORTER", "url_fichier": url_fichier, "nom_fichier": nom_fichier, "avertissements": avertissements}


def Nettoyer_nom_fichier(nom=""):
    nom = re.sub(r"[^\w\- ]", "", nom, flags=re.UNICODE).strip().replace(" ", "_")
    return nom[:80] or "modele_document"


def Parcourir_objets(objets=[]):
    """ Générateur qui parcourt récursivement les objets fabric (y compris ceux des groupes) """
    for objet in objets:
        if isinstance(objet, dict):
            yield objet
            if isinstance(objet.get("objects"), list):
                yield from Parcourir_objets(objet["objects"])


def Embarquer_images(objets=[], nom_modele="", avertissements=[]):
    """ Convertit en base64 les images référencées par un chemin vers le répertoire media """
    rep_media = os.path.realpath(settings.MEDIA_ROOT)
    for objet in Parcourir_objets(objets):
        if objet.get("categorie") != "image" or not isinstance(objet.get("src"), str) or objet["src"].startswith("data:"):
            continue
        src = objet["src"]
        chemin = src.split("?")[0]
        chemin = chemin[chemin.find("media/") + len("media/"):] if "media/" in chemin else chemin.lstrip("/")
        chemin = os.path.realpath(os.path.join(rep_media, chemin))
        mime = mimetypes.guess_type(chemin)[0]
        if chemin.startswith(rep_media + os.sep) and os.path.isfile(chemin) and mime in MIMES_IMAGES_VALIDES:
            with open(chemin, "rb") as fichier:
                objet["src"] = "data:%s;base64,%s" % (mime, base64.b64encode(fichier.read()).decode("ascii"))
        else:
            objet["src"] = ""
            avertissements.append("Une image du modèle '%s' n'a pas pu être incluse dans l'export." % nom_modele)
    return objets


# ------------------------------------------------------------------------------------------------
# IMPORT
# ------------------------------------------------------------------------------------------------

class ErreurImport(Exception):
    pass


def Lire_fichier(fichier):
    if fichier.size > TAILLE_MAX_FICHIER:
        raise ErreurImport("Le fichier est trop volumineux (20 Mo maximum).")
    try:
        donnees = json.loads(fichier.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ErreurImport("Le fichier n'est pas un fichier de modèles de documents valide.")
    if not isinstance(donnees, dict) or donnees.get("format") != FORMAT_FICHIER or not isinstance(donnees.get("modeles"), list):
        raise ErreurImport("Le fichier n'est pas un fichier de modèles de documents valide.")
    if not isinstance(donnees.get("version"), int) or donnees["version"] > VERSION_FICHIER:
        raise ErreurImport("Ce fichier a été créé avec une version plus récente de Noethysweb. Veuillez mettre à jour l'application.")
    if len(donnees["modeles"]) > NBRE_MAX_MODELES:
        raise ErreurImport("Le fichier contient trop de modèles.")

    # Validation de chaque modèle
    dict_modeles = {}
    for modele in donnees["modeles"]:
        Valider_modele(modele)
        dict_modeles[str(modele["ref"])] = modele

    # Vérifie que les fonds référencés sont bien des calques de fond présents dans le fichier
    for modele in dict_modeles.values():
        if modele.get("fond") is not None:
            fond = dict_modeles.get(str(modele["fond"]))
            if not fond or fond["categorie"] != "fond" or modele["categorie"] == "fond":
                modele["fond"] = None
    return dict_modeles


def Valider_modele(modele={}):
    if not isinstance(modele, dict):
        raise ErreurImport("Le fichier contient un modèle invalide.")
    nom = modele.get("nom")
    if not isinstance(nom, str) or not nom.strip() or len(nom) > 200:
        raise ErreurImport("Le fichier contient un modèle sans nom valide.")
    if not isinstance(modele.get("ref"), (int, str)):
        raise ErreurImport("Le modèle '%s' est invalide." % nom)
    if modele.get("categorie") not in CATEGORIES_VALIDES:
        raise ErreurImport("La catégorie du modèle '%s' est inconnue." % nom)
    for champ in ("largeur", "hauteur"):
        valeur = modele.get(champ)
        if not isinstance(valeur, int) or isinstance(valeur, bool) or not 1 <= valeur <= DIMENSION_MAX:
            raise ErreurImport("Les dimensions du modèle '%s' sont invalides." % nom)
    if not isinstance(modele.get("objets"), list):
        raise ErreurImport("Le contenu du modèle '%s' est invalide." % nom)

    for objet in Parcourir_objets(modele["objets"]):
        # Contrôle des formules contenues dans les textes
        for cle in ("text", "texte"):
            if isinstance(objet.get(cle), str):
                for formule in REGEX_FORMULES.findall(objet[cle]):
                    if not Formule_sure(formule):
                        raise ErreurImport("Le modèle '%s' contient une formule non autorisée : %s" % (nom, formule[:100]))

        # Contrôle des images : uniquement des images embarquées
        if objet.get("categorie") == "image":
            src = objet.get("src", "")
            if not isinstance(src, str) or (src and not Image_base64_valide(src)):
                raise ErreurImport("Le modèle '%s' contient une image invalide." % nom)

        # Les sources des logos et photos sont recalculées à l'impression : on neutralise les chemins
        if objet.get("categorie") in ("logo", "photo") and isinstance(objet.get("src"), str) and not objet["src"].startswith("data:"):
            if ".." in objet["src"] or not re.match(r"^/?(static|media)/[\w\-/\.]+$", objet["src"]):
                objet["src"] = ""


def Formule_sure(formule=""):
    """ Vérifie qu'une formule ne pourra pas exécuter de code arbitraire lors de son évaluation """
    contenu = formule.rstrip("]]").lstrip("[[")
    resultat = REGEX_FORMULE_CONDITIONNELLE.search(contenu)
    if resultat is not None and len(resultat.groups()) == 4:
        # Formule conditionnelle : non évaluée par eval()
        return True
    # Formule de calcul : seuls les mots-clés, nombres et opérateurs arithmétiques sont acceptés
    calcul = REGEX_MOTCLE.sub("0", contenu)
    if len(calcul) > 500 or "**" in calcul:
        return False
    return bool(REGEX_CALCUL_AUTORISE.match(calcul))


def Image_base64_valide(src=""):
    match = re.match(r"^data:([\w/+\-\.]+);base64,([A-Za-z0-9+/=\s]+)$", src)
    if not match or match.group(1) not in MIMES_IMAGES_VALIDES:
        return False
    try:
        base64.b64decode(match.group(2), validate=False)
    except Exception:
        return False
    return True


def Importer(request, parametres):
    dict_modeles = Lire_fichier(parametres["fichier"])
    if not dict_modeles:
        raise ErreurImport("Le fichier ne contient aucun modèle.")

    # Etape 1 : renvoie la liste des modèles importables pour sélection par l'utilisateur
    selection = json.loads(parametres["selection_modeles_importables"] or "[]")
    if not selection:
        liste_modeles = [{"value": str(ref), "text": "%s (%s)" % (modele["nom"], DICT_LABELS_CATEGORIES[modele["categorie"]])}
                         for ref, modele in sorted(dict_modeles.items(), key=lambda x: (x[1]["categorie"] == "fond", x[1]["nom"]))]
        return {"resultat": "ok", "action": "SELECTION_MODELES", "liste_modeles": json.dumps(liste_modeles)}

    # Etape 2 : importation des modèles sélectionnés
    structure = parametres["selection_structure"]
    dict_fonds_crees = {}
    noms_importes = []

    def Creer_modele(modele={}, fond=None):
        nom = modele["nom"].strip()
        if ModeleDocument.objects.filter(categorie=modele["categorie"], nom=nom).exists():
            nom = ("%s (importé)" % nom)[:200]
        nouveau_modele = ModeleDocument.objects.create(
            nom=nom, categorie=modele["categorie"], largeur=modele["largeur"], hauteur=modele["hauteur"],
            fond=fond, defaut=False, objets=json.dumps(modele["objets"]), structure=structure)
        noms_importes.append(nouveau_modele.nom)
        return nouveau_modele

    def Get_fond(ref=None):
        ref = str(ref)
        if ref in dict_fonds_crees:
            return dict_fonds_crees[ref]
        modele_fond = dict_modeles[ref]
        # Réutilise un calque de fond identique déjà présent dans la base
        objets_json = json.dumps(modele_fond["objets"])
        fond = ModeleDocument.objects.filter(Get_condition_structure(request), categorie="fond", nom=modele_fond["nom"].strip(),
                                             largeur=modele_fond["largeur"], hauteur=modele_fond["hauteur"], objets=objets_json).first()
        if not fond:
            fond = Creer_modele(modele_fond)
        dict_fonds_crees[ref] = fond
        return fond

    with transaction.atomic():
        # Les calques de fond sélectionnés en premier
        for ref in sorted([str(r) for r in selection if str(r) in dict_modeles], key=lambda r: dict_modeles[r]["categorie"] != "fond"):
            modele = dict_modeles[ref]
            if modele["categorie"] == "fond":
                Get_fond(ref)
            else:
                fond = Get_fond(modele["fond"]) if modele.get("fond") is not None else None
                Creer_modele(modele, fond=fond)

        # Si aucun modèle de la catégorie n'est défini par défaut, le premier importé le devient
        for categorie in {dict_modeles[str(r)]["categorie"] for r in selection if str(r) in dict_modeles}:
            if categorie != "fond" and not ModeleDocument.objects.filter(categorie=categorie, defaut=True).exists():
                premier = ModeleDocument.objects.filter(categorie=categorie).order_by("pk").first()
                if premier:
                    premier.defaut = True
                    premier.save()

    logger.info("Import de modèles de documents par %s : %s" % (request.user, ", ".join(noms_importes)))
    return {"resultat": "ok", "action": "IMPORTER", "nbre_modeles": len(noms_importes)}
