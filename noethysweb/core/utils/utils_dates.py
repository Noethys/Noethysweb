# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, time
import dateutil.parser
from dateutil.relativedelta import relativedelta



LISTE_JOURS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")
LISTE_MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")
LISTE_JOURS_ABREGES = ("Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim.")
LISTE_MOIS_ABREGES = ("janv.", "fév.", "mars", "avril", "mai", "juin", "juil.", "août", "sept.", "oct", "nov.", "déc.")


def EstEnVacances(date=None, liste_vacances=None):
    for vacance in liste_vacances:
        if isinstance(vacance, list):
            if vacance[0] <= str(date) <= vacance[1]:
                return vacance
        else:
            if vacance.date_debut <= date <= vacance.date_fin:
                return vacance
    return None

def EstFerie(date=None, liste_feries=None):
    jour, mois, annee = date.day, date.month, date.year
    for ferie in liste_feries:
        if ferie.type == "fixe":
            if ferie.jour == jour and ferie.mois == mois:
                return ferie
        else:
            if ferie.jour == jour and ferie.mois == mois and ferie.annee == annee:
                return ferie
    return None

def ConvertDatetimeToDate(date=None):
    if date == None:
        return None
    return datetime.date(year=date.year, month=date.month, day=date.day)

def ConvertDateFRtoDate(date=None):
    if not date:
        return None
    try:
        return ConvertDatetimeToDate(dateutil.parser.parse(date, dayfirst=True))
    except:
        return None

def ConvertDateToFR(date=None):
    # Si date vide
    if not date or date == "None":
        return None
    # Si date str anglaise
    if isinstance(date, str) and "-" in date:
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    if isinstance(date, str) and "/" in date:
        return date
    return date.strftime('%d/%m/%Y')

def ConvertDateToDate(date=None):
    if not date: return None
    # Si date str anglaise
    if isinstance(date, str) and "-" in date:
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    if isinstance(date, str) and "/" in date:
        return ConvertDateFRtoDate(date)
    if isinstance(date, datetime.date):
        return date
    return None


def ConvertDateENGtoDate(date=None):
    if date == None:
        return None
    try:
        if isinstance(date, str) and "-" in date:
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        return ConvertDatetimeToDate(date)
    except:
        pass
    try:
        return ConvertDatetimeToDate(dateutil.parser.parse(date, dayfirst=False))
    except:
        pass
    return None

def ConvertDateENGtoFR(date=None):
    date = ConvertDateENGtoDate(date)
    return ConvertDateToFR(date)

def ConvertDureeStrToDuree(duree="j0-m22-a0"):
    if duree == None:
        return None
    j, m, a = duree.split("-")
    jours, mois, annees = int(j[1:]), int(m[1:]), int(a[1:])
    return relativedelta(years=+annees, months=+mois, days=+jours)

def DateComplete(dateDD, abrege=False):
    """ Transforme une date DD en date complète : Ex : lundi 15 janvier 2008 """
    if dateDD == None: return ""
    if abrege == False:
        listeJours, listeMois = LISTE_JOURS, LISTE_MOIS
    else :
        listeJours, listeMois = LISTE_JOURS_ABREGES, LISTE_MOIS_ABREGES
    dateComplete = listeJours[dateDD.weekday()] + " " + str(dateDD.day) + " " + listeMois[dateDD.month-1] + " " + str(dateDD.year)
    return dateComplete

def HeureStrEnTime(heureStr):
    if heureStr == None or heureStr == "": return datetime.time(0, 0)
    try:
        if len(heureStr.split(":")) == 2: heures, minutes = heureStr.split(":")
        if len(heureStr.split(":")) == 3: heures, minutes, secondes = heureStr.split(":")
        return datetime.time(int(heures), int(minutes))
    except:
        return datetime.time(0, 0)

def DeltaEnTime(varTimedelta) :
    """ Transforme une variable TIMEDELTA en heure datetime.time """
    heureStr = time.strftime("%H:%M", time.gmtime(varTimedelta.seconds))
    heure = HeureStrEnTime(heureStr)
    return heure

def DeltaEnStr(heureDelta, separateur="h", si_null=None):
    if not heureDelta:
        return si_null
    if heureDelta < datetime.timedelta(0):
        signe = "-"
        heureDelta = -heureDelta
    else :
        signe = ""

    heures = (heureDelta.days * 24) + (heureDelta.seconds // 3600)
    minutes = heureDelta.seconds % 3600//60
    valeur = "{}{}{}{:0>2}".format(signe, heures, separateur, minutes)
    return valeur

def TimeEnDelta(heureTime):
    if heureTime == None :
        return datetime.timedelta(0)
    hr = heureTime.hour
    mn = heureTime.minute
    return datetime.timedelta(hours=hr, minutes=mn)

def HeureStrEnDelta(heureStr):
    if heureStr == None or heureStr == "": return datetime.timedelta(hours=0, minutes=0)
    if type(heureStr) == datetime.time: return datetime.timedelta(hours=heureStr.hour, minutes=heureStr.minute)
    if "h" in heureStr:
        heureStr = heureStr.replace("h", ":")
    if ":" not in heureStr:
        heureStr += ":"
    if len(heureStr.split(":")) == 2:
        heures, minutes = heureStr.split(":")
    if len(heureStr.split(":")) == 3:
        heures, minutes, secondes = heureStr.split(":")
    if heures == "": heures = 0
    if minutes == "": minutes = 0
    return datetime.timedelta(hours=int(heures), minutes=int(minutes))

def SoustractionHeures(heure_max, heure_min):
    """ Effectue l'opération heure_max - heure_min. Renvoi un timedelta """
    if type(heure_max) != datetime.timedelta : heure_max = datetime.timedelta(hours=heure_max.hour, minutes=heure_max.minute)
    if type(heure_min) != datetime.timedelta : heure_min =  datetime.timedelta(hours=heure_min.hour, minutes=heure_min.minute)
    return heure_max - heure_min

def AdditionHeures(heure1, heure2):
    """ Effectue l'opération heure_max - heure_min. Renvoi un timedelta """
    if type(heure1) != datetime.timedelta : heure1 = datetime.timedelta(hours=heure1.hour, minutes=heure1.minute)
    if type(heure2) != datetime.timedelta : heure2 =  datetime.timedelta(hours=heure2.hour, minutes=heure2.minute)
    return heure1 + heure2

def Additionne_intervalles_temps(intervals=[]):
    def tparse(timestring):
        if type(timestring) == datetime.time: return datetime.datetime(year=1900, month=1, day=1, hour=timestring.hour, minute=timestring.minute)
        if len(timestring.split(":")) == 2: return datetime.datetime.strptime(timestring, '%H:%M')
        if len(timestring.split(":")) == 3: return datetime.datetime.strptime(timestring, '%H:%M:%S')
    START, END = range(2)
    times = []
    for interval in intervals:
        times.append((tparse(interval[START]), START))
        times.append((tparse(interval[END]), END))
    times.sort()
    started = 0
    result = datetime.timedelta()
    for t, categorie in times:
        if categorie == START:
            if not started:
                start_time = t
            started += 1
        elif categorie == END:
            started -= 1
            if not started:
                result += (t - start_time)
    return result



def ArrondirTime(heure=datetime.time(hour=10, minute=25), delta_minutes=15, sens="inf"):
    """ sens = 'sup' ou 'inf' """
    dt = datetime.datetime(year=2015, month=1, day=1, hour=heure.hour, minute=heure.minute)
    if dt.minute % delta_minutes :
        if sens == "sup": resultat = dt + datetime.timedelta(minutes=delta_minutes - dt.minute % delta_minutes)
        if sens == "inf": resultat = dt - datetime.timedelta(minutes=dt.minute % delta_minutes)
    else:
        resultat = dt
    return datetime.time(hour=resultat.hour, minute=resultat.minute)

def ArrondirDelta(duree=datetime.timedelta(hours=1, minutes=25), delta_minutes=15, sens="sup"):
    duree_minutes = duree.seconds // 60
    if duree_minutes % delta_minutes:
        if sens == "sup": resultat = duree + datetime.timedelta(minutes=delta_minutes - duree_minutes % delta_minutes)
        if sens == "inf": resultat = duree - datetime.timedelta(minutes=duree_minutes % delta_minutes)
    else :
        resultat = duree
    return resultat


def CalculerArrondi(arrondi_type="duree", arrondi_delta=15, heure_debut=None, heure_fin=None):
    """
    :param arrondi_type: None ou duree ou tranche_horaire
    :param arrondi_delta: minutes
    :param heure_debut: heure_debut en time
    :param heure_fin: heure_fin en time
    :return: datetime.time
    """
    duree_reelle = SoustractionHeures(heure_fin, heure_debut)

    if arrondi_type == None :
        duree_arrondie = duree_reelle

    if arrondi_type == "tranche_horaire" :
        heure_debut_temp = ArrondirTime(heure=heure_debut, delta_minutes=arrondi_delta, sens="inf")
        heure_fin_temp = ArrondirTime(heure=heure_fin, delta_minutes=arrondi_delta, sens="sup")
        duree_arrondie = SoustractionHeures(heure_fin_temp, heure_debut_temp)

    if arrondi_type == "duree" :
        duree_arrondie = ArrondirDelta(duree=duree_reelle, delta_minutes=arrondi_delta, sens="sup")

    return duree_arrondie


def FormateMois(donnee):
    if donnee in ("", None):
        return ""
    else:
        annee, mois = donnee
        return u"%s %d" % (LISTE_MOIS[mois-1].capitalize(), annee)

def ConvertDateRangePicker(periode=""):
    date_debut = ConvertDateENGtoDate(periode.split(";")[0])
    date_fin = ConvertDateENGtoDate(periode.split(";")[1])
    return (date_debut, date_fin)

def ConvertPeriodeFrToDate(periode=""):
    try:
        date_debut, date_fin = periode.split("-")
        date_debut = ConvertDatetimeToDate(dateutil.parser.parse(date_debut.strip(), dayfirst=True))
        date_fin = ConvertDatetimeToDate(dateutil.parser.parse(date_fin.strip(), dayfirst=True))
        return (date_debut, date_fin)
    except:
        return None
