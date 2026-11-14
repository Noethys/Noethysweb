# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Contrôle réglementaire du temps de travail des collaborateurs.
    Les anomalies sont de simples alertes : elles n'empêchent jamais l'enregistrement.
    Seuls les évènements dont la catégorie est en temps comptabilisé (ADDITION) sont pris en compte.
    Une journée regroupe les périodes de travail qui commencent à cette date (un travail de nuit compte pour le jour où il commence). """

import datetime
from django.db.models import Q
from core.models import EvenementCollaborateur, TypeEvenementCollaborateur, ContratCollaborateur, ProfilReglementaireCollaborateur

REGLES = [
    {"code": "duree_max_jour", "court": "Jour", "libelle": "Durée maximale par jour"},
    {"code": "amplitude_max_jour", "court": "Amplitude", "libelle": "Amplitude maximale de la journée"},
    {"code": "repos_quotidien_min", "court": "Repos quotidien", "libelle": "Repos quotidien minimal"},
    {"code": "duree_max_semaine", "court": "Semaine", "libelle": "Durée maximale par semaine"},
    {"code": "moyenne_max_12_semaines", "court": "Moyenne 12 sem.", "libelle": "Moyenne hebdomadaire maximale sur 12 semaines"},
    {"code": "repos_hebdo_min", "court": "Repos hebdo", "libelle": "Repos hebdomadaire minimal"},
    {"code": "jours_consecutifs_max", "court": "Jours consécutifs", "libelle": "Jours travaillés consécutifs maximum"},
]

NBRE_SEMAINES_MOYENNE = 12
UNE_MINUTE = datetime.timedelta(minutes=1)


def Format_minutes(minutes=0):
    minutes = int(round(minutes))
    return "%dh%02d" % (minutes // 60, minutes % 60)


def Format_valeur_regle(code="", valeur=None):
    if valeur is None:
        return ""
    if code == "jours_consecutifs_max":
        return "%d j" % valeur
    return Format_minutes(valeur)


def Format_date(date=None):
    return date.strftime("%d/%m")


def Lundi(date=None):
    return date - datetime.timedelta(days=date.weekday())


def Minutes(debut=None, fin=None):
    return (fin - debut).total_seconds() / 60


class Profils():
    """ Profil réglementaire applicable à un collaborateur à une date : celui du contrat en cours, sinon le profil par défaut """
    def __init__(self, collaborateurs=None):
        self.defaut = ProfilReglementaireCollaborateur.objects.filter(defaut=True).first()
        self.contrats = {}
        contrats = ContratCollaborateur.objects.select_related("profil_reglementaire").order_by("date_debut")
        if collaborateurs is not None:
            contrats = contrats.filter(collaborateur_id__in=collaborateurs)
        for contrat in contrats:
            self.contrats.setdefault(contrat.collaborateur_id, []).append(contrat)

    def Get(self, idcollaborateur=None, date=None):
        for contrat in self.contrats.get(idcollaborateur, []):
            if contrat.date_debut <= date and (not contrat.date_fin or date <= contrat.date_fin):
                return contrat.profil_reglementaire or self.defaut
        return self.defaut

    def Existe(self, idcollaborateur=None):
        return bool(self.defaut) or any(contrat.profil_reglementaire_id for contrat in self.contrats.get(idcollaborateur, []))


class Controle():
    def __init__(self, date_debut=None, date_fin=None, collaborateurs=None, simulation=[], supprimes=[]):
        """ collaborateurs : liste d'IDs ou None pour tous.
            simulation : évènements non enregistrés à contrôler (dict au format du planning, remplacent ceux de même ID).
            supprimes : IDs d'évènements à ignorer. """
        self.date_debut, self.date_fin = date_debut, date_fin
        self.collaborateurs = collaborateurs
        self.simulation = simulation or []
        self.supprimes = set(supprimes or [])
        self.anomalies = []

    # ------------------------------------------------- Chargement -------------------------------------------------

    def Charger(self):
        """ Renvoie {idcollaborateur: [(debut, fin, idevenement), ...]} des périodes de travail, avec une marge autour de la période contrôlée """
        self.charge_debut = Lundi(self.date_debut) - datetime.timedelta(weeks=NBRE_SEMAINES_MOYENNE)
        self.charge_fin = self.date_fin + datetime.timedelta(days=15)
        debut = datetime.datetime.combine(self.charge_debut, datetime.time(0))
        fin = datetime.datetime.combine(self.charge_fin, datetime.time(0))

        categories_travail = set(TypeEvenementCollaborateur.objects.filter(type="ADDITION").values_list("pk", flat=True))
        evenements = {}
        conditions = Q(date_debut__lt=fin, date_fin__gt=debut, type_evenement_id__in=categories_travail)
        if self.collaborateurs is not None:
            conditions &= Q(collaborateur_id__in=self.collaborateurs)
        champs = ("pk", "collaborateur_id", "type_evenement_id", "date_debut", "date_fin", "realise_debut", "realise_fin")
        for valeurs in EvenementCollaborateur.objects.filter(conditions).values_list(*champs):
            if valeurs[0] not in self.supprimes:
                evenements[valeurs[0]] = valeurs

        # Evènements simulés (modification en cours non enregistrée)
        for evt in self.simulation:
            idevenement = evt.get("id") or "nouveau_%d" % len(evenements)
            evenements.pop(idevenement, None)
            if evt.get("cat") in categories_travail and evt.get("d") and evt.get("f"):
                evenements[idevenement] = (idevenement, evt["c"], evt["cat"], evt["d"], evt["f"], evt.get("rd"), evt.get("rf"))

        self.profils = Profils(collaborateurs=self.collaborateurs)
        periodes = {}
        for idevenement, idcollaborateur, idcategorie, date_debut, date_fin, realise_debut, realise_fin in evenements.values():
            if not self.profils.Existe(idcollaborateur):
                continue
            profil = self.profils.Get(idcollaborateur, date_debut.date())
            if profil and profil.utiliser_realise and realise_debut and realise_fin and realise_fin > realise_debut:
                date_debut, date_fin = realise_debut, realise_fin
            if date_fin > date_debut:
                periodes.setdefault(idcollaborateur, []).append((date_debut, date_fin, idevenement))
        return periodes

    # ------------------------------------------------- Calcul -------------------------------------------------

    def Calculer(self):
        for idcollaborateur, periodes in self.Charger().items():
            self.Controler_collaborateur(idcollaborateur, sorted(periodes, key=lambda periode: (periode[0], periode[1])))
        self.anomalies = [anomalie for anomalie in self.anomalies if any(self.date_debut <= date <= self.date_fin for date in anomalie["dates"])]
        self.anomalies.sort(key=lambda anomalie: (anomalie["date"], anomalie["c"], anomalie["regle"]))
        return [dict(anomalie, date=str(anomalie["date"]), dates=[str(date) for date in anomalie["dates"]]) for anomalie in self.anomalies]

    def Ajouter(self, idcollaborateur=None, regle="", date=None, dates=None, texte="", evenements=[]):
        self.anomalies.append({"c": idcollaborateur, "regle": regle, "date": date, "dates": sorted(set(dates or [date])),
                               "texte": texte, "evts": sorted(set(evenements), key=str)})

    def Controler_collaborateur(self, idcollaborateur=None, periodes=[]):
        profil = lambda date: self.profils.Get(idcollaborateur, date)

        # Fusion des périodes qui se chevauchent ou se touchent (travail continu)
        blocs = []
        for debut, fin, idevenement in periodes:
            if blocs and debut <= blocs[-1]["fin"]:
                blocs[-1]["fin"] = max(blocs[-1]["fin"], fin)
                blocs[-1]["evts"].append(idevenement)
            else:
                blocs.append({"debut": debut, "fin": fin, "evts": [idevenement]})
        if not blocs:
            return

        # Regroupement par journée (date de début du travail)
        journees = {}
        for bloc in blocs:
            journee = journees.setdefault(bloc["debut"].date(), {"debut": bloc["debut"], "fin": bloc["fin"], "minutes": 0, "blocs": []})
            journee["fin"] = max(journee["fin"], bloc["fin"])
            journee["minutes"] += Minutes(bloc["debut"], bloc["fin"])
            journee["blocs"].append(bloc)
        dates = sorted(journees.keys())
        evts_journee = lambda date: [idevenement for bloc in journees[date]["blocs"] for idevenement in bloc["evts"]]

        # Règles journalières
        for date in dates:
            journee, regles = journees[date], profil(date)
            if not regles:
                continue
            if regles.duree_max_jour and journee["minutes"] > regles.duree_max_jour:
                self.Ajouter(idcollaborateur, "duree_max_jour", date, texte="Durée de travail de la journée : %s (max. %s)" % (Format_minutes(journee["minutes"]), Format_minutes(regles.duree_max_jour)),
                             evenements=evts_journee(date))
            amplitude = Minutes(journee["debut"], journee["fin"])
            if regles.amplitude_max_jour and amplitude > regles.amplitude_max_jour:
                self.Ajouter(idcollaborateur, "amplitude_max_jour", date, texte="Amplitude de la journée : %s, de %s à %s (max. %s)" % (
                    Format_minutes(amplitude), journee["debut"].strftime("%Hh%M"), journee["fin"].strftime("%Hh%M"), Format_minutes(regles.amplitude_max_jour)), evenements=evts_journee(date))

        # Repos quotidien entre deux journées travaillées
        for date_precedente, date in zip(dates, dates[1:]):
            regles = profil(date)
            if not regles or not regles.repos_quotidien_min:
                continue
            repos = Minutes(journees[date_precedente]["fin"], journees[date]["debut"])
            if repos < regles.repos_quotidien_min:
                self.Ajouter(idcollaborateur, "repos_quotidien_min", date, dates=[date_precedente, date],
                             texte="Repos entre le %s et le %s : %s (min. %s)" % (Format_date(date_precedente), Format_date(date), Format_minutes(max(repos, 0)), Format_minutes(regles.repos_quotidien_min)),
                             evenements=journees[date_precedente]["blocs"][-1]["evts"] + journees[date]["blocs"][0]["evts"])

        # Pause : travail sans interruption suffisante au-delà de la durée autorisée
        chaine = None
        for bloc in blocs + [None]:
            regles = profil(chaine["debut"].date()) if chaine else None
            duree_pause = regles.pause_duree if regles and regles.pause_duree and regles.pause_apres else None
            if chaine and bloc and duree_pause and Minutes(chaine["fin"], bloc["debut"]) < duree_pause:
                chaine["fin"] = max(chaine["fin"], bloc["fin"])
                chaine["evts"] += bloc["evts"]
                continue
            if chaine and duree_pause and Minutes(chaine["debut"], chaine["fin"]) > regles.pause_apres:
                self.Ajouter(idcollaborateur, "pause", chaine["debut"].date(), texte="Pause de %s manquante : travail continu de %s, de %s à %s (pause obligatoire après %s)" % (
                    Format_minutes(duree_pause), Format_minutes(Minutes(chaine["debut"], chaine["fin"])), chaine["debut"].strftime("%Hh%M"), chaine["fin"].strftime("%Hh%M"),
                    Format_minutes(regles.pause_apres)), evenements=chaine["evts"])
            chaine = {"debut": bloc["debut"], "fin": bloc["fin"], "evts": list(bloc["evts"])} if bloc else None

        # Jours travaillés consécutifs
        serie = []
        for date in dates + [None]:
            if date and serie and date - serie[-1] == datetime.timedelta(days=1):
                serie.append(date)
                continue
            regles = profil(serie[-1]) if serie else None
            if regles and regles.jours_consecutifs_max and len(serie) > regles.jours_consecutifs_max:
                exces = serie[regles.jours_consecutifs_max:]
                self.Ajouter(idcollaborateur, "jours_consecutifs_max", exces[0], dates=exces, texte="%d jours travaillés consécutifs, du %s au %s (max. %d)" % (
                    len(serie), Format_date(serie[0]), Format_date(serie[-1]), regles.jours_consecutifs_max), evenements=[idevenement for jour in exces for idevenement in evts_journee(jour)])
            serie = [date] if date else []

        # Règles hebdomadaires (semaines civiles du lundi au dimanche)
        semaines = {}
        for date in dates:
            semaines.setdefault(Lundi(date), []).append(date)
        minutes_semaine = lambda lundi: sum(journees[date]["minutes"] for date in semaines.get(lundi, []))
        for lundi, dates_semaine in sorted(semaines.items()):
            if lundi + datetime.timedelta(days=6) < self.date_debut or lundi > self.date_fin:
                continue
            regles = profil(dates_semaine[0])
            if not regles:
                continue

            # Durée maximale par semaine : signalée le jour où le cumul dépasse le maximum
            if regles.duree_max_semaine and minutes_semaine(lundi) > regles.duree_max_semaine:
                cumul, date_depassement = 0, dates_semaine[-1]
                for date in dates_semaine:
                    cumul += journees[date]["minutes"]
                    if cumul > regles.duree_max_semaine:
                        date_depassement = date
                        break
                self.Ajouter(idcollaborateur, "duree_max_semaine", date_depassement, dates=dates_semaine, texte="Durée de travail de la semaine du %s : %s (max. %s)" % (
                    Format_date(lundi), Format_minutes(minutes_semaine(lundi)), Format_minutes(regles.duree_max_semaine)))

            # Moyenne sur 12 semaines consécutives se terminant par cette semaine
            if regles.moyenne_max_12_semaines:
                premier_lundi = lundi - datetime.timedelta(weeks=NBRE_SEMAINES_MOYENNE - 1)
                moyenne = sum(minutes_semaine(premier_lundi + datetime.timedelta(weeks=index)) for index in range(NBRE_SEMAINES_MOYENNE)) / NBRE_SEMAINES_MOYENNE
                if moyenne > regles.moyenne_max_12_semaines:
                    self.Ajouter(idcollaborateur, "moyenne_max_12_semaines", dates_semaine[-1], dates=dates_semaine, texte="Moyenne hebdomadaire sur 12 semaines (du %s au %s) : %s (max. %s)" % (
                        Format_date(premier_lundi), Format_date(lundi + datetime.timedelta(days=6)), Format_minutes(moyenne), Format_minutes(regles.moyenne_max_12_semaines)))

            # Repos hebdomadaire : plus long repos continu qui touche la semaine
            if regles.repos_hebdo_min:
                debut_semaine = datetime.datetime.combine(lundi, datetime.time(0))
                fin_semaine = debut_semaine + datetime.timedelta(days=7)
                limite_debut = datetime.datetime.combine(self.charge_debut, datetime.time(0))
                limite_fin = datetime.datetime.combine(self.charge_fin, datetime.time(0))
                bornes = [(limite_debut, limite_debut)] + [(bloc["debut"], bloc["fin"]) for bloc in blocs] + [(limite_fin, limite_fin)]
                repos_max = 0
                for (_, fin_travail), (debut_travail, _) in zip(bornes, bornes[1:]):
                    if fin_travail < fin_semaine and debut_travail > debut_semaine:
                        # Les bornes de la période chargée ne limitent pas le repos (travail inconnu au-delà)
                        if fin_travail == limite_debut or debut_travail == limite_fin:
                            repos_max = float("inf")
                        repos_max = max(repos_max, Minutes(fin_travail, debut_travail))
                if repos_max < regles.repos_hebdo_min:
                    self.Ajouter(idcollaborateur, "repos_hebdo_min", dates_semaine[-1], dates=dates_semaine, texte="Repos hebdomadaire le plus long de la semaine du %s : %s (min. %s)" % (
                        Format_date(lundi), Format_minutes(repos_max), Format_minutes(regles.repos_hebdo_min)))


def Lire_simulation(texte="[]"):
    """ Evènements simulés envoyés par le planning (format Serialiser_evenement) """
    import json
    from collaborateurs.utils.utils_planning import Parse_datetime
    simulation = []
    try:
        for evt in json.loads(texte or "[]")[:500]:
            simulation.append({"id": int(evt["id"]) if evt.get("id") else None, "c": int(evt["c"]), "cat": int(evt["cat"]) if evt.get("cat") else None,
                               "d": Parse_datetime(evt.get("d")), "f": Parse_datetime(evt.get("f")), "rd": Parse_datetime(evt.get("rd")), "rf": Parse_datetime(evt.get("rf"))})
    except (TypeError, ValueError, KeyError):
        return None
    return simulation


def Get_anomalies(date_debut=None, date_fin=None, collaborateurs=None, simulation=[], supprimes=[]):
    return Controle(date_debut=date_debut, date_fin=date_fin, collaborateurs=collaborateurs, simulation=simulation, supprimes=supprimes).Calculer()


def Get_profil_dict(profil=None):
    """ Résumé lisible des règles d'un profil """
    if not profil:
        return None
    regles = [{"libelle": regle["libelle"], "valeur": Format_valeur_regle(regle["code"], getattr(profil, regle["code"]))} for regle in REGLES if getattr(profil, regle["code"]) is not None]
    if profil.pause_duree and profil.pause_apres:
        regles.append({"libelle": "Pause obligatoire", "valeur": "%s après %s" % (Format_minutes(profil.pause_duree), Format_minutes(profil.pause_apres))})
    return {"id": profil.pk, "nom": profil.nom, "regles": regles}
