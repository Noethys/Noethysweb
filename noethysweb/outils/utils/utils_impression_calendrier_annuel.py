# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Impression PDF (A4 paysage) d'un calendrier annuel : un mois par colonne, avec les vacances scolaires,
les jours fériés et les week-ends. Priorité d'affichage : jour férié > week-end > vacances.
"""

import logging, datetime, uuid, os
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Q
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas
from core.models import Vacance, Ferie
from core.utils import utils_fichiers

MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
JOURS = "LMMJVSD"
C_WE = colors.HexColor("#DADDE2")
C_VAC = colors.HexColor("#FFE9A8")
C_FER = colors.HexColor("#F4B8B8")
C_BLEU = colors.HexColor("#1F3A5F")
C_TRAIT = colors.HexColor("#C8C8C8")
C_TEXTE = colors.HexColor("#333333")
C_INVALIDE = colors.HexColor("#F5F5F5")
MARGE = 28


def Get_mois(annee, type_annee="scolaire"):
    """ Renvoie la liste des 12 (année, mois) affichés """
    mois_debut = 9 if type_annee == "scolaire" else 1
    return [(annee + (mois_debut - 1 + i) // 12, (mois_debut - 1 + i) % 12 + 1) for i in range(12)]


def Get_titre(annee, type_annee="scolaire"):
    if type_annee == "scolaire":
        return "Calendrier de l'année scolaire %d-%d" % (annee, annee + 1)
    return "Calendrier %d" % annee


def Get_feries(annees=[]):
    """ Renvoie {date: nom} des jours fériés des années données """
    feries = {}
    for ferie in Ferie.objects.filter(Q(annee=0) | Q(annee__in=annees)):
        for annee in (annees if ferie.annee == 0 else [ferie.annee]):
            try:
                feries[datetime.date(annee, ferie.mois, ferie.jour)] = ferie.nom
            except (ValueError, TypeError):
                pass
    return feries


class Impression():
    def __init__(self, annee=None, type_annee="scolaire"):
        self.annee = int(annee)
        self.type_annee = type_annee
        self.erreurs = []
        self.nom_fichier = None
        self.Generer()

    def Get_nom_fichier(self):
        return self.nom_fichier

    def Generer(self):
        mois_liste = Get_mois(self.annee, self.type_annee)
        self.date_debut = datetime.date(mois_liste[0][0], mois_liste[0][1], 1)
        dernier = mois_liste[-1]
        self.date_fin = datetime.date(dernier[0] + dernier[1] // 12, dernier[1] % 12 + 1, 1) - datetime.timedelta(days=1)

        # Données
        self.vacances = [(vacance.nom, vacance.date_debut, vacance.date_fin) for vacance in Vacance.objects.filter(
            date_fin__gte=self.date_debut, date_debut__lte=self.date_fin).order_by("date_debut")]
        self.feries = Get_feries(sorted({annee for annee, mois in mois_liste}))

        # Fichier
        utils_fichiers.GetTempRep()
        self.nom_fichier = "/temp/%s.pdf" % uuid.uuid4()
        chemin = settings.MEDIA_ROOT + self.nom_fichier
        largeur, hauteur = landscape(A4)
        c = rl_canvas.Canvas(chemin, pagesize=(largeur, hauteur))
        c.setTitle(Get_titre(self.annee, self.type_annee))
        c.setAuthor("Noethysweb")
        self.Dessiner_entete(c, largeur, hauteur)
        self.Dessiner_grille(c, largeur, hauteur, mois_liste)
        self.Dessiner_legende(c, largeur)
        c.showPage()
        c.save()

    def Get_vacance(self, date):
        for nom, debut, fin in self.vacances:
            if debut <= date <= fin:
                return nom
        return None

    def Dessiner_entete(self, c, largeur, hauteur):
        c.setFont("Helvetica-Bold", 17)
        c.setFillColor(C_BLEU)
        c.drawString(MARGE, hauteur - 38, Get_titre(self.annee, self.type_annee))
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(MARGE, hauteur - 50, "Vacances scolaires, jours fériés et week-ends")

    def Dessiner_grille(self, c, largeur, hauteur, mois_liste):
        x0, y0 = MARGE, hauteur - 64
        larg = (largeur - 2 * MARGE) / 12
        haut = (hauteur - 64 - 44) / 32
        c.setLineWidth(0.3)
        for index, (annee, mois) in enumerate(mois_liste):
            x = x0 + index * larg
            # Entête du mois
            c.setFillColor(C_BLEU)
            c.rect(x, y0 - haut, larg, haut, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x + larg / 2, y0 - haut + 3.5, "%s %d" % (MOIS[mois - 1], annee))

            for jour in range(1, 32):
                y = y0 - haut * (jour + 1)
                try:
                    date = datetime.date(annee, mois, jour)
                except ValueError:
                    c.setFillColor(C_INVALIDE)
                    c.rect(x, y, larg, haut, fill=1, stroke=0)
                    continue

                # Priorité : jour férié > week-end > vacances
                if date in self.feries:
                    fond = C_FER
                elif date.weekday() >= 5:
                    fond = C_WE
                elif self.Get_vacance(date):
                    fond = C_VAC
                else:
                    fond = colors.white
                c.setFillColor(fond)
                c.setStrokeColor(C_TRAIT)
                c.rect(x, y, larg, haut, fill=1, stroke=1)

                c.setFillColor(C_TEXTE)
                c.setFont("Helvetica-Bold" if date.weekday() == 0 else "Helvetica", 6.5)
                c.drawString(x + 4, y + 3, "%s %02d" % (JOURS[date.weekday()], jour))
                if date in self.feries:
                    # Nom du férié tronqué à la place disponible
                    nom, place = self.feries[date], larg - 26
                    while nom and stringWidth(nom, "Helvetica-Oblique", 5.2) > place:
                        nom = nom[:-1]
                    c.setFont("Helvetica-Oblique", 5.2)
                    c.drawRightString(x + larg - 2, y + 3.2, nom)
                elif date.weekday() == 0:
                    c.setFont("Helvetica", 5)
                    c.setFillColor(colors.HexColor("#8A8A8A"))
                    c.drawRightString(x + larg - 2, y + 3.2, "S%d" % date.isocalendar()[1])

    def Dessiner_legende(self, c, largeur):
        x, y = MARGE, 24
        c.setFont("Helvetica", 8)
        c.setLineWidth(0.3)
        for couleur, label in ((C_WE, "Week-end"), (C_VAC, "Vacances scolaires"), (C_FER, "Jour férié")):
            c.setFillColor(couleur)
            c.setStrokeColor(colors.HexColor("#999999"))
            c.rect(x, y - 1, 10, 8, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.drawString(x + 14, y, label)
            x += 14 + stringWidth(label, "Helvetica", 8) + 18

        # Périodes de vacances de la période affichée (police réduite si nécessaire)
        texte = "   ".join("%s : %s – %s" % (nom, debut.strftime("%d/%m/%y"), fin.strftime("%d/%m/%y")) for nom, debut, fin in self.vacances)
        if not texte:
            texte = "Aucune période de vacances n'est paramétrée pour cette période (Menu Paramétrage > Vacances)"
        if texte:
            taille, place = 8, largeur - MARGE - x - 6
            while taille > 5 and stringWidth(texte, "Helvetica", taille) > place:
                taille -= 0.25
            c.setFont("Helvetica", taille)
            c.setFillColor(colors.HexColor("#555555"))
            c.drawString(x + 6, y, texte)

        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#999999"))
        c.drawRightString(largeur - MARGE, 10, "Édité le %s avec Noethysweb" % datetime.date.today().strftime("%d/%m/%Y"))
