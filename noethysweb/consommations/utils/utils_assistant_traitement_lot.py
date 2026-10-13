# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Moteur de l'assistant de traitement par lot des consommations.

- La sélection et la simulation sont calculées en base, sur des listes d'identifiants, sans charger la grille.
- L'application est faite par paquets d'inscriptions (appels successifs depuis la page) avec la grille virtuelle,
  pour conserver exactement les règles de facturation de la grille des consommations.
"""

import datetime, json, logging, time
logger = logging.getLogger(__name__)
from django.db.models import Q, Max, Sum, Count, Value, IntegerField
from django.db.models.functions import Coalesce
from core.models import Activite, Groupe, CategorieTarif, Inscription, Individu, Unite, UniteRemplissage, Remplissage, Ouverture, \
                        Consommation, Evenement, Vacance, Ferie, Scolarite, LISTE_ETATS_CONSO
from core.utils import utils_dates
from individus.utils.utils_inscriptions_assistant_lot import Normaliser_texte, Get_valeurs, Calculer_age, Get_nom_complet, \
                                                              Par_paquets, Resoudre_liste, Get_entier, Get_liste_entiers, Get_date, Erreur, \
                                                              Is_validite_illimitee

LIBELLE_FONCTION = "Assistant de traitement par lot"
CLE_SESSION = "assistant_traitement_lot"
TAILLE_PAQUET = 10
NBRE_MAX_DATES = 400
NBRE_MAX_INSCRIPTIONS = 3000
ETATS = dict(LISTE_ETATS_CONSO)
ETATS_PLACES = ("reservation", "present")
ETATS_POINTES = ("present", "absentj", "absenti")
ETATS_ACTIFS = ("reservation", "present", "attente", "demande")
TYPES_UNITES = dict(Unite.choix_type)

STATUTS = {
    "creer": "À créer",
    "attente": "À créer en attente (complet)",
    "existe": "Déjà existante",
    "ferme": "Jour fermé pour le groupe",
    "incompatible": "Unité incompatible déjà réservée",
    "complet": "Complet : non créée",
    "hors_inscription": "Hors période d'inscription",
    "unite_groupe": "Unité non proposée à ce groupe",
    "unite_validite": "Unité hors période de validité",
    "modifier": "À modifier",
    "supprimer": "À supprimer",
    "facturee": "Facturée : conservée",
    "pointee": "Déjà pointée : conservée",
    "forfait": "Liée à un forfait : conservée",
    "interdit": "Changement d'état impossible : conservée",
}
STATUTS_ACTION = ("creer", "attente", "modifier", "supprimer")


def Lire_parametres(donnees=None):
    if isinstance(donnees, dict):
        return donnees
    try:
        parametres = json.loads(donnees or "{}")
    except ValueError:
        raise Erreur("Les paramètres ne sont pas valides")
    if not isinstance(parametres, dict):
        raise Erreur("Les paramètres ne sont pas valides")
    return parametres


def Get_activite(idactivite=None, request=None):
    idactivite = Get_entier(idactivite)
    if not idactivite:
        raise Erreur("Veuillez sélectionner une activité")
    activite = Activite.objects.filter(pk=idactivite, structure__in=request.user.structures.all()).first()
    if not activite:
        raise Erreur("Cette activité n'est pas accessible")
    return activite


def Heure(valeur=None):
    """ Normalise une heure au format HH:MM (ou None) """
    if not valeur:
        return None
    texte = str(valeur)[:5]
    try:
        datetime.datetime.strptime(texte, "%H:%M")
    except ValueError:
        raise Erreur("L'heure %s n'est pas valide" % valeur)
    return texte


def Date_fr(date):
    return utils_dates.ConvertDateToFR(date) if date else ""


# ---------------------------------------------- Activité ----------------------------------------------

def Get_infos_activite(activite=None):
    inscrits = {ligne["groupe"]: ligne["nbre"] for ligne in Inscription.objects.filter(activite=activite, statut="ok").values("groupe").annotate(nbre=Count("pk"))}
    unites = []
    for unite in Unite.objects.prefetch_related("groupes", "incompatibilites").filter(activite=activite).order_by("ordre"):
        unites.append({
            "id": unite.pk, "nom": unite.nom, "type": unite.type, "type_label": TYPES_UNITES.get(unite.type, unite.type),
            "heure_debut": Heure(unite.heure_debut) or "", "heure_fin": Heure(unite.heure_fin) or "",
            "groupes": [groupe.pk for groupe in unite.groupes.all()], "incompatibilites": [u.pk for u in unite.incompatibilites.all()],
        })
    # Vacances proposées en raccourcis : celles qui ne sont pas terminées depuis longtemps, jusqu'à la fin de l'activité
    # (ou jusqu'à un an à partir d'aujourd'hui pour une activité à validité illimitée)
    aujourdhui = datetime.date.today()
    debut = max(activite.date_debut or aujourdhui, aujourdhui - datetime.timedelta(days=200))
    fin = aujourdhui + datetime.timedelta(days=365) if Is_validite_illimitee(activite) else activite.date_fin
    vacances = [{"nom": "%s %s" % (vacance.get_nom_display() if hasattr(vacance, "get_nom_display") else vacance.nom, vacance.annee), "date_debut": str(vacance.date_debut), "date_fin": str(vacance.date_fin)}
                for vacance in Vacance.objects.filter(date_fin__gte=debut, date_debut__lte=fin).order_by("date_debut")[:12]]
    return {
        "id": activite.pk, "nom": activite.nom,
        "date_debut": str(activite.date_debut) if activite.date_debut else "", "date_fin": str(activite.date_fin) if activite.date_fin else "",
        "date_debut_fr": Date_fr(activite.date_debut), "date_fin_fr": Date_fr(activite.date_fin),
        "illimitee": Is_validite_illimitee(activite),
        "groupes": [{"id": g.pk, "nom": g.nom, "inscrits": inscrits.get(g.pk, 0)} for g in Groupe.objects.filter(activite=activite).order_by("ordre", "nom")],
        "categories": [{"id": c.pk, "nom": c.nom} for c in CategorieTarif.objects.filter(activite=activite).order_by("nom")],
        "unites": unites,
        "inscrits": sum(inscrits.values()),
        "vacances": vacances,
        "etats": LISTE_ETATS_CONSO,
    }


# ---------------------------------------------- Dates ----------------------------------------------

def Calculer_dates(activite=None, periode={}):
    """ Dates retenues selon la période, les jours, la fréquence, les fériés et les ouvertures de l'activité.
    Reprend les règles du traitement par lot existant (consommations/utils/utils_traitement_lot.py) """
    date_debut = Get_date(periode.get("date_debut"), obligatoire=True, nom="la date de début")
    date_fin = Get_date(periode.get("date_fin"), obligatoire=True, nom="la date de fin")
    if date_fin < date_debut:
        raise Erreur("La date de fin doit être supérieure à la date de début")
    if (date_fin - date_debut).days > NBRE_MAX_DATES:
        raise Erreur("La période ne peut pas dépasser %d jours" % NBRE_MAX_DATES)
    jours_scolaires = {str(j) for j in periode.get("jours_scolaires", [])}
    jours_vacances = {str(j) for j in periode.get("jours_vacances", [])}
    if not jours_scolaires and not jours_vacances:
        raise Erreur("Cochez au moins un jour de la semaine")
    frequence = Get_entier(periode.get("frequence")) or 1
    inclure_feries = bool(periode.get("inclure_feries"))
    ouvertures_uniquement = periode.get("ouvertures_uniquement", True)

    liste_vacances = list(Vacance.objects.filter(date_fin__gte=date_debut, date_debut__lte=date_fin))
    liste_feries = list(Ferie.objects.all())
    dates_ouvertes = set(Ouverture.objects.filter(activite=activite, date__gte=date_debut, date__lte=date_fin).values_list("date", flat=True).distinct())

    jours, retenues, feries_exclus, fermes_exclus = [], [], [], []
    num_semaine = frequence
    date_precedente = date_debut
    date = date_debut
    while date <= date_fin:
        vacances = bool(utils_dates.EstEnVacances(date, liste_vacances))
        valide = str(date.weekday()) in (jours_vacances if vacances else jours_scolaires)
        if date.weekday() < date_precedente.weekday():
            num_semaine += 1
        if frequence in (2, 3, 4) and num_semaine % frequence != 0:
            valide = False
        if valide and frequence in (5, 6):
            semaine_annee = date.isocalendar()[1]
            if (semaine_annee % 2 == 0 and frequence == 6) or (semaine_annee % 2 != 0 and frequence == 5):
                valide = False
        statut = "retenu" if valide else ""
        if valide and not inclure_feries and utils_dates.EstFerie(date, liste_feries):
            statut = "ferie"
            feries_exclus.append(date)
        elif valide and ouvertures_uniquement and date not in dates_ouvertes:
            statut = "ferme"
            fermes_exclus.append(date)
        if statut == "retenu":
            retenues.append(date)
        jours.append({"date": str(date), "statut": statut, "vacances": vacances})
        date_precedente = date
        date += datetime.timedelta(days=1)
    return {"dates": retenues, "jours": jours, "feries_exclus": feries_exclus, "fermes_exclus": fermes_exclus}


def Get_evenements(activite=None, dates=[], unites=[]):
    """ Événements programmés aux dates retenues sur les unités événementielles """
    if not dates or not unites:
        return []
    evenements = list(Evenement.objects.select_related("groupe", "unite").filter(activite=activite, unite_id__in=unites, date__in=dates).order_by("date", "heure_debut", "nom"))
    places = {ligne["evenement"]: ligne["nbre"] for ligne in Consommation.objects.filter(evenement__in=evenements, etat__in=ETATS_PLACES).values("evenement").annotate(nbre=Count("pk"))}
    return [{"id": e.pk, "date": str(e.date), "date_fr": Date_fr(e.date), "jour": e.date.weekday(), "nom": e.nom, "groupe": e.groupe_id, "groupe_nom": e.groupe.nom,
             "unite": e.unite_id, "heure_debut": Heure(e.heure_debut) or "", "heure_fin": Heure(e.heure_fin) or "",
             "capacite": e.capacite_max or None, "places_prises": places.get(e.pk, 0), "montant": float(e.montant) if e.montant else 0.0} for e in evenements]


# ---------------------------------------------- Sélection des individus ----------------------------------------------

def Get_selection(p={}, activite=None, dates=[], request=None):
    """ Inscriptions concernées, triées par nom : [{inscription, individu, famille, groupe, categorie_tarif, date_debut, date_fin, nom}] """
    individus = p.get("individus") or {}
    filtres = p.get("filtres") or {}
    date_min, date_max = (min(dates), max(dates)) if dates else (None, None)

    inscriptions = Inscription.objects.filter(activite=activite)
    if individus.get("validees", True):
        inscriptions = inscriptions.filter(statut="ok")
    if date_min:
        if individus.get("toute_periode"):
            inscriptions = inscriptions.filter(date_debut__lte=date_min).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_max))
        else:
            inscriptions = inscriptions.filter(date_debut__lte=date_max).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_min))

    non_trouves, ambigus = [], []
    if individus.get("type") == "liste":
        ids = set(Get_liste_entiers(individus.get("individus")))
        trouves, non_trouves, ambigus = Resoudre_liste(individus.get("texte", ""))
        ids |= trouves
        if not ids and not non_trouves and not ambigus:
            raise Erreur("Ajoutez au moins un individu à la liste")
        inscriptions = inscriptions.filter(individu_id__in=ids)
    else:
        groupes = Get_liste_entiers(individus.get("groupes"))
        if "groupes" in individus and not groupes:
            raise Erreur("Cochez au moins un groupe")
        if groupes:
            inscriptions = inscriptions.filter(groupe_id__in=groupes)
        categories = Get_liste_entiers(individus.get("categories"))
        if "categories" in individus and not categories:
            raise Erreur("Cochez au moins une catégorie de tarif")
        if categories:
            inscriptions = inscriptions.filter(categorie_tarif_id__in=categories)

    lignes = list(inscriptions.values_list("pk", "individu_id", "famille_id", "groupe_id", "categorie_tarif_id", "date_debut", "date_fin"))

    # Filtre scolarité
    if filtres.get("scolarite"):
        filtre = filtres["scolarite"]
        date_scolarite = Get_date(filtre.get("date")) or date_min or datetime.date.today()
        scolarites = Scolarite.objects.filter(date_debut__lte=date_scolarite, date_fin__gte=date_scolarite)
        if Get_liste_entiers(filtre.get("ecoles")):
            scolarites = scolarites.filter(ecole_id__in=Get_liste_entiers(filtre.get("ecoles")))
        if Get_liste_entiers(filtre.get("niveaux")):
            scolarites = scolarites.filter(niveau_id__in=Get_liste_entiers(filtre.get("niveaux")))
        scolarises = set(scolarites.filter(individu_id__in={l[1] for l in lignes}).values_list("individu_id", flat=True)) if lignes else set()
        lignes = [l for l in lignes if l[1] in scolarises]

    # Filtre âge (déchiffrement limité aux inscrits sélectionnés)
    nbre_sans_date_naiss = 0
    if filtres.get("age"):
        filtre = filtres["age"]
        age_min, age_max = Get_entier(filtre.get("min")), Get_entier(filtre.get("max"))
        if age_min is None and age_max is None:
            raise Erreur("Renseignez au moins un âge")
        date_reference = Get_date(filtre.get("date")) or date_min or datetime.date.today()
        dates_naiss = {pk: valeurs[0] for pk, valeurs in Get_valeurs(Individu, {l[1] for l in lignes}, ["date_naiss"]).items()}
        resultats = []
        for ligne in lignes:
            age = Calculer_age(dates_naiss.get(ligne[1]), date_reference)
            if age is None:
                nbre_sans_date_naiss += 1
            elif (age_min is None or age >= age_min) and (age_max is None or age <= age_max):
                resultats.append(ligne)
        lignes = resultats

    # Filtre selon les consommations déjà saisies sur les dates retenues
    if filtres.get("consommations") in ("avec", "sans") and dates:
        avec = set()
        for paquet in Par_paquets([l[0] for l in lignes]):
            avec |= set(Consommation.objects.filter(inscription_id__in=paquet, date__in=dates).values_list("inscription_id", flat=True).distinct())
        lignes = [l for l in lignes if (l[0] in avec) == (filtres["consommations"] == "avec")]

    noms = {pk: Get_nom_complet(*valeurs) for pk, valeurs in Get_valeurs(Individu, {l[1] for l in lignes}, ["nom", "prenom"]).items()}
    resultats = [{"inscription": l[0], "individu": l[1], "famille": l[2], "groupe": l[3], "categorie_tarif": l[4], "date_debut": l[5], "date_fin": l[6], "nom": noms.get(l[1], "")} for l in lignes]
    resultats.sort(key=lambda x: (Normaliser_texte(x["nom"]), x["inscription"]))
    return resultats, {"non_trouves": non_trouves[:50], "ambigus": ambigus[:50], "nbre_sans_date_naiss": nbre_sans_date_naiss}


def Rechercher_inscrits(activite=None, texte=""):
    termes = [terme for terme in texte.split() if terme]
    if not termes or len(texte.strip()) < 2:
        return []
    condition = Q(activite=activite)
    for terme in termes[:4]:
        condition &= (Q(individu__nom__icontains=terme) | Q(individu__prenom__icontains=terme))
    resultats = {}
    for idindividu, nom, prenom, groupe in Inscription.objects.filter(condition).values_list("individu_id", "individu__nom", "individu__prenom", "groupe__nom").order_by("individu__nom", "individu__prenom")[:30]:
        resultats.setdefault(idindividu, {"id": idindividu, "label": Get_nom_complet(nom, prenom), "groupes": set()})["groupes"].add(groupe)
    return [{"id": r["id"], "label": r["label"], "groupes": ", ".join(sorted(r["groupes"]))} for r in list(resultats.values())[:20]]


# ---------------------------------------------- Simulation ----------------------------------------------

class Simulation():
    """ Calcule, sans rien enregistrer, les opérations à réaliser pour chaque inscription.
    self.operations = {idinscription: [operation, ...]} avec operation = dict(statut, date, unite, evenement, heure_debut, heure_fin, quantite, etat, conso) """

    def __init__(self, parametres=None, request=None, inscriptions=None):
        self.p = Lire_parametres(parametres)
        self.request = request
        self.activite = Get_activite(self.p.get("idactivite"), request)
        self.action = self.p.get("action")
        if self.action not in ("ajouter", "modifier", "supprimer"):
            raise Erreur("Choisissez l'action à réaliser")
        resultat_dates = Calculer_dates(self.activite, self.p.get("periode") or {})
        self.dates = resultat_dates["dates"]
        if not self.dates:
            raise Erreur("Aucune date n'est retenue avec ces paramètres")
        self.Lire_unites()
        self.selection, self.infos_selection = Get_selection(self.p, self.activite, self.dates, request)
        if inscriptions is not None:
            inscriptions = set(inscriptions)
            self.selection = [ligne for ligne in self.selection if ligne["inscription"] in inscriptions]
        if len(self.selection) > NBRE_MAX_INSCRIPTIONS:
            raise Erreur("La sélection contient %d inscriptions : affinez-la (%d au maximum)" % (len(self.selection), NBRE_MAX_INSCRIPTIONS))
        self.operations = {}
        self.depassements = {}
        if self.selection:
            self.Charger_donnees()
            getattr(self, "Simuler_%s" % self.action)()

    # --------------------------- Lecture des paramètres ---------------------------

    def Lire_unites(self):
        parametres_unites = self.p.get("unites") or {}
        ids = Get_liste_entiers(parametres_unites.keys())
        if not ids:
            raise Erreur("Cochez au moins une unité")
        self.unites = {unite.pk: unite for unite in Unite.objects.prefetch_related("groupes", "incompatibilites").filter(activite=self.activite, pk__in=ids)}
        if len(self.unites) != len(set(ids)):
            raise Erreur("Une des unités n'appartient pas à cette activité")
        self.groupes_unites = {pk: {g.pk for g in unite.groupes.all()} for pk, unite in self.unites.items()}
        self.incompatibilites = {pk: {u.pk for u in unite.incompatibilites.all()} for pk, unite in self.unites.items()}

        # Vérifie que les unités choisies ne sont pas incompatibles entre elles
        if self.action == "ajouter":
            for pk, unite in self.unites.items():
                for autre in self.incompatibilites[pk] & set(self.unites):
                    raise Erreur("Les unités %s et %s sont incompatibles : décochez-en une" % (unite.nom, self.unites[autre].nom))

        # Paramètres de création par unité
        self.creations = {}
        self.evenements = {}
        if self.action == "ajouter":
            for pk, unite in self.unites.items():
                options = parametres_unites.get(str(pk)) or {}
                if unite.type == "Multihoraires":
                    plages = []
                    for plage in options.get("plages") or []:
                        debut, fin = Heure(plage[0] if len(plage) > 0 else None), Heure(plage[1] if len(plage) > 1 else None)
                        if not debut or not fin or debut >= fin:
                            raise Erreur("Les plages horaires de l'unité %s ne sont pas valides" % unite.nom)
                        plages.append((debut, fin))
                    if not plages:
                        raise Erreur("Ajoutez au moins une plage horaire pour l'unité %s" % unite.nom)
                    plages.sort()
                    for index in range(1, len(plages)):
                        if plages[index][0] < plages[index - 1][1]:
                            raise Erreur("Les plages horaires de l'unité %s se chevauchent" % unite.nom)
                    self.creations[pk] = [{"heure_debut": d, "heure_fin": f, "quantite": None} for d, f in plages]
                elif unite.type == "Horaire":
                    debut, fin = Heure(options.get("heure_debut")) or Heure(unite.heure_debut), Heure(options.get("heure_fin")) or Heure(unite.heure_fin)
                    if not debut or not fin or debut >= fin:
                        raise Erreur("Les horaires de l'unité %s ne sont pas valides" % unite.nom)
                    self.creations[pk] = [{"heure_debut": debut, "heure_fin": fin, "quantite": None}]
                elif unite.type == "Quantite":
                    quantite = Get_entier(options.get("quantite")) or 1
                    if quantite < 1:
                        raise Erreur("La quantité de l'unité %s n'est pas valide" % unite.nom)
                    self.creations[pk] = [{"heure_debut": Heure(unite.heure_debut), "heure_fin": Heure(unite.heure_fin), "quantite": quantite}]
                elif unite.type == "Evenement":
                    ids_evenements = Get_liste_entiers(options.get("evenements"))
                    if not ids_evenements:
                        raise Erreur("Cochez au moins un événement pour l'unité %s" % unite.nom)
                    for evenement in Evenement.objects.filter(pk__in=ids_evenements, unite=unite, activite=self.activite, date__in=self.dates):
                        self.evenements[evenement.pk] = evenement
                    self.creations[pk] = []
                else:
                    self.creations[pk] = [{"heure_debut": Heure(unite.heure_debut), "heure_fin": Heure(unite.heure_fin), "quantite": None}]
            self.etat = self.p.get("etat") if self.p.get("etat") in ("reservation", "attente", "present") else "reservation"
            self.regle_complet = self.p.get("complet") if self.p.get("complet") in ("attente", "ignorer", "forcer") else "attente"

        if self.action == "modifier":
            modifier = self.p.get("modifier") or {}
            self.etats_source = [etat for etat in modifier.get("etats_source", []) if etat in ETATS]
            self.etat_cible = modifier.get("etat_cible")
            if not self.etats_source:
                raise Erreur("Cochez au moins un état actuel")
            if self.etat_cible not in ETATS:
                raise Erreur("Choisissez le nouvel état")
            if self.etat_cible in self.etats_source and len(self.etats_source) == 1:
                raise Erreur("Le nouvel état doit être différent de l'état actuel")

        if self.action == "supprimer":
            self.etats_suppression = [etat for etat in (self.p.get("supprimer") or {}).get("etats", ["reservation", "attente", "demande", "refus"]) if etat in ETATS]
            if not self.etats_suppression:
                raise Erreur("Cochez au moins un état de consommation à supprimer")

    # --------------------------- Chargement des données ---------------------------

    def Charger_donnees(self):
        date_min, date_max = min(self.dates), max(self.dates)
        self.ensemble_dates = set(self.dates)
        ids_inscriptions = [ligne["inscription"] for ligne in self.selection]

        # Consommations existantes des inscriptions sélectionnées
        self.consos = {}
        champs = ("pk", "inscription_id", "date", "unite_id", "evenement_id", "heure_debut", "heure_fin", "etat", "forfait", "prestation__facture_id", "quantite")
        for paquet in Par_paquets(ids_inscriptions):
            for valeurs in Consommation.objects.filter(inscription_id__in=paquet, date__gte=date_min, date__lte=date_max).values_list(*champs):
                conso = dict(zip(champs, valeurs))
                self.consos.setdefault((conso["inscription_id"], conso["date"]), []).append(conso)

        if self.action != "ajouter":
            return

        # Ouvertures
        self.ouvertures = set(Ouverture.objects.filter(activite=self.activite, date__in=self.dates, unite_id__in=self.unites.keys()).values_list("date", "groupe_id", "unite_id"))

        # Capacités (unités de remplissage) et places déjà prises sur toute l'activité
        self.remplissage_unite = {}
        self.unites_remplissage = {}
        for unite_remplissage in UniteRemplissage.objects.prefetch_related("unites").filter(activite=self.activite):
            unites_conso = {u.pk for u in unite_remplissage.unites.all()}
            self.unites_remplissage[unite_remplissage.pk] = {"nom": unite_remplissage.nom, "unites": unites_conso}
            for pk in unites_conso & set(self.unites):
                self.remplissage_unite.setdefault(pk, []).append(unite_remplissage.pk)
        self.capacites = {(r.date, r.unite_remplissage_id, r.groupe_id or 0): r.places for r in Remplissage.objects.filter(activite=self.activite, date__in=self.dates) if r.places}
        self.places = {}
        if self.capacites:
            unites_suivies = set()
            for valeurs in self.unites_remplissage.values():
                unites_suivies |= valeurs["unites"]
            requete = Consommation.objects.filter(activite=self.activite, date__in=self.dates, etat__in=ETATS_PLACES, unite_id__in=unites_suivies)
            for ligne in requete.values("date", "unite", "groupe").annotate(nbre=Sum(Coalesce("quantite", Value(1), output_field=IntegerField()))):
                for idgroupe in (ligne["groupe"], 0):
                    cle = (ligne["date"], ligne["unite"], idgroupe)
                    self.places[cle] = self.places.get(cle, 0) + ligne["nbre"]
        self.places_evenements = {ligne["evenement"]: ligne["nbre"] for ligne in Consommation.objects.filter(evenement__in=self.evenements.keys(), etat__in=ETATS_PLACES).values("evenement").annotate(nbre=Count("pk"))}
        self.noms_groupes = dict(Groupe.objects.filter(activite=self.activite).values_list("pk", "nom"))

    # --------------------------- Ajouter ---------------------------

    def Places_restantes(self, date=None, idunite=None, idgroupe=None):
        """ Nombre de places restantes (None si illimité), selon la même règle que la grille """
        restantes = []
        for idunite_remplissage in self.remplissage_unite.get(idunite, []):
            for groupe in (idgroupe, 0):
                capacite = self.capacites.get((date, idunite_remplissage, groupe))
                if capacite:
                    prises = sum(self.places.get((date, idunite_conso, groupe), 0) for idunite_conso in self.unites_remplissage[idunite_remplissage]["unites"])
                    restantes.append((capacite - prises, idunite_remplissage, groupe, capacite))
        return min(restantes) if restantes else None

    def Simuler_ajouter(self):
        unites_triees = sorted(self.unites.values(), key=lambda u: (u.ordre, u.pk))
        for ligne in self.selection:
            operations = []
            for date in self.dates:
                hors_inscription = date < ligne["date_debut"] or (ligne["date_fin"] and date > ligne["date_fin"])
                existantes = self.consos.get((ligne["inscription"], date), [])
                for unite in unites_triees:
                    # Liste des créations à tenter pour cette unité ce jour-là
                    if unite.type == "Evenement":
                        creations = [{"heure_debut": Heure(e.heure_debut), "heure_fin": Heure(e.heure_fin), "quantite": None, "evenement": e}
                                     for e in self.evenements.values() if e.date == date and e.unite_id == unite.pk and e.groupe_id == ligne["groupe"]]
                    else:
                        creations = [dict(creation, evenement=None) for creation in self.creations[unite.pk]]
                    for creation in creations:
                        evenement = creation["evenement"]
                        operation = {"date": date, "unite": unite.pk, "evenement": evenement.pk if evenement else None, "heure_debut": creation["heure_debut"],
                                     "heure_fin": creation["heure_fin"], "quantite": creation["quantite"], "etat": self.etat, "multi": unite.type == "Multihoraires"}
                        operation["statut"] = self.Get_statut_creation(ligne, unite, date, operation, existantes, hors_inscription)
                        if operation["statut"] in ("creer", "attente"):
                            self.Reserver_place(ligne, unite, date, operation)
                        operations.append(operation)
            self.operations[ligne["inscription"]] = operations

    def Get_statut_creation(self, ligne={}, unite=None, date=None, operation={}, existantes=[], hors_inscription=False):
        if hors_inscription:
            return "hors_inscription"
        if self.groupes_unites[unite.pk] and ligne["groupe"] not in self.groupes_unites[unite.pk]:
            return "unite_groupe"
        if (unite.date_debut and date < unite.date_debut) or (unite.date_fin and date > unite.date_fin):
            return "unite_validite"
        if (date, ligne["groupe"], unite.pk) not in self.ouvertures:
            return "ferme"
        # Conso déjà existante sur la même case (ou chevauchement d'horaires pour les multihoraires)
        for conso in existantes:
            if conso["unite_id"] == unite.pk and conso["evenement_id"] == operation["evenement"]:
                if not operation["multi"]:
                    return "existe"
                debut, fin = Heure(conso["heure_debut"]), Heure(conso["heure_fin"])
                if not (debut and fin) or (operation["heure_debut"] < fin and debut < operation["heure_fin"]):
                    return "existe"
        # Unité incompatible déjà réservée
        for conso in existantes:
            if conso["etat"] in ETATS_ACTIFS and conso["unite_id"] in self.incompatibilites[unite.pk]:
                return "incompatible"
        # Capacité
        if self.etat in ETATS_PLACES and self.regle_complet != "forcer":
            complet = False
            quantite = operation["quantite"] or 1
            restantes = self.Places_restantes(date, unite.pk, ligne["groupe"])
            if restantes and restantes[0] < quantite:
                complet = True
                self.Noter_depassement((date, "remplissage", restantes[1], restantes[2]), restantes[3], date,
                                       "%s%s" % (self.unites_remplissage[restantes[1]]["nom"], (" · " + self.noms_groupes.get(restantes[2], "")) if restantes[2] else ""))
            evenement = self.evenements.get(operation["evenement"])
            if evenement and evenement.capacite_max and self.places_evenements.get(evenement.pk, 0) >= evenement.capacite_max:
                complet = True
                self.Noter_depassement((date, "evenement", evenement.pk), evenement.capacite_max, date, evenement.nom)
            if complet:
                return "attente" if self.regle_complet == "attente" else "complet"
        return "creer"

    def Noter_depassement(self, cle=None, capacite=0, date=None, libelle=""):
        depassement = self.depassements.setdefault(cle, {"date": str(date), "date_fr": Date_fr(date), "libelle": libelle, "capacite": capacite, "nbre": 0})
        depassement["nbre"] += 1

    def Reserver_place(self, ligne={}, unite=None, date=None, operation={}):
        if operation["statut"] == "attente":
            operation["etat"] = "attente"
            return
        if operation["etat"] not in ETATS_PLACES:
            return
        quantite = operation["quantite"] or 1
        for idgroupe in (ligne["groupe"], 0):
            cle = (date, unite.pk, idgroupe)
            self.places[cle] = self.places.get(cle, 0) + quantite
        if operation["evenement"]:
            self.places_evenements[operation["evenement"]] = self.places_evenements.get(operation["evenement"], 0) + 1

    # --------------------------- Modifier ---------------------------

    def Simuler_modifier(self):
        for ligne in self.selection:
            operations = []
            for date in self.dates:
                for conso in self.consos.get((ligne["inscription"], date), []):
                    if conso["unite_id"] not in self.unites or conso["etat"] not in self.etats_source or conso["etat"] == self.etat_cible:
                        continue
                    operation = {"date": date, "unite": conso["unite_id"], "evenement": conso["evenement_id"], "conso": conso["pk"], "etat": self.etat_cible, "etat_initial": conso["etat"]}
                    if conso["prestation__facture_id"]:
                        operation["statut"] = "facturee"
                    elif conso["forfait"]:
                        operation["statut"] = "forfait"
                    elif self.etat_cible in ETATS_POINTES and conso["etat"] in ("attente", "refus", "demande"):
                        operation["statut"] = "interdit"
                    else:
                        operation["statut"] = "modifier"
                    operations.append(operation)
            self.operations[ligne["inscription"]] = operations

    # --------------------------- Supprimer ---------------------------

    def Simuler_supprimer(self):
        for ligne in self.selection:
            operations = []
            for date in self.dates:
                for conso in self.consos.get((ligne["inscription"], date), []):
                    if conso["unite_id"] not in self.unites:
                        continue
                    if conso["etat"] not in self.etats_suppression and conso["etat"] not in ETATS_POINTES:
                        continue
                    operation = {"date": date, "unite": conso["unite_id"], "evenement": conso["evenement_id"], "conso": conso["pk"], "etat": conso["etat"]}
                    if conso["etat"] in ETATS_POINTES:
                        operation["statut"] = "pointee"
                    elif conso["prestation__facture_id"]:
                        operation["statut"] = "facturee"
                    elif conso["forfait"]:
                        operation["statut"] = "forfait"
                    else:
                        operation["statut"] = "supprimer"
                    operations.append(operation)
            self.operations[ligne["inscription"]] = operations

    # --------------------------- Résultats ---------------------------

    def Get_resultats(self):
        totaux = {}
        par_date = {}
        lignes = []
        noms_unites = {pk: unite.nom for pk, unite in self.unites.items()}
        noms_evenements = {pk: e.nom for pk, e in self.evenements.items()}
        for ligne in self.selection:
            compteurs = {}
            remarques = {}
            for operation in self.operations.get(ligne["inscription"], []):
                statut = operation["statut"]
                compteurs[statut] = compteurs.get(statut, 0) + 1
                totaux[statut] = totaux.get(statut, 0) + 1
                jour = par_date.setdefault(str(operation["date"]), {"date": str(operation["date"]), "date_fr": Date_fr(operation["date"])})
                jour[statut] = jour.get(statut, 0) + 1
                if statut not in ("creer", "modifier", "supprimer"):
                    libelle = noms_evenements.get(operation["evenement"]) or noms_unites.get(operation["unite"], "")
                    texte = "%s %s" % (libelle, operation["date"].strftime("%d/%m"))
                    if texte not in remarques.setdefault(statut, []):
                        remarques[statut].append(texte)
            a_traiter = sum(compteurs.get(statut, 0) for statut in STATUTS_ACTION)
            lignes.append({
                "inscription": ligne["inscription"], "individu": ligne["individu"], "famille": ligne["famille"], "nom": ligne["nom"],
                "groupe": ligne["groupe"], "compteurs": compteurs, "a_traiter": a_traiter,
                "remarques": [{"statut": statut, "texte": "%s : %s" % (STATUTS[statut], ", ".join(details[:4]) + ("..." if len(details) > 4 else ""))} for statut, details in remarques.items()],
            })
        depassements = sorted(self.depassements.values(), key=lambda d: (d["date"], d["libelle"]))
        return {
            "action": self.action,
            "nbre_dates": len(self.dates),
            "dates": [str(d) for d in self.dates],
            "nbre_inscriptions": len(self.selection),
            "totaux": totaux,
            "statuts": STATUTS,
            "lignes": lignes,
            "par_date": sorted(par_date.values(), key=lambda j: j["date"]),
            "depassements": depassements,
            "infos_selection": self.infos_selection,
        }


def Compter(parametres=None, request=None):
    """ Compteur de l'étape Individus (sans calcul des opérations) """
    p = Lire_parametres(parametres)
    activite = Get_activite(p.get("idactivite"), request)
    dates = Calculer_dates(activite, p.get("periode") or {})["dates"]
    if not dates:
        raise Erreur("Aucune date n'est retenue avec ces paramètres")
    selection, infos = Get_selection(p, activite, dates, request)
    par_groupe, par_categorie = {}, {}
    for ligne in selection:
        par_groupe[str(ligne["groupe"])] = par_groupe.get(str(ligne["groupe"]), 0) + 1
        par_categorie[str(ligne["categorie_tarif"])] = par_categorie.get(str(ligne["categorie_tarif"]), 0) + 1
    return dict(infos, nbre=len(selection), nbre_individus=len({ligne["individu"] for ligne in selection}), par_groupe=par_groupe, par_categorie=par_categorie)


# ---------------------------------------------- Application par paquets ----------------------------------------------

def Appliquer_paquet(parametres=None, inscriptions=None, premier=False, request=None):
    """ Applique le traitement aux inscriptions du paquet avec la grille virtuelle """
    from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
    debut = time.time()
    try:
        inscriptions = [int(x) for x in (json.loads(inscriptions) if isinstance(inscriptions, str) else (inscriptions or []))]
    except (TypeError, ValueError):
        raise Erreur("La liste des inscriptions n'est pas valide")
    if not inscriptions or len(inscriptions) > TAILLE_PAQUET * 2:
        raise Erreur("Le paquet d'inscriptions n'est pas valide")

    simulation = Simulation(parametres, request, inscriptions=inscriptions)
    if premier:
        request.session[CLE_SESSION] = {"activite": simulation.activite.pk, "action": simulation.action, "consommations": [], "horodatage": datetime.datetime.now().isoformat(timespec="seconds")}
    pk_max = Consommation.objects.aggregate(pk_max=Max("pk"))["pk_max"] or 0

    resultats = {"traites": 0, "erreurs": [], "totaux": {}, "lignes": []}
    for ligne in simulation.selection:
        operations = [op for op in simulation.operations.get(ligne["inscription"], []) if op["statut"] in STATUTS_ACTION]
        if not operations:
            resultats["traites"] += 1
            continue
        try:
            dates = [op["date"] for op in operations]
            grille = Grille_virtuelle(request=request, idfamille=ligne["famille"], idindividu=ligne["individu"], idactivite=simulation.activite.pk, date_min=min(dates), date_max=max(dates))
            for op in operations:
                if op["statut"] in ("creer", "attente"):
                    parametres_conso = {"etat": op["etat"], "heure_debut": op["heure_debut"], "heure_fin": op["heure_fin"]}
                    if op["quantite"]:
                        parametres_conso["quantite"] = op["quantite"]
                    grille.Ajouter(criteres={"date": str(op["date"]), "unite": op["unite"], "inscription": ligne["inscription"], "evenement": op["evenement"]},
                                   parametres=parametres_conso, plusieurs=op.get("multi", False))
                elif op["statut"] == "modifier":
                    grille.Modifier(criteres={"pk": op["conso"]}, modifications={"etat": op["etat"]})
                elif op["statut"] == "supprimer":
                    grille.Supprimer(criteres={"pk": op["conso"]})
            grille.Enregistrer()
        except Exception as err:
            logger.exception("%s : erreur sur l'inscription %s" % (LIBELLE_FONCTION, ligne["inscription"]))
            resultats["erreurs"].append({"nom": ligne["nom"], "message": "Erreur pendant l'enregistrement : %s" % err})
            continue
        resultats["traites"] += 1
        compteurs = {}
        for op in operations:
            compteurs[op["statut"]] = compteurs.get(op["statut"], 0) + 1
            resultats["totaux"][op["statut"]] = resultats["totaux"].get(op["statut"], 0) + 1
        resultats["lignes"].append({"nom": ligne["nom"], "inscription": ligne["inscription"], "famille": ligne["famille"], "individu": ligne["individu"], "compteurs": compteurs})

    # Mémorisation des consommations créées pour permettre l'annulation
    if simulation.action == "ajouter":
        crees = list(Consommation.objects.filter(pk__gt=pk_max, inscription_id__in=inscriptions, activite=simulation.activite).values_list("pk", flat=True))
        lot = request.session.get(CLE_SESSION) or {"activite": simulation.activite.pk, "action": "ajouter", "consommations": []}
        if lot.get("activite") == simulation.activite.pk:
            lot["consommations"] = lot.get("consommations", []) + crees
            request.session[CLE_SESSION] = lot
        resultats["nbre_crees"] = len(crees)
    resultats["duree"] = round(time.time() - debut, 2)
    return resultats


def Annuler_paquet(request=None):
    """ Supprime les consommations créées par le dernier traitement, par paquets d'inscriptions """
    from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
    lot = request.session.get(CLE_SESSION)
    if not lot or lot.get("action") != "ajouter" or not lot.get("consommations"):
        raise Erreur("Aucun traitement à annuler")
    activite = Get_activite(lot["activite"], request)
    par_inscription = {}
    for paquet in Par_paquets(lot["consommations"]):
        for valeurs in Consommation.objects.filter(pk__in=paquet, activite=activite).values_list("pk", "inscription_id", "inscription__famille_id", "individu_id", "date", "etat", "prestation__facture_id"):
            par_inscription.setdefault((valeurs[1], valeurs[2], valeurs[3]), []).append(valeurs)
    cles = sorted(par_inscription)[:TAILLE_PAQUET]
    supprimees, conservees = 0, 0
    for idinscription, idfamille, idindividu in cles:
        consos = par_inscription[(idinscription, idfamille, idindividu)]
        a_supprimer = [c for c in consos if c[5] not in ETATS_POINTES and not c[6]]
        conservees += len(consos) - len(a_supprimer)
        if a_supprimer:
            dates = [c[4] for c in a_supprimer]
            grille = Grille_virtuelle(request=request, idfamille=idfamille, idindividu=idindividu, idactivite=activite.pk, date_min=min(dates), date_max=max(dates))
            for conso in a_supprimer:
                grille.Supprimer(criteres={"pk": conso[0]})
            grille.Enregistrer()
            supprimees += len(a_supprimer)
    # Les consommations encore présentes des inscriptions non traitées restent à annuler
    lot["consommations"] = [c[0] for cle in sorted(par_inscription)[TAILLE_PAQUET:] for c in par_inscription[cle]]
    restantes = len(par_inscription) - len(cles)
    if restantes:
        request.session[CLE_SESSION] = lot
    else:
        request.session.pop(CLE_SESSION, None)
    return {"supprimees": supprimees, "conservees": conservees, "restantes": restantes}
