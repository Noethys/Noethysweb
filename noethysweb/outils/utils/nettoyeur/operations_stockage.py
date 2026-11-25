# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, logging, os, shutil, time, io, tempfile
logger = logging.getLogger(__name__)
from django.apps import apps
from django.db.models import FileField
from outils.utils.nettoyeur.base import Operation, Element, Resultat_analyse, Resultat_execution, Url_famille, Url_individu, \
                                        Get_taille_fichier, Decoupe


def Label_piece(piece=None):
    try:
        nom = piece.Get_nom() or "Pièce"
    except Exception:
        nom = piece.titre or "Pièce"
    if piece.famille_id and piece.famille:
        nom += " - %s" % piece.famille.nom
    elif piece.individu_id and piece.individu:
        nom += " - %s %s" % (piece.individu.nom, piece.individu.prenom or "")
    return nom


def Url_piece(piece=None):
    if piece.famille_id:
        return Url_famille(piece.famille_id)
    return None


# ------------------------------------------------------------------------------------------------
# Pièces expirées
# ------------------------------------------------------------------------------------------------

class Supprimer_pieces_expirees(Operation):
    code = "pieces_expirees"
    titre = "Supprimer les pièces expirées"
    description = "Supprime les pièces dont la date de fin de validité est antérieure à la date limite, ainsi que leurs fichiers (PDF, images...)."
    categorie = "stockage"
    icone = "fa-calendar-times-o"
    delai_defaut = 24
    delai_minimum_jours = 30
    label_date = "Pièces expirées avant le"
    alerte_accueil = True
    label_alerte = "Pièces expirées"
    seuil_suggestion_nbre = 50
    seuil_suggestion_octets = 50 * 1024 * 1024

    def Get_queryset(self, date_limite=None):
        from core.models import Piece
        return Piece.objects.select_related("type_piece", "individu", "famille").filter(date_fin__lt=date_limite)

    def Analyser(self, date_limite=None):
        elements = []
        for piece in self.Get_queryset(date_limite).order_by("date_fin"):
            elements.append(Element(id=piece.pk, label=Label_piece(piece), info="Expirée le %s" % piece.date_fin.strftime("%d/%m/%Y"),
                                    octets=Get_taille_fichier(piece.document), url=Url_piece(piece)))
        return Resultat_analyse(nbre=len(elements), elements=elements, octets=sum([element.octets for element in elements]))

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        resultat = Resultat_execution()
        for piece in self.Get_queryset(date_limite):
            if str(piece.pk) in exclusions:
                resultat.nbre_exclus += 1
                continue
            octets = Get_taille_fichier(piece.document)
            piece.delete()
            resultat.nbre += 1
            resultat.octets += octets
        return resultat


# ------------------------------------------------------------------------------------------------
# Pièces remplacées par une pièce plus récente
# ------------------------------------------------------------------------------------------------

class Supprimer_pieces_remplacees(Operation):
    code = "pieces_remplacees"
    titre = "Supprimer les pièces remplacées"
    description = ("Supprime les anciennes pièces quand une pièce plus récente du même type a été fournie pour le même individu "
                   "ou la même famille. Seules les pièces dont la date de début est antérieure à la date limite sont concernées.")
    categorie = "stockage"
    icone = "fa-clone"
    delai_defaut = 12
    delai_minimum_jours = 30
    label_date = "Pièces remplacées datant d'avant le"
    alerte_accueil = True
    label_alerte = "Pièces remplacées"
    seuil_suggestion_nbre = 50
    seuil_suggestion_octets = 50 * 1024 * 1024

    def Get_candidats(self, date_limite=None):
        from core.models import Piece
        groupes = {}
        for piece in Piece.objects.filter(type_piece__isnull=False).values("pk", "type_piece_id", "individu_id", "famille_id", "date_debut"):
            cle = (piece["type_piece_id"], "i", piece["individu_id"]) if piece["individu_id"] else (piece["type_piece_id"], "f", piece["famille_id"])
            groupes.setdefault(cle, []).append(piece)
        candidats = {}
        for cle, pieces in groupes.items():
            if len(pieces) < 2:
                continue
            pieces.sort(key=lambda piece: (piece["date_debut"] or datetime.date(1900, 1, 1), piece["pk"]))
            plus_recente = pieces[-1]
            for piece in pieces[:-1]:
                if not piece["date_debut"] or piece["date_debut"] < date_limite:
                    candidats[piece["pk"]] = plus_recente
        return candidats

    def Analyser(self, date_limite=None):
        from core.models import Piece
        candidats = self.Get_candidats(date_limite)
        elements = []
        for lot in Decoupe(candidats.keys()):
            for piece in Piece.objects.select_related("type_piece", "individu", "famille").filter(pk__in=lot):
                plus_recente = candidats[piece.pk]
                info = "Du %s, remplacée par celle du %s" % (piece.date_debut.strftime("%d/%m/%Y") if piece.date_debut else "?",
                                                             plus_recente["date_debut"].strftime("%d/%m/%Y") if plus_recente["date_debut"] else "?")
                elements.append(Element(id=piece.pk, label=Label_piece(piece), info=info, octets=Get_taille_fichier(piece.document), url=Url_piece(piece)))
        elements.sort(key=lambda element: element.label.lower())
        return Resultat_analyse(nbre=len(elements), elements=elements, octets=sum([element.octets for element in elements]))

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Piece
        resultat = Resultat_execution()
        candidats = self.Get_candidats(date_limite)
        for lot in Decoupe(candidats.keys()):
            for piece in Piece.objects.filter(pk__in=lot):
                if str(piece.pk) in exclusions:
                    resultat.nbre_exclus += 1
                    continue
                octets = Get_taille_fichier(piece.document)
                piece.delete()
                resultat.nbre += 1
                resultat.octets += octets
        return resultat


# ------------------------------------------------------------------------------------------------
# Fichiers orphelins
# ------------------------------------------------------------------------------------------------

def Get_repertoires_fichiers():
    """ Renvoie la liste des répertoires de fichiers gérés par les modèles {chemin_repertoire: (location, set(noms_references))} """
    repertoires = {}
    for modele in apps.get_models():
        for champ in modele._meta.concrete_fields:
            if not isinstance(champ, FileField) or getattr(champ.upload_to, "__name__", "") != "get_uuid_path":
                continue
            try:
                location = os.path.abspath(champ.storage.path(""))
            except Exception:
                # Stockage distant : pas de recherche de fichiers orphelins
                continue
            repertoire = os.path.join(location, modele._meta.db_table)
            repertoires.setdefault(repertoire, (location, set()))
            references = modele.objects.exclude(**{champ.name: ""}).exclude(**{"%s__isnull" % champ.name: True}).values_list(champ.name, flat=True)
            # Les chemins importés depuis Windows peuvent contenir des antislashs (individus\xxx.jpg) :
            # sur le disque, le fichier est bien dans individus/xxx.jpg, il ne doit donc pas être considéré comme orphelin
            repertoires[repertoire][1].update([os.path.normpath(nom.replace("\\", "/")) for nom in references])
    # Plusieurs modèles peuvent partager une même table : fusion des références par location
    references_location = {}
    for repertoire, (location, references) in repertoires.items():
        references_location.setdefault(location, set()).update(references)
    return {repertoire: (location, references_location[location]) for repertoire, (location, references) in repertoires.items()}


class Supprimer_fichiers_orphelins(Operation):
    code = "fichiers_orphelins"
    titre = "Supprimer les fichiers orphelins"
    description = ("Supprime les fichiers présents dans le répertoire media mais qui ne sont plus associés à aucune donnée "
                   "(pièces, photos, documents...), par exemple après une suppression interrompue. Les fichiers de moins de 24 heures sont ignorés.")
    categorie = "stockage"
    icone = "fa-chain-broken"
    delai_defaut = None
    label_date = ""
    alerte_accueil = True
    label_alerte = "Fichiers orphelins"
    seuil_suggestion_nbre = 20
    seuil_suggestion_octets = 20 * 1024 * 1024

    def Get_candidats(self):
        limite = time.time() - 24 * 3600
        candidats = {}
        for repertoire, (location, references) in Get_repertoires_fichiers().items():
            if not os.path.isdir(repertoire):
                continue
            for racine, sous_repertoires, fichiers in os.walk(repertoire):
                for nom_fichier in fichiers:
                    chemin = os.path.join(racine, nom_fichier)
                    nom_relatif = os.path.normpath(os.path.relpath(chemin, location))
                    if nom_relatif in references:
                        continue
                    try:
                        stat = os.stat(chemin)
                    except OSError:
                        continue
                    if stat.st_mtime > limite:
                        continue
                    candidats[chemin] = (nom_relatif, stat.st_size, stat.st_mtime)
        return candidats

    def Analyser(self, date_limite=None):
        elements = []
        for chemin, (nom_relatif, taille, mtime) in sorted(self.Get_candidats().items()):
            elements.append(Element(id=nom_relatif, label=nom_relatif, info="Modifié le %s" % datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y"), octets=taille))
        return Resultat_analyse(nbre=len(elements), elements=elements, octets=sum([element.octets for element in elements]))

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        resultat = Resultat_execution()
        for chemin, (nom_relatif, taille, mtime) in self.Get_candidats().items():
            if nom_relatif in exclusions:
                resultat.nbre_exclus += 1
                continue
            try:
                os.remove(chemin)
                resultat.nbre += 1
                resultat.octets += taille
            except OSError as err:
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s : %s" % (nom_relatif, err))
        return resultat


# ------------------------------------------------------------------------------------------------
# Photos des individus inactifs
# ------------------------------------------------------------------------------------------------

class Supprimer_photos_inactifs(Operation):
    code = "photos_inactifs"
    titre = "Supprimer les photos des individus inactifs"
    description = "Supprime la photo d'identité des individus sans activité depuis la date limite."
    categorie = "stockage"
    icone = "fa-camera"
    delai_defaut = 24
    delai_minimum_jours = 90
    label_date = "Individus sans activité depuis le"

    def Get_queryset(self, date_limite=None):
        from core.models import Individu
        ids = set(Individu.objects.exclude(photo="").exclude(photo__isnull=True).values_list("pk", flat=True)) - self.Get_individus_actifs(date_limite)
        return Individu.objects.filter(pk__in=ids)

    def Analyser(self, date_limite=None):
        from core.models import Rattachement
        qs = self.Get_queryset(date_limite)
        familles = dict(Rattachement.objects.filter(individu__in=qs).values_list("individu_id", "famille_id"))
        elements = [Element(id=individu.pk, label=("%s %s" % (individu.nom, individu.prenom or "")).strip(), octets=Get_taille_fichier(individu.photo),
                            url=Url_individu(familles.get(individu.pk), individu.pk)) for individu in qs.order_by("nom", "prenom")]
        return Resultat_analyse(nbre=len(elements), elements=elements, octets=sum([element.octets for element in elements]))

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        resultat = Resultat_execution()
        for individu in self.Get_queryset(date_limite):
            if str(individu.pk) in exclusions:
                resultat.nbre_exclus += 1
                continue
            octets = Get_taille_fichier(individu.photo)
            individu.photo.delete(save=True)
            resultat.nbre += 1
            resultat.octets += octets
        return resultat


# ------------------------------------------------------------------------------------------------
# Réduction des images trop lourdes
# ------------------------------------------------------------------------------------------------

EXTENSIONS_IMAGES = (".jpg", ".jpeg", ".png", ".webp")

# (modèle, champ, taille au-delà de laquelle l'image est réduite, dimension maximale en pixels, libellé)
IMAGES_A_REDUIRE = [
    ("Individu", "photo", 300 * 1024, 800, "Photo d'individu"),
    ("Collaborateur", "photo", 300 * 1024, 800, "Photo de collaborateur"),
    ("Piece", "document", 1024 * 1024, 2000, "Pièce"),
    ("Information", "document", 1024 * 1024, 2000, "Document médical"),
    ("Quotient", "document", 1024 * 1024, 2000, "Justificatif de quotient"),
    ("Assurance", "document", 1024 * 1024, 2000, "Attestation d'assurance"),
    ("PieceCollaborateur", "document", 1024 * 1024, 2000, "Pièce de collaborateur"),
    ("Photo", "fichier", 1024 * 1024, 2000, "Photo d'album"),
]


def Reduire_image(contenu=None, dimension_max=2000):
    """ Renvoie (nouveau_contenu, format) ou (None, None) si l'image ne peut pas être réduite """
    from PIL import Image, ImageOps
    image = Image.open(io.BytesIO(contenu))
    format_image = image.format
    if format_image not in ("JPEG", "PNG", "WEBP"):
        return None, None
    image = ImageOps.exif_transpose(image)
    image.thumbnail((dimension_max, dimension_max), Image.LANCZOS)
    sortie = io.BytesIO()
    if format_image == "JPEG":
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(sortie, format="JPEG", quality=85, optimize=True, progressive=True)
    elif format_image == "PNG":
        image.save(sortie, format="PNG", optimize=True)
    else:
        image.save(sortie, format="WEBP", quality=85)
    return sortie.getvalue(), format_image


class Reduire_images(Operation):
    code = "images_lourdes"
    titre = "Réduire les images trop lourdes"
    description = ("Redimensionne et compresse les images trop volumineuses : photos d'individus et de collaborateurs ramenées à 800 pixels "
                   "(au-delà de 300 Ko), pièces, documents et photos d'albums ramenés à 2000 pixels (au-delà de 1 Mo). "
                   "Les fichiers PDF ne sont pas modifiés. L'image d'origine est remplacée.")
    categorie = "stockage"
    icone = "fa-compress"
    delai_defaut = None
    nature = "Compression"
    seuil_suggestion_nbre = 20
    seuil_suggestion_octets = 50 * 1024 * 1024

    def Get_candidats(self):
        candidats = []
        for nom_modele, nom_champ, seuil, dimension_max, label in IMAGES_A_REDUIRE:
            modele = apps.get_model("core", nom_modele)
            qs = modele.objects.exclude(**{nom_champ: ""}).exclude(**{"%s__isnull" % nom_champ: True})
            for pk, nom_fichier in qs.values_list("pk", nom_champ):
                if not nom_fichier.lower().endswith(EXTENSIONS_IMAGES):
                    continue
                champ = modele._meta.get_field(nom_champ)
                try:
                    chemin = champ.storage.path(nom_fichier)
                    taille = os.path.getsize(chemin)
                except Exception:
                    # Stockage distant ou fichier absent
                    continue
                if taille > seuil:
                    candidats.append(("%s:%d" % (nom_modele, pk), nom_modele, nom_champ, pk, nom_fichier, taille, dimension_max, label))
        return candidats

    def Analyser(self, date_limite=None):
        candidats = self.Get_candidats()
        elements = [Element(id=id, label="%s ID%d" % (label, pk), info=os.path.basename(nom_fichier), octets=taille)
                    for id, nom_modele, nom_champ, pk, nom_fichier, taille, dimension_max, label in candidats]
        # Estimation : les images sont en général réduites des deux tiers
        octets = int(sum([element.octets for element in elements]) * 0.65)
        return Resultat_analyse(nbre=len(elements), elements=elements, octets=octets, octets_estimes=True)

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        resultat = Resultat_execution()
        for id, nom_modele, nom_champ, pk, nom_fichier, taille, dimension_max, label in self.Get_candidats():
            if id in exclusions:
                resultat.nbre_exclus += 1
                continue
            modele = apps.get_model("core", nom_modele)
            champ = modele._meta.get_field(nom_champ)
            try:
                chemin = champ.storage.path(nom_fichier)
                with open(chemin, "rb") as fichier:
                    contenu = fichier.read()
                nouveau_contenu, format_image = Reduire_image(contenu, dimension_max=dimension_max)
                if not nouveau_contenu or len(nouveau_contenu) >= len(contenu) * 0.9:
                    continue
                # Ecriture dans un fichier temporaire puis remplacement (pour ne jamais laisser un fichier tronqué)
                descripteur, chemin_temp = tempfile.mkstemp(dir=os.path.dirname(chemin))
                with os.fdopen(descripteur, "wb") as fichier:
                    fichier.write(nouveau_contenu)
                shutil.copymode(chemin, chemin_temp)
                os.replace(chemin_temp, chemin)
                resultat.nbre += 1
                resultat.octets += len(contenu) - len(nouveau_contenu)
            except Exception as err:
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s : %s" % (nom_fichier, err))
        return resultat
