# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, logging, os
logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.urls import reverse


CATEGORIES = [
    ("rgpd", "Protection des données (RGPD)", "fa-shield"),
    ("stockage", "Stockage des fichiers", "fa-folder-open-o"),
    ("base", "Base de données", "fa-database"),
]

# Délais proposés dans les listes (en mois)
CHOIX_DELAIS = [(1, "1 mois"), (3, "3 mois"), (6, "6 mois"), (12, "1 an"), (24, "2 ans"), (36, "3 ans"), (60, "5 ans"), (120, "10 ans")]

# Nombre maximal d'éléments renvoyés dans l'aperçu
MAX_APERCU = 1000


def Get_date_limite(delai_mois=None):
    return datetime.date.today() - relativedelta(months=delai_mois)


def Formate_taille(octets=0):
    octets = octets or 0
    for unite in ("octets", "Ko", "Mo", "Go"):
        if abs(octets) < 1024 or unite == "Go":
            if unite == "octets":
                return "%d %s" % (octets, unite)
            return ("%.1f %s" % (octets, unite)).replace(".", ",")
        octets /= 1024.0


def Formate_nombre(nombre=0):
    return "{:,}".format(nombre or 0).replace(",", " ")


def Get_chemin_local(fieldfile=None):
    """ Renvoie le chemin local d'un fichier ou None si le stockage est distant """
    try:
        return fieldfile.storage.path(fieldfile.name)
    except Exception:
        return None


def Get_taille_fichier(fieldfile=None):
    """ Renvoie la taille d'un fichier. Pour les stockages distants, la taille n'est pas calculée (trop lent). """
    if not fieldfile or not fieldfile.name:
        return 0
    chemin = Get_chemin_local(fieldfile)
    if chemin:
        try:
            return os.path.getsize(chemin)
        except OSError:
            return 0
    return 0


def Url_famille(idfamille=None):
    try:
        return reverse("famille_resume", args=[idfamille])
    except Exception:
        return None


def Url_individu(idfamille=None, idindividu=None):
    try:
        if idfamille:
            return reverse("individu_resume", args=[idfamille, idindividu])
    except Exception:
        pass
    return None


class Element():
    """ Elément proposé au nettoyage """
    def __init__(self, id=None, label="", info="", octets=0, url=None):
        self.id = str(id)
        self.label = label
        self.info = info
        self.octets = octets or 0
        self.url = url

    def To_dict(self):
        return {"id": self.id, "label": self.label, "info": self.info, "octets": self.octets, "url": self.url}


class Resultat_analyse():
    def __init__(self, nbre=0, octets=0, elements=None, nbre_exclus=0, message_exclus="", detail="", octets_estimes=False):
        self.nbre = nbre
        self.octets = octets
        self.elements = elements
        self.nbre_exclus = nbre_exclus
        self.message_exclus = message_exclus
        self.detail = detail
        self.octets_estimes = octets_estimes

    def To_dict(self):
        return {
            "nbre": self.nbre,
            "nbre_texte": Formate_nombre(self.nbre),
            "octets": self.octets,
            "octets_texte": Formate_taille(self.octets) if self.octets else "",
            "octets_estimes": self.octets_estimes,
            "apercu": [element.To_dict() for element in self.elements[:MAX_APERCU]] if self.elements is not None else None,
            "apercu_tronque": bool(self.elements and len(self.elements) > MAX_APERCU),
            "nbre_exclus": self.nbre_exclus,
            "message_exclus": self.message_exclus,
            "detail": self.detail,
        }


class Resultat_execution():
    def __init__(self):
        self.nbre = 0
        self.nbre_echecs = 0
        self.nbre_exclus = 0
        self.octets = 0
        self.lignes_detail = []

    def To_dict(self):
        return {
            "nbre": self.nbre,
            "nbre_texte": Formate_nombre(self.nbre),
            "nbre_echecs": self.nbre_echecs,
            "nbre_exclus": self.nbre_exclus,
            "octets": self.octets,
            "octets_texte": Formate_taille(self.octets) if self.octets else "",
            "detail": "\n".join(self.lignes_detail),
        }


class Operation():
    """ Classe de base d'une opération du nettoyeur.
        Pour ajouter une opération : créer une classe héritant de Operation et l'ajouter à la liste OPERATIONS (__init__.py). """
    code = ""
    titre = ""
    description = ""
    categorie = "base"
    icone = "fa-eraser"

    # Délai par défaut en mois (None si l'opération n'utilise pas de date limite)
    delai_defaut = 12
    # Délai minimal autorisé en jours (sécurité)
    delai_minimum_jours = 30
    # Texte expliquant la date limite
    label_date = "Données antérieures au"

    # Nature de l'opération
    irreversible = True
    nature = "Suppression"  # Suppression, Anonymisation, Désactivation, Compression

    # L'aperçu permet-il de décocher des éléments un par un ?
    selection_individuelle = True

    # Suggestion : l'opération est mise en avant si le nombre d'éléments ou l'espace libéré dépasse ces seuils
    seuil_suggestion_nbre = 1
    seuil_suggestion_octets = None
    # L'opération est-elle prise en compte dans l'encart de la page d'accueil ?
    alerte_accueil = False
    # Libellé utilisé dans l'encart de la page d'accueil (le titre de l'opération par défaut)
    label_alerte = ""

    def __init__(self, cache=None):
        # Le cache est partagé entre les opérations d'une même requête (calcul des familles actives par exemple)
        self.cache = cache if cache is not None else {}

    def To_dict(self):
        return {
            "code": self.code, "titre": self.titre, "description": self.description, "categorie": self.categorie,
            "icone": self.icone, "delai_defaut": self.delai_defaut, "irreversible": self.irreversible, "nature": self.nature,
            "selection_individuelle": self.selection_individuelle, "label_date": self.label_date,
        }

    def Check_date_limite(self, date_limite=None):
        """ Renvoie un message d'erreur si la date limite n'est pas autorisée """
        if self.delai_defaut is None:
            return None
        if not date_limite:
            return "La date limite n'est pas renseignée"
        if date_limite > datetime.date.today() - datetime.timedelta(days=self.delai_minimum_jours):
            return "Pour l'opération '%s', la date limite doit être antérieure d'au moins %d jours à la date du jour" % (self.titre, self.delai_minimum_jours)
        return None

    def Is_suggestion(self, resultat=None):
        if not resultat or not resultat.nbre:
            return False
        if self.seuil_suggestion_octets and resultat.octets >= self.seuil_suggestion_octets:
            return True
        return bool(self.seuil_suggestion_nbre and resultat.nbre >= self.seuil_suggestion_nbre)

    def Analyser(self, date_limite=None):
        """ Renvoie un Resultat_analyse """
        raise NotImplementedError

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        """ Renvoie un Resultat_execution """
        raise NotImplementedError

    # --------------------------------------------------------------------------------------------
    # Outils communs : activité des familles et des individus
    # --------------------------------------------------------------------------------------------

    def Get_familles_actives(self, date_limite=None):
        """ Renvoie les ID des familles ayant une activité depuis la date limite """
        cle = ("familles_actives", date_limite)
        if cle not in self.cache:
            self.cache[cle] = Get_familles_actives(date_limite)
        return self.cache[cle]

    def Get_individus_actifs(self, date_limite=None):
        cle = ("individus_actifs", date_limite)
        if cle not in self.cache:
            self.cache[cle] = Get_individus_actifs(date_limite, familles_actives=self.Get_familles_actives(date_limite))
        return self.cache[cle]


def Get_familles_actives(date_limite=None):
    """ Une famille est considérée comme active si elle a, depuis la date limite :
        une inscription en cours ou terminée après la date, une consommation, une prestation, une adhésion,
        une location, une aide, une facture, un règlement, un paiement en ligne, un message sur le portail,
        une connexion au portail, une modification de sa fiche ou de celle d'un de ses membres (historique),
        un individu créé, une pièce, un quotient, un mandat, une assurance, un devis, une note ou un renseignement
        du portail, ou si elle a été créée après cette date.
        En cas de doute, une famille est toujours considérée comme active. """
    from core.models import Famille, Inscription, Consommation, Prestation, Cotisation, Location, Facture, Reglement, Paiement, \
                            PortailMessage, Rattachement, Aide, Historique, Individu, Piece, Quotient, Mandat, Assurance, Devis, Note, PortailRenseignement
    actives = set()
    actives.update(Inscription.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_limite)).values_list("famille_id", flat=True).distinct())
    actives.update(Consommation.objects.filter(date__gte=date_limite).values_list("inscription__famille_id", flat=True).distinct())
    actives.update(Prestation.objects.filter(date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Cotisation.objects.filter(date_fin__gte=date_limite, famille__isnull=False).values_list("famille_id", flat=True).distinct())
    individus_cotisations = set(Cotisation.objects.filter(date_fin__gte=date_limite, famille__isnull=True, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    if individus_cotisations:
        actives.update(Rattachement.objects.filter(individu_id__in=individus_cotisations).values_list("famille_id", flat=True).distinct())
    actives.update(Location.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__date__gte=date_limite) | Q(date_debut__date__gte=date_limite)).values_list("famille_id", flat=True).distinct())
    actives.update(Aide.objects.filter(date_fin__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Facture.objects.filter(date_edition__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Reglement.objects.filter(date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Paiement.objects.filter(horodatage__date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(PortailMessage.objects.filter(date_creation__date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Famille.objects.filter(Q(date_creation__date__gte=date_limite) | Q(utilisateur__last_login__date__gte=date_limite)).values_list("pk", flat=True))

    # Signes de retour d'une famille sans inscription ni facturation récente : fiche modifiée, individu ajouté,
    # pièce, quotient, mandat, assurance, devis, note ou renseignement du portail récent
    actives.update(Historique.objects.filter(horodatage__date__gte=date_limite, famille__isnull=False).values_list("famille_id", flat=True).distinct())
    individus_recents = set(Individu.objects.filter(date_creation__date__gte=date_limite).values_list("pk", flat=True))
    individus_recents.update(Historique.objects.filter(horodatage__date__gte=date_limite, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    pieces = Piece.objects.filter(date_debut__gte=date_limite)
    actives.update(pieces.filter(famille__isnull=False).values_list("famille_id", flat=True).distinct())
    individus_recents.update(pieces.filter(individu__isnull=False).values_list("individu_id", flat=True).distinct())
    actives.update(Rattachement.objects.filter(individu_id__in=individus_recents).values_list("famille_id", flat=True).distinct())
    actives.update(Quotient.objects.filter(date_fin__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Mandat.objects.filter(date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Assurance.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_limite)).values_list("famille_id", flat=True).distinct())
    actives.update(Devis.objects.filter(date_edition__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Note.objects.filter(date_saisie__date__gte=date_limite, famille__isnull=False).values_list("famille_id", flat=True).distinct())
    actives.update(PortailRenseignement.objects.filter(date__date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.discard(None)
    return actives


def Get_individus_actifs(date_limite=None, familles_actives=set()):
    """ Un individu est considéré comme actif s'il est rattaché à une famille active, s'il a une activité propre
        depuis la date limite ou s'il a été créé après cette date. """
    from core.models import Individu, Inscription, Consommation, Prestation, Cotisation, Rattachement, Historique, Piece
    actifs = set()
    actifs.update(Rattachement.objects.filter(famille_id__in=familles_actives, individu__isnull=False).values_list("individu_id", flat=True))
    actifs.update(Inscription.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_limite)).values_list("individu_id", flat=True).distinct())
    actifs.update(Consommation.objects.filter(date__gte=date_limite).values_list("individu_id", flat=True).distinct())
    actifs.update(Prestation.objects.filter(date__gte=date_limite, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    actifs.update(Cotisation.objects.filter(date_fin__gte=date_limite, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    actifs.update(Individu.objects.filter(date_creation__date__gte=date_limite).values_list("pk", flat=True))
    actifs.update(Historique.objects.filter(horodatage__date__gte=date_limite, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    actifs.update(Piece.objects.filter(date_debut__gte=date_limite, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    actifs.discard(None)
    return actifs


def Decoupe(liste=[], taille=500):
    """ Découpe une liste en lots (pour éviter les requêtes SQL trop longues) """
    liste = list(liste)
    for index in range(0, len(liste), taille):
        yield liste[index:index + taille]


def Is_individu_supprimable(individu=None, famille_exclue=None):
    """ Vérifie qu'un individu n'est pas utilisé par une autre famille (allocataire, titulaire Hélios, tiers solidaire,
        rattachement). La suppression d'un allocataire supprimerait la famille en cascade, celle d'un titulaire Hélios
        viderait silencieusement ce champ. """
    from core.models import Famille, Rattachement
    autres_familles = Famille.objects.filter(Q(allocataire=individu) | Q(titulaire_helios=individu) | Q(tiers_solidaire=individu))
    rattachements = Rattachement.objects.filter(individu=individu)
    if famille_exclue:
        autres_familles = autres_familles.exclude(pk=famille_exclue.pk)
        rattachements = rattachements.exclude(famille=famille_exclue)
    return not autres_familles.exists() and not rattachements.exists()
