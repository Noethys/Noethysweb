# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Calcul des cycles des modèles de planning des collaborateurs (1, 2 ou 3 semaines, semaines paires/impaires, vacances) """

import datetime
from core.models import Vacance, Ferie, LigneModelePlanningCollaborateur, ModelePlanningCollaborateur
from core.utils import utils_dates

UNE_SEMAINE = datetime.timedelta(days=7)
LIMITE_RECHERCHE = 260  # Nombre maximal de semaines parcourues pour compter un cycle (5 ans)


def Lundi(date):
    return date - datetime.timedelta(days=date.weekday())


class Calendrier():
    """ Vacances et fériés, avec mémorisation des semaines déjà calculées """
    def __init__(self, vacances=None, feries=None):
        self.vacances = [(vacance.date_debut, vacance.date_fin) for vacance in (Vacance.objects.all() if vacances is None else vacances)]
        self.feries = list(Ferie.objects.all()) if feries is None else feries
        self.cache_semaines = {}

    def Est_vacances(self, date):
        return any(debut <= date <= fin for debut, fin in self.vacances)

    def Est_ferie(self, date):
        return bool(utils_dates.EstFerie(date, self.feries))

    def Est_semaine_vacances(self, lundi):
        """ Une semaine est une semaine de vacances si tous ses jours du lundi au vendredi sont en vacances """
        if lundi not in self.cache_semaines:
            self.cache_semaines[lundi] = all(self.Est_vacances(lundi + datetime.timedelta(days=n)) for n in range(5))
        return self.cache_semaines[lundi]

    def Annees_sans_vacances(self, annees=[]):
        return sorted(annee for annee in set(annees) if not any(debut.year <= annee <= fin.year for debut, fin in self.vacances))


def Get_ancrage(modele=None, premier_lundi=None, depart=None):
    """ Renvoie (lundi, semaine du cycle) servant de repère, ou None si le cycle ne dépend pas d'un repère """
    if modele.nb_semaines <= 1 or modele.reperage == "PARITE":
        return None
    if depart and 1 <= int(depart) <= modele.nb_semaines:
        return (premier_lundi, int(depart))
    if modele.reperage == "REFERENCE" and modele.date_reference:
        return (Lundi(modele.date_reference), 1)
    if modele.ancrage_date and modele.ancrage_semaine and 1 <= modele.ancrage_semaine <= modele.nb_semaines:
        return (Lundi(modele.ancrage_date), modele.ancrage_semaine)
    return (premier_lundi, 1)


def Get_origine_depart(modele=None, depart=None):
    """ Explique d'où vient la semaine de départ proposée """
    if modele.nb_semaines <= 1 or modele.reperage == "PARITE":
        return ""
    if depart:
        return "choisie"
    if modele.reperage == "REFERENCE" and modele.date_reference:
        return "Calculée depuis la date de référence du %s" % modele.date_reference.strftime("%d/%m/%Y")
    if modele.ancrage_date and modele.ancrage_semaine:
        return "Suite de la dernière application (semaine du %s en semaine %d)" % (Lundi(modele.ancrage_date).strftime("%d/%m/%Y"), modele.ancrage_semaine)
    return "Par défaut"


def Compter_semaines(debut, fin, calendrier):
    """ Nombre de semaines hors vacances dans [debut, fin[ """
    nbre, lundi, limite = 0, debut, 0
    while lundi < fin and limite < LIMITE_RECHERCHE:
        if not calendrier.Est_semaine_vacances(lundi):
            nbre += 1
        lundi += UNE_SEMAINE
        limite += 1
    return nbre


def Get_semaine_cycle(modele=None, lundi=None, ancrage=None, calendrier=None):
    """ Numéro de la semaine du cycle (1 à nb_semaines) pour la semaine commençant par lundi, ou None pour une semaine de vacances suspendue """
    nb = modele.nb_semaines
    if nb <= 1:
        return 1
    if modele.reperage == "PARITE":
        return 1 if lundi.isocalendar()[1] % 2 == 1 else 2

    lundi_ancre, semaine_ancre = ancrage
    if modele.vacances_cycle == "CONTINU":
        return (semaine_ancre - 1 + (lundi - lundi_ancre).days // 7) % nb + 1

    # Pause ou redémarrage : les semaines de vacances ne sont pas numérotées
    if calendrier.Est_semaine_vacances(lundi):
        return None

    # Si le repère tombe en vacances, la semaine choisie s'applique à la première semaine scolaire qui suit
    limite = 0
    while calendrier.Est_semaine_vacances(lundi_ancre) and limite < 52:
        lundi_ancre += UNE_SEMAINE
        limite += 1

    if modele.vacances_cycle == "RESTART":
        # Recherche de la dernière semaine de vacances précédant cette semaine (après le repère, ou dans les 5 ans avant)
        borne = lundi_ancre if lundi >= lundi_ancre else lundi - LIMITE_RECHERCHE * UNE_SEMAINE
        test = lundi - UNE_SEMAINE
        while test >= borne:
            if calendrier.Est_semaine_vacances(test):
                return Compter_semaines(test + UNE_SEMAINE, lundi, calendrier) % nb + 1
            test -= UNE_SEMAINE

    # Pause (ou redémarrage sans vacances depuis le repère)
    if lundi >= lundi_ancre:
        decalage = Compter_semaines(lundi_ancre, lundi, calendrier)
    else:
        decalage = -Compter_semaines(lundi, lundi_ancre, calendrier)
    return (semaine_ancre - 1 + decalage) % nb + 1


def Is_ligne_applicable(ligne=None, date=None, semaine=None, est_vacances=False, est_ferie=False):
    if ligne.jour != date.weekday():
        return False
    if est_ferie and not ligne.modele.inclure_feries:
        return False
    if (ligne.periode == "SCOLAIRES" and est_vacances) or (ligne.periode == "VACANCES" and not est_vacances):
        return False
    if ligne.semaine and ligne.semaine != semaine:
        return False
    return True


class Generateur():
    """ Détermine les lignes de modèles à appliquer sur chaque date """
    def __init__(self, modeles=[], dates=[], departs={}, calendrier=None):
        self.dates = sorted(set(dates))
        self.modeles = list(ModelePlanningCollaborateur.objects.filter(pk__in=[getattr(modele, "pk", modele) for modele in modeles]))
        self.calendrier = calendrier or Calendrier()
        self.departs = {int(cle): int(valeur) for cle, valeur in (departs or {}).items() if valeur}
        premier_lundi = Lundi(self.dates[0]) if self.dates else None
        self.ancrages = {modele.pk: Get_ancrage(modele, premier_lundi, self.departs.get(modele.pk)) for modele in self.modeles}
        self.cache = {}

    def Semaine(self, modele, lundi):
        cle = (modele.pk, lundi)
        if cle not in self.cache:
            self.cache[cle] = Get_semaine_cycle(modele, lundi, self.ancrages[modele.pk], self.calendrier)
        return self.cache[cle]

    def Get_lignes_par_date(self):
        """ Renvoie une liste de tuples (date, ligne) """
        dict_modeles = {modele.pk: modele for modele in self.modeles}
        lignes = list(LigneModelePlanningCollaborateur.objects.select_related("type_evenement").filter(modele__in=self.modeles).order_by("heure_debut"))
        for ligne in lignes:
            ligne.modele = dict_modeles[ligne.modele_id]
        resultats = []
        for date in self.dates:
            est_ferie = self.calendrier.Est_ferie(date)
            est_vacances = self.calendrier.Est_vacances(date)
            for ligne in lignes:
                semaine = self.Semaine(ligne.modele, Lundi(date))
                if Is_ligne_applicable(ligne, date, semaine, est_vacances, est_ferie):
                    resultats.append((date, ligne))
        return resultats

    def Memoriser_ancrages(self):
        """ Mémorise le repère utilisé pour proposer la suite du cycle lors de la prochaine application """
        for modele in self.modeles:
            ancrage = self.ancrages.get(modele.pk)
            if ancrage and modele.reperage == "APPLICATION" and (modele.ancrage_date, modele.ancrage_semaine) != ancrage:
                ModelePlanningCollaborateur.objects.filter(pk=modele.pk).update(ancrage_date=ancrage[0], ancrage_semaine=ancrage[1])

    def Get_frise(self):
        """ Correspondance entre les semaines de la période et les semaines du cycle de chaque modèle """
        lundis = sorted(set(Lundi(date) for date in self.dates))
        semaines = [{"lundi": str(lundi), "num": lundi.isocalendar()[1], "annee": lundi.isocalendar()[0],
                     "vacances": self.calendrier.Est_semaine_vacances(lundi),
                     "jours_vacances": sum(1 for n in range(7) if self.calendrier.Est_vacances(lundi + datetime.timedelta(days=n)))} for lundi in lundis]
        nbre_lignes = {}
        for ligne in LigneModelePlanningCollaborateur.objects.filter(modele__in=self.modeles).values("modele_id", "periode"):
            nbre_lignes.setdefault(ligne["modele_id"], []).append(ligne["periode"])

        modeles, alertes = [], []
        for modele in sorted(self.modeles, key=lambda m: m.nom):
            noms = modele.Get_noms_semaines()
            valeurs = [self.Semaine(modele, lundi) for lundi in lundis]
            ancrage = self.ancrages.get(modele.pk)
            depart = None
            if ancrage and lundis:
                depart = valeurs[0] if valeurs[0] else next((valeur for valeur in valeurs if valeur), None)
            modeles.append({
                "id": modele.pk, "nom": modele.nom, "nb_semaines": modele.nb_semaines, "reperage": modele.reperage,
                "vacances_cycle": modele.vacances_cycle, "libelle_cycle": modele.Get_libelle_cycle(), "noms_semaines": noms,
                "depart_modifiable": bool(ancrage), "depart": depart, "origine_depart": Get_origine_depart(modele, self.departs.get(modele.pk)),
                "valeurs": valeurs,
            })

            # Alertes
            if modele.nb_semaines == 2 and modele.reperage == "PARITE":
                for index in range(1, len(lundis)):
                    if valeurs[index] == valeurs[index - 1]:
                        alertes.append("%s : la semaine %d de %d et la semaine %d de %d sont toutes les deux %s." % (
                            modele.nom, semaines[index - 1]["num"], semaines[index - 1]["annee"], semaines[index]["num"], semaines[index]["annee"],
                            "impaires" if valeurs[index] == 1 else "paires"))
            utilise_vacances = modele.vacances_cycle in ("PAUSE", "RESTART") and modele.nb_semaines > 1 and modele.reperage != "PARITE"
            if utilise_vacances or any(periode != "TOUTES" for periode in nbre_lignes.get(modele.pk, [])):
                annees = {date.year for date in self.dates}
                if utilise_vacances and ancrage:
                    annees.update(range(min(ancrage[0].year, min(annees)), max(annees) + 1))
                for annee in self.calendrier.Annees_sans_vacances(annees):
                    alerte = "Aucune période de vacances n'est saisie pour l'année %d : toutes ses semaines sont considérées comme scolaires." % annee
                    if alerte not in alertes:
                        alertes.append(alerte)
        return {"semaines": semaines, "modeles": modeles, "alertes": alertes}


def Get_departs(request=None, nom="departs"):
    """ Récupère les semaines de départ choisies {idmodele: semaine} depuis une requête """
    import json
    try:
        departs = json.loads(request.POST.get(nom) or "{}")
        return {int(cle): int(valeur) for cle, valeur in departs.items() if valeur}
    except (TypeError, ValueError, AttributeError):
        return {}


# ------------------------------------------------- Restrictions des modèles -------------------------------------------------

CATEGORIE_PARAMETRES = "modeles_planning_collaborateurs"


def Get_restrictions(modeles=[]):
    """ Renvoie {idmodele: {"groupes": {...}, "postes": {...}, "collaborateurs": {...}}} """
    restrictions = {getattr(modele, "pk", modele): {"groupes": set(), "postes": set(), "collaborateurs": set()} for modele in modeles}
    ids = list(restrictions.keys())
    for nom, through, champ in [("groupes", ModelePlanningCollaborateur.groupes.through, "groupecollaborateurs_id"),
                                ("postes", ModelePlanningCollaborateur.postes.through, "typepostecollaborateur_id"),
                                ("collaborateurs", ModelePlanningCollaborateur.collaborateurs.through, "collaborateur_id")]:
        for idmodele, valeur in through.objects.filter(modeleplanningcollaborateur_id__in=ids).values_list("modeleplanningcollaborateur_id", champ):
            restrictions[idmodele][nom].add(valeur)
    return restrictions


def Est_restreint(restriction=None):
    return bool(restriction and (restriction["groupes"] or restriction["postes"] or restriction["collaborateurs"]))


def Get_postes(collaborateurs=[], date=None):
    """ Poste de chaque collaborateur, vérifié une seule fois : contrat en cours à la date, sinon prochain contrat qui commence """
    from core.models import ContratCollaborateur
    postes = {}
    for contrat in ContratCollaborateur.objects.filter(collaborateur_id__in=collaborateurs).order_by("date_debut"):
        if contrat.date_fin and contrat.date_fin < date:
            continue
        en_cours = contrat.date_debut <= date
        actuel = postes.get(contrat.collaborateur_id)
        if en_cours or not actuel:
            postes[contrat.collaborateur_id] = contrat.type_poste_id
    return postes


def Get_groupes(collaborateurs=[]):
    from core.models import Collaborateur
    groupes = {}
    for idcollaborateur, idgroupe in Collaborateur.groupes.through.objects.filter(collaborateur_id__in=collaborateurs).values_list("collaborateur_id", "groupecollaborateurs_id"):
        groupes.setdefault(idcollaborateur, set()).add(idgroupe)
    return groupes


def Get_eligibles(modeles=[], collaborateurs=[], date=None, restrictions=None):
    """ Renvoie {idmodele: set des collaborateurs auxquels le modèle est proposé} """
    restrictions = restrictions or Get_restrictions(modeles)
    groupes = Get_groupes(collaborateurs)
    postes = Get_postes(collaborateurs, date or datetime.date.today())
    resultat = {}
    for idmodele, restriction in restrictions.items():
        if not Est_restreint(restriction):
            resultat[idmodele] = set(collaborateurs)
            continue
        resultat[idmodele] = {idcollaborateur for idcollaborateur in collaborateurs if idcollaborateur in restriction["collaborateurs"]
                              or groupes.get(idcollaborateur, set()) & restriction["groupes"] or postes.get(idcollaborateur) in restriction["postes"]}
    return resultat


def Get_texte_restriction(modele=None):
    """ Texte décrivant à qui le modèle est proposé """
    morceaux = [groupe.nom for groupe in modele.groupes.all().order_by("nom")]
    morceaux += ["poste %s" % poste.nom for poste in modele.postes.all().order_by("nom")]
    morceaux += [collaborateur.Get_nom() for collaborateur in modele.collaborateurs.all().order_by("nom", "prenom")]
    return ", ".join(morceaux)


def Repartir(modeles=[], collaborateurs=[], date=None, forcer=False):
    """ Détermine à quels collaborateurs appliquer chaque modèle. Renvoie ({idmodele: [idcollaborateurs]}, [messages]) """
    from core.models import Collaborateur
    modeles = list(ModelePlanningCollaborateur.objects.filter(pk__in=[getattr(modele, "pk", modele) for modele in modeles]))
    collaborateurs = [getattr(collaborateur, "pk", collaborateur) for collaborateur in collaborateurs]
    eligibles = Get_eligibles(modeles, collaborateurs, date)
    noms = {collaborateur.pk: collaborateur.Get_nom() for collaborateur in Collaborateur.objects.filter(pk__in=collaborateurs)}
    repartition, messages = {}, []
    for modele in modeles:
        concernes = [idcollaborateur for idcollaborateur in collaborateurs if idcollaborateur in eligibles[modele.pk]]
        exclus = [idcollaborateur for idcollaborateur in collaborateurs if idcollaborateur not in eligibles[modele.pk]]
        if forcer or not concernes:
            repartition[modele.pk] = list(collaborateurs)
            if exclus:
                messages.append("%s : appliqué à titre exceptionnel à %s, à qui il n'est pas proposé" % (modele.nom, Texte_noms([noms.get(i, "") for i in exclus])))
        else:
            repartition[modele.pk] = concernes
            if exclus:
                messages.append("%s : non appliqué à %s (non proposé)" % (modele.nom, Texte_noms([noms.get(i, "") for i in exclus])))
    return repartition, messages


def Texte_noms(noms=[], maxi=3):
    if len(noms) <= maxi:
        return ", ".join(noms)
    return "%s et %d autres" % (", ".join(noms[:maxi]), len(noms) - maxi)


# ------------------------------------------------- Liste pour le sélecteur -------------------------------------------------

def Get_recents(utilisateur=None):
    from core.utils import utils_parametres
    return utils_parametres.Get(nom="recents", categorie=CATEGORIE_PARAMETRES, utilisateur=utilisateur, valeur=[]) or []


def Memoriser_recents(utilisateur=None, modeles=[]):
    from core.utils import utils_parametres
    ids = [getattr(modele, "pk", modele) for modele in modeles]
    recents = ids + [idmodele for idmodele in Get_recents(utilisateur) if idmodele not in ids]
    utils_parametres.Set(nom="recents", categorie=CATEGORIE_PARAMETRES, utilisateur=utilisateur, valeur=recents[:5])


def Get_heures_hebdo(lignes=[], nb_semaines=1):
    """ Temps comptabilisé moyen par semaine scolaire (en heures) """
    total = 0
    for ligne in lignes:
        if ligne.periode == "VACANCES" or not ligne.type_evenement:
            continue
        duree = (datetime.datetime.combine(datetime.date.today(), ligne.heure_fin) - datetime.datetime.combine(datetime.date.today(), ligne.heure_debut)).total_seconds() / 60
        if duree <= 0:
            duree += 1440
        nbre = 1 if ligne.semaine else max(nb_semaines, 1)
        signe = {"ADDITION": 1, "SOUSTRACTION": -1}.get(ligne.type_evenement.type, 0)
        total += signe * duree * nbre
    return round(total / max(nb_semaines, 1) / 60, 2)


def Get_liste_modeles(utilisateur=None, collaborateurs=[], date=None):
    """ Liste des modèles pour le sélecteur, avec le nombre de collaborateurs concernés """
    modeles = list(ModelePlanningCollaborateur.objects.prefetch_related("groupes", "postes", "collaborateurs").order_by("nom"))
    lignes = {}
    for ligne in LigneModelePlanningCollaborateur.objects.select_related("type_evenement").filter(modele__in=modeles):
        lignes.setdefault(ligne.modele_id, []).append(ligne)
    restrictions = {modele.pk: {"groupes": {g.pk for g in modele.groupes.all()}, "postes": {p.pk for p in modele.postes.all()},
                                "collaborateurs": {c.pk for c in modele.collaborateurs.all()}} for modele in modeles}
    eligibles = Get_eligibles(modeles, collaborateurs, date, restrictions=restrictions) if collaborateurs else {}
    recents = Get_recents(utilisateur)
    resultat = []
    for modele in modeles:
        resultat.append({
            "id": modele.pk, "nom": modele.nom, "nb_semaines": modele.nb_semaines, "cycle": modele.Get_libelle_cycle(),
            "heures": Get_heures_hebdo(lignes.get(modele.pk, []), modele.nb_semaines),
            "restreint": Est_restreint(restrictions[modele.pk]),
            "restriction": ", ".join([g.nom for g in modele.groupes.all()] + ["poste %s" % p.nom for p in modele.postes.all()] + [c.Get_nom() for c in modele.collaborateurs.all()]),
            "eligibles": len(eligibles.get(modele.pk, [])) if collaborateurs else None,
            "recent": recents.index(modele.pk) if modele.pk in recents else None,
        })
    return {"modeles": resultat, "nbre_collaborateurs": len(collaborateurs)}
