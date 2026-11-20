# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Limitations des réservations par catégorie d'événements (ex : 3 événements max par semaine).

Sont comptées toutes les consommations de l'individu sur des événements de la catégorie, quel que soit leur état.
La semaine va du lundi au dimanche (ISO), l'année est l'année civile.
"""

import datetime, calendar
from core.models import Consommation, LimitationCategorieEvenement

MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def Get_bornes_periode(regle, date):
    """ Renvoie (date_debut, date_fin) de la période de la règle contenant la date, ou None si la date n'est pas concernée """
    if regle.periode == "JOUR":
        return date, date
    if regle.periode == "SEMAINE":
        lundi = date - datetime.timedelta(days=date.weekday())
        return lundi, lundi + datetime.timedelta(days=6)
    if regle.periode == "MOIS":
        return date.replace(day=1), date.replace(day=calendar.monthrange(date.year, date.month)[1])
    if regle.periode == "ANNEE":
        return datetime.date(date.year, 1, 1), datetime.date(date.year, 12, 31)
    if regle.periode == "PERIODE" and regle.date_debut and regle.date_fin and regle.date_debut <= date <= regle.date_fin:
        return regle.date_debut, regle.date_fin
    return None


def Get_label_periode(regle, bornes):
    """ Texte de la période pour les messages. Ex : 'par semaine (semaine du 12/07/2027)' """
    debut, fin = bornes
    if regle.periode == "JOUR":
        return "par jour (le %s)" % debut.strftime("%d/%m/%Y")
    if regle.periode == "SEMAINE":
        return "par semaine (semaine du %s)" % debut.strftime("%d/%m/%Y")
    if regle.periode == "MOIS":
        return "par mois (%s %d)" % (MOIS[debut.month - 1], debut.year)
    if regle.periode == "ANNEE":
        return "par année (%d)" % debut.year
    return "entre le %s et le %s" % (debut.strftime("%d/%m/%Y"), fin.strftime("%d/%m/%Y"))


def Get_regles(categories=[]):
    """ Renvoie un dict {idcategorie: [regles]} """
    dict_regles = {}
    for regle in LimitationCategorieEvenement.objects.filter(categorie__in=categories).order_by("pk"):
        dict_regles.setdefault(regle.categorie_id, []).append(regle)
    return dict_regles


def Get_bornes_globales(dict_regles={}, dates=[]):
    """ Renvoie (date_min, date_max) couvrant toutes les périodes des règles concernées par les dates, ou None """
    bornes = [Get_bornes_periode(regle, date) for regles in dict_regles.values() for regle in regles for date in dates]
    bornes = [b for b in bornes if b]
    if not bornes:
        return None
    return min(b[0] for b in bornes), max(b[1] for b in bornes)


def Get_bornes_plage(dict_regles={}, date_min=None, date_max=None):
    """ Renvoie (date_min, date_max) couvrant toutes les périodes des règles qui recoupent la plage affichée, ou None """
    bornes = []
    for regles in dict_regles.values():
        for regle in regles:
            if regle.periode == "PERIODE":
                if regle.date_debut and regle.date_fin and regle.date_debut <= date_max and regle.date_fin >= date_min:
                    bornes.append((regle.date_debut, regle.date_fin))
            else:
                bornes.append((Get_bornes_periode(regle, date_min)[0], Get_bornes_periode(regle, date_max)[1]))
    if not bornes:
        return None
    return min(b[0] for b in bornes), max(b[1] for b in bornes)


def Get_conso_existantes(dict_regles={}, individus=[], bornes=None, exclure_pks=[]):
    """ Renvoie la liste des consommations existantes à compter : [(idconso, idindividu, idcategorie, date)] """
    if not bornes or not individus or not dict_regles:
        return []
    return list(Consommation.objects.filter(individu_id__in=individus, evenement__categorie_id__in=dict_regles.keys(), date__range=bornes)
                .exclude(pk__in=exclure_pks).values_list("pk", "individu_id", "evenement__categorie_id", "date"))


class Controle_limitations():
    """ Contrôle des limitations lors de l'ajout de consommations sur des événements """
    def __init__(self, categories=[], individus=[], dates=[], exclure_pks=[]):
        self.dict_regles = Get_regles(categories)
        self.dict_noms = {categorie.pk: categorie.nom for categorie in categories}
        self.dates_reservees = {}
        for idconso, idindividu, idcategorie, date in Get_conso_existantes(self.dict_regles, individus, Get_bornes_globales(self.dict_regles, dates), exclure_pks):
            self.dates_reservees.setdefault((idindividu, idcategorie), []).append(date)

    def Ajouter(self, idindividu=None, idcategorie=None, date=None):
        """ Mémorise la réservation si elle respecte toutes les règles. Sinon, renvoie le message d'erreur """
        dates = self.dates_reservees.setdefault((idindividu, idcategorie), [])
        for regle in self.dict_regles.get(idcategorie, []):
            bornes = Get_bornes_periode(regle, date)
            if not bornes:
                continue
            nbre = len([d for d in dates if bornes[0] <= d <= bornes[1]])
            if nbre + 1 > regle.nbre_max:
                return "Vous ne pouvez pas réserver plus de %d événement%s de type '%s' %s (déjà réservé%s : %d)." % (
                    regle.nbre_max, "s" if regle.nbre_max > 1 else "", self.dict_noms.get(idcategorie, ""),
                    Get_label_periode(regle, bornes), "s" if nbre > 1 else "", nbre)
        dates.append(date)
        return None


def Get_donnees_grille(categories=[], individus=[], date_min=None, date_max=None):
    """ Données nécessaires au contrôle dans la grille (grille.js) :
    - regles : {idcategorie: [{nbre_max, periode, date_debut, date_fin}]}
    - conso_existantes : consommations de la base sur les périodes concernées [[idconso, idindividu, idcategorie, 'AAAA-MM-JJ']] """
    dict_regles = Get_regles(categories)
    bornes = Get_bornes_plage(dict_regles, date_min, date_max) if date_min and date_max else None
    regles = {idcategorie: [{"nbre_max": r.nbre_max, "periode": r.periode, "date_debut": str(r.date_debut) if r.date_debut else None,
                             "date_fin": str(r.date_fin) if r.date_fin else None} for r in liste] for idcategorie, liste in dict_regles.items()}
    conso_existantes = [[idconso, idindividu, idcategorie, str(date)] for idconso, idindividu, idcategorie, date in Get_conso_existantes(dict_regles, individus, bornes)]
    return {"regles": regles, "conso_existantes": conso_existantes}
