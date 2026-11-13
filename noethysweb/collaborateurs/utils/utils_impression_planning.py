# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, calendar
logger = logging.getLogger(__name__)
from reportlab.platypus import Spacer, Table, TableStyle, PageBreak, Paragraph, KeepTogether, CondPageBreak
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from django.utils.html import escape
from core.utils import utils_impression, utils_polices, utils_dates
from core.models import Collaborateur, TypeEvenementCollaborateur, ContratCollaborateur, Ferie, NotePlanningCollaborateur
from collaborateurs.utils import utils_planning
from collaborateurs.utils.utils_affectations import Arbre

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_COURTS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

# Types de documents : (libellé, orientation paysage, un document par collaborateur)
TYPES_DOCUMENTS = {
    "individuel": ("Planning individuel", False, True),
    "equipe": ("Planning d'équipe hebdomadaire", True, False),
    "frise": ("Frise de la journée", True, False),
    "affectation": ("Planning par affectation", False, False),
    "emargement": ("Feuille d'émargement", False, False),
    "recapitulatif": ("Récapitulatif mensuel des heures", True, False),
    "calendrier": ("Calendrier mensuel individuel", True, True),
}

GRIS_LIGNE = colors.HexColor("#b8c0cc")
GRIS_FOND = colors.HexColor("#eef1f5")
GRIS_CLAIR = colors.HexColor("#f6f8fb")
ROUGE_FERIE = colors.HexColor("#e0485a")
JAUNE_VACANCES = colors.HexColor("#fff3cd")


def Couleur(valeur, defaut="#94a3b8"):
    try:
        return colors.HexColor(valeur or defaut)
    except Exception:
        return colors.HexColor(defaut)


def Format_heures(minutes=0, decimal=False):
    if decimal:
        return ("%.1f" % (minutes / 60)).replace(".", ",").replace(",0", "") if minutes else ""
    return utils_planning.Format_minutes(minutes)


class Frise(Flowable):
    """ Frise horaire dessinée : une ligne par libellé, des barres colorées """
    def __init__(self, largeur=700, lignes=[], plage=(420, 1140), hauteur_ligne=22, largeur_libelle=150):
        Flowable.__init__(self)
        self.largeur, self.lignes, self.plage = largeur, lignes, plage
        self.hauteur_ligne, self.largeur_libelle = hauteur_ligne, largeur_libelle
        self.hauteur = 18 + len(lignes) * hauteur_ligne

    def wrap(self, *args):
        return self.largeur, self.hauteur

    def X(self, minutes):
        debut, fin = self.plage
        piste = self.largeur - self.largeur_libelle - 50
        return self.largeur_libelle + max(0, min(1, (minutes - debut) / (fin - debut))) * piste

    def draw(self):
        c = self.canv
        debut, fin = self.plage
        haut = self.hauteur
        # Graduations horaires
        c.setFont(utils_polices.FONT_NORMAL, 7)
        for heure in range(debut // 60, fin // 60 + 1):
            x = self.X(heure * 60)
            c.setStrokeColor(colors.HexColor("#e2e6ec"))
            c.setLineWidth(0.4)
            c.line(x, 0, x, haut - 14)
            c.setFillColor(colors.HexColor("#5b6472"))
            c.drawCentredString(x, haut - 10, "%02dh" % heure)
        c.setFillColor(colors.HexColor("#5b6472"))
        c.drawRightString(self.largeur, haut - 10, "Total")
        # Lignes
        for index, ligne in enumerate(self.lignes):
            y = haut - 18 - (index + 1) * self.hauteur_ligne
            if ligne.get("titre"):
                c.setFillColor(GRIS_FOND)
                c.rect(0, y + 1, self.largeur, self.hauteur_ligne - 2, stroke=0, fill=1)
                c.setFillColor(colors.HexColor("#1f2937"))
                c.setFont(utils_polices.FONT_BOLD, 8.5)
                c.drawString(4 + ligne.get("niveau", 0) * 10, y + self.hauteur_ligne / 2 - 3, ligne["titre"][:90])
                continue
            c.setStrokeColor(colors.HexColor("#eef0f3"))
            c.line(0, y, self.largeur, y)
            c.setFillColor(colors.HexColor("#1f2937"))
            c.setFont(utils_polices.FONT_NORMAL, 8)
            c.drawString(4 + ligne.get("niveau", 0) * 10, y + self.hauteur_ligne / 2 - 3, ligne["libelle"][:32])
            for barre in ligne["barres"]:
                x1, x2 = self.X(barre["debut"]), self.X(barre["fin"])
                if x2 - x1 < 1:
                    continue
                c.setFillColor(Couleur(barre["couleur"]))
                c.roundRect(x1, y + 3, x2 - x1, self.hauteur_ligne - 6, 2.5, stroke=0, fill=1)
                texte = barre["texte"]
                c.setFont(utils_polices.FONT_BOLD, 6.5)
                while texte and c.stringWidth(texte, utils_polices.FONT_BOLD, 6.5) > x2 - x1 - 4:
                    texte = texte[:-1]
                if texte:
                    c.setFillColor(colors.white)
                    c.drawString(x1 + 2, y + self.hauteur_ligne / 2 - 2.5, texte)
            c.setFillColor(colors.HexColor("#1f2937"))
            c.setFont(utils_polices.FONT_BOLD, 8)
            c.drawRightString(self.largeur, y + self.hauteur_ligne / 2 - 3, ligne.get("total", ""))


class Impression(utils_impression.Impression):
    """ Documents imprimables du planning des collaborateurs """
    def __init__(self, *args, **kwds):
        donnees = kwds.get("dict_donnees", {})
        type_document = donnees.get("type", "individuel")
        if TYPES_DOCUMENTS.get(type_document, TYPES_DOCUMENTS["individuel"])[1]:
            kwds["taille_page"] = landscape(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    # ---------------------------------------------------------------- Préparation des données
    def Charger(self):
        d = self.dict_donnees
        self.dates = d["dates"]
        self.dates_set = set(self.dates)
        self.type = d.get("type", "individuel")
        self.afficher_realise = d.get("afficher_realise", False)
        self.afficher_affectations = d.get("afficher_affectations", True)
        self.afficher_notes = d.get("afficher_notes", True)
        self.collaborateurs = list(Collaborateur.objects.filter(pk__in=d["collaborateurs"]).order_by("nom", "prenom"))
        self.categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
        self.arbre = Arbre()
        self.liste_feries = list(Ferie.objects.all())
        self.contrats = {}
        for contrat in ContratCollaborateur.objects.filter(collaborateur__in=self.collaborateurs):
            self.contrats.setdefault(contrat.collaborateur_id, []).append(contrat)
        # Evènements rangés par (collaborateur, date de début)
        self.evenements = {}
        date_min, date_max = self.dates[0], self.dates[-1]
        if self.type == "calendrier":
            # Le calendrier affiche les mois complets
            date_min = date_min.replace(day=1)
            date_max = date_max.replace(day=calendar.monthrange(date_max.year, date_max.month)[1])
            self.dates_set = {date_min + datetime.timedelta(days=i) for i in range((date_max - date_min).days + 1)}
            self.dates = sorted(self.dates_set)
        for evenement in utils_planning.Get_evenements(date_min, date_max, [collaborateur.pk for collaborateur in self.collaborateurs]):
            self.evenements.setdefault((evenement.collaborateur_id, evenement.date_debut.date()), []).append(evenement)
        for liste in self.evenements.values():
            liste.sort(key=lambda evenement: evenement.date_debut)
        self.notes = {(note.date, note.affectation_id): note.texte for note in NotePlanningCollaborateur.objects.filter(date__gte=self.dates[0], date__lte=self.dates[-1])}
        self.largeur = self.taille_page[0] - 56
        # Styles
        self.s_texte = ParagraphStyle(name="texte", fontName=utils_polices.FONT_NORMAL, fontSize=7.5, leading=9)
        self.s_petit = ParagraphStyle(name="petit", fontName=utils_polices.FONT_NORMAL, fontSize=6.5, leading=8)
        self.s_gras = ParagraphStyle(name="gras", fontName=utils_polices.FONT_BOLD, fontSize=7.5, leading=9)
        self.s_total = ParagraphStyle(name="total", fontName=utils_polices.FONT_BOLD, fontSize=9, leading=11)
        self.s_note = ParagraphStyle(name="note", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10, backColor=colors.HexColor("#e0f2fe"),
                                     borderPadding=(4, 6, 4, 6), textColor=colors.HexColor("#075985"))

    def Periode(self, dates=None):
        dates = dates or self.dates
        if len(dates) == 1:
            return "%s %s" % (JOURS[dates[0].weekday()], utils_dates.ConvertDateToFR(dates[0]))
        return "du %s au %s" % (utils_dates.ConvertDateToFR(dates[0]), utils_dates.ConvertDateToFR(dates[-1]))

    def Ferie(self, date):
        return utils_dates.EstFerie(date, self.liste_feries)

    def Evts(self, idcollaborateur, date):
        return self.evenements.get((idcollaborateur, date), [])

    def Duree(self, evenement, realise=False):
        return utils_planning.Duree_comptabilisee(evenement, self.categories.get(evenement.type_evenement_id), realise=realise)

    def Total(self, idcollaborateur, dates):
        return sum(self.Duree(evenement) for date in dates for evenement in self.Evts(idcollaborateur, date))

    def Attendu(self, idcollaborateur, dates):
        return utils_planning.Heures_attendues(self.contrats.get(idcollaborateur, []), dates, self.liste_feries)

    def Hors_contrat(self, idcollaborateur, date):
        contrats = self.contrats.get(idcollaborateur, [])
        return bool(contrats) and not any(contrat.date_debut <= date and (not contrat.date_fin or date <= contrat.date_fin) for contrat in contrats)

    def Texte_evt(self, evenement, abrege=True, affectation=None):
        categorie = self.categories.get(evenement.type_evenement_id)
        texte = "%s-%s" % (evenement.date_debut.strftime("%H:%M"), evenement.date_fin.strftime("%H:%M"))
        detail = evenement.titre or (categorie.nom if categorie else "")
        if abrege and len(detail) > 18:
            detail = detail[:17] + "."
        texte = "<font color='%s'>&#9632;</font> <b>%s</b> %s" % (escape(categorie.couleur if categorie else "#999"), texte, escape(detail))
        if (self.afficher_affectations if affectation is None else affectation) and evenement.affectation_id:
            texte += "<br/><font color='#5b6472'>%s</font>" % escape(self.arbre.Get_chemin(evenement.affectation_id, abrege=True))
        return texte

    def Notes_du_jour(self, date):
        resultats = []
        if (date, None) in self.notes:
            resultats.append(("", self.notes[(date, None)]))
        for (date_note, idaffectation), texte in sorted(self.notes.items(), key=lambda x: str(x[0])):
            if date_note == date and idaffectation:
                resultats.append((self.arbre.Get_chemin(idaffectation, abrege=True), texte))
        return resultats

    def Insert_notes(self, date):
        if not self.afficher_notes:
            return
        for affectation, texte in self.Notes_du_jour(date):
            self.story.append(Paragraph("<b>Note%s :</b> %s" % (" " + escape(affectation) if affectation else "", escape(texte).replace("\n", "<br/>")), self.s_note))
            self.story.append(Spacer(0, 6))

    def Insert_titre(self, titre, detail=""):
        self.Insert_header(titre=titre, detail=detail, espace_apres=10)

    def Semaines(self, dates):
        semaines = []
        for date in dates:
            if not semaines or date.isocalendar()[:2] != semaines[-1][0].isocalendar()[:2]:
                semaines.append([])
            semaines[-1].append(date)
        return semaines

    def Mois(self, dates):
        mois = []
        for date in dates:
            if not mois or (date.year, date.month) != (mois[-1][0].year, mois[-1][0].month):
                mois.append([])
            mois[-1].append(date)
        return mois

    # ---------------------------------------------------------------- Dessin
    def Draw(self):
        self.Charger()
        if not self.collaborateurs:
            self.erreurs.append("Aucun collaborateur à imprimer")
            return
        for nom in ("leftMargin", "rightMargin", "topMargin", "bottomMargin"):
            setattr(self.doc, nom, 28)
        fonction = getattr(self, "Draw_%s" % self.type, None) or self.Draw_individuel
        fonction()
        if not self.story:
            self.story.append(Paragraph("Aucune donnée à imprimer.", self.s_texte))

    # A. Planning individuel (une page par collaborateur)
    def Draw_individuel(self):
        entetes = ["Date", "Horaires", "Durée", "Catégorie"]
        largeurs = [80, 62, 38, 90]
        if self.afficher_affectations:
            entetes.append("Affectation")
            largeurs.append(120)
        entetes.append("Titre")
        if self.afficher_realise:
            entetes.append("Réalisé")
            largeurs.append(62)
        largeurs.insert(entetes.index("Titre"), max(60, self.largeur - sum(largeurs)))

        for index_collaborateur, collaborateur in enumerate(self.collaborateurs):
            if index_collaborateur:
                self.story.append(PageBreak())
            self.Insert_titre("Planning de %s" % collaborateur.Get_nom(), self.Periode())
            lignes = [[Paragraph(entete, self.s_gras) for entete in entetes]]
            styles = [("GRID", (0, 0), (-1, -1), 0.25, GRIS_LIGNE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, 0), GRIS_FOND)]
            total_realise = 0
            for date in self.dates:
                liste = self.Evts(collaborateur.pk, date)
                ferie = self.Ferie(date)
                texte_date = "<b>%s %s</b>%s" % (JOURS[date.weekday()], date.strftime("%d/%m/%Y"), "<br/><font color='#e0485a'>%s</font>" % escape(ferie.nom) if ferie else "")
                if not liste:
                    if date.weekday() >= 5 and not ferie:
                        continue
                    lignes.append([Paragraph(texte_date, self.s_texte), Paragraph("<font color='#6b7280'>Aucun évènement</font>", self.s_texte)] + [""] * (len(entetes) - 2))
                    styles.append(("SPAN", (1, len(lignes) - 1), (-1, len(lignes) - 1)))
                    continue
                premiere = len(lignes)
                for evenement in liste:
                    categorie = self.categories.get(evenement.type_evenement_id)
                    total_realise += self.Duree(evenement, realise=True)
                    duree_brute = (evenement.date_fin - evenement.date_debut).total_seconds() / 60
                    ligne = [Paragraph(texte_date, self.s_texte),
                             Paragraph("%s - %s" % (evenement.date_debut.strftime("%H:%M"), evenement.date_fin.strftime("%H:%M")), self.s_texte),
                             Paragraph(utils_planning.Format_minutes(duree_brute) if categorie and categorie.type != "NEUTRE" else "<font color='#6b7280'>%s</font>" % utils_planning.Format_minutes(duree_brute), self.s_texte),
                             Paragraph("<font color='%s'>&#9632;</font> %s" % (escape(categorie.couleur) if categorie else "#999999", escape(categorie.nom) if categorie else ""), self.s_texte)]
                    if self.afficher_affectations:
                        ligne.append(Paragraph(escape(self.arbre.Get_chemin(evenement.affectation_id)) if evenement.affectation_id else "", self.s_texte))
                    ligne.append(Paragraph(escape(evenement.titre or ""), self.s_texte))
                    if self.afficher_realise:
                        ligne.append(Paragraph("%s - %s" % (evenement.realise_debut.strftime("%H:%M"), evenement.realise_fin.strftime("%H:%M")) if evenement.realise_debut else "", self.s_texte))
                    lignes.append(ligne)
                if len(liste) > 1:
                    styles += [("SPAN", (0, premiere), (0, len(lignes) - 1)), ("VALIGN", (0, premiere), (0, len(lignes) - 1), "TOP")]
            tableau = Table(lignes, largeurs, repeatRows=1)
            tableau.setStyle(TableStyle(styles))
            self.story += [tableau, Spacer(0, 12)]
            total = self.Total(collaborateur.pk, self.dates)
            texte = "Temps de travail planifié : %s" % utils_planning.Format_minutes(total)
            attendu = self.Attendu(collaborateur.pk, self.dates)
            if attendu:
                texte += " · Prévu au contrat : %s · Écart : %s" % (utils_planning.Format_minutes(attendu), utils_planning.Format_minutes(total - attendu))
            if self.afficher_realise:
                texte += " · Réalisé saisi : %s" % utils_planning.Format_minutes(total_realise)
            self.story.append(Paragraph(texte, self.s_total))

    # B. Planning d'équipe hebdomadaire (collaborateurs x jours)
    def Draw_equipe(self):
        for index_semaine, dates in enumerate(self.Semaines(self.dates)):
            if index_semaine:
                self.story.append(PageBreak())
            self.Insert_titre("Planning d'équipe", "Semaine %s" % self.Periode(dates))
            largeur_nom, largeur_total = 105, 62
            largeur_jour = (self.largeur - largeur_nom - largeur_total) / len(dates)
            entete = [Paragraph("Collaborateur", self.s_gras)]
            styles = [("GRID", (0, 0), (-1, -1), 0.25, GRIS_LIGNE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, 0), GRIS_FOND)]
            for colonne, date in enumerate(dates, 1):
                ferie = self.Ferie(date)
                entete.append(Paragraph("<b>%s %s</b>%s" % (JOURS_COURTS[date.weekday()], date.strftime("%d/%m"), "<br/><font color='#e0485a'>%s</font>" % escape(ferie.nom) if ferie else ""), self.s_texte))
                if ferie:
                    styles.append(("BACKGROUND", (colonne, 1), (colonne, -1), colors.HexColor("#fde7ea")))
            entete.append(Paragraph("Total", self.s_gras))
            lignes = [entete]
            for collaborateur in self.collaborateurs:
                ligne = [Paragraph("<b>%s</b>" % escape(collaborateur.Get_nom()), self.s_texte)]
                for colonne, date in enumerate(dates, 1):
                    textes = [self.Texte_evt(evenement) for evenement in self.Evts(collaborateur.pk, date)]
                    ligne.append(Paragraph("<br/>".join(textes), self.s_petit))
                    if self.Hors_contrat(collaborateur.pk, date):
                        styles.append(("BACKGROUND", (colonne, len(lignes)), (colonne, len(lignes)), GRIS_CLAIR))
                total, attendu = self.Total(collaborateur.pk, dates), self.Attendu(collaborateur.pk, dates)
                texte_total = "<b>%s</b>" % utils_planning.Format_minutes(total)
                if attendu:
                    texte_total += "<br/><font color='#5b6472'>contrat %s<br/>écart %s</font>" % (utils_planning.Format_minutes(attendu), utils_planning.Format_minutes(total - attendu))
                ligne.append(Paragraph(texte_total, self.s_petit))
                lignes.append(ligne)
            tableau = Table(lignes, [largeur_nom] + [largeur_jour] * len(dates) + [largeur_total], repeatRows=1)
            tableau.setStyle(TableStyle(styles))
            self.story.append(tableau)
            if self.afficher_notes:
                notes = [(date, affectation, texte) for date in dates for affectation, texte in self.Notes_du_jour(date)]
                if notes:
                    self.story.append(Spacer(0, 8))
                    for date, affectation, texte in notes:
                        self.story.append(Paragraph("<b>%s %s%s :</b> %s" % (JOURS_COURTS[date.weekday()], date.strftime("%d/%m"), " · " + escape(affectation) if affectation else "", escape(texte)), self.s_texte))

    # C. Frise de la journée (une page par date)
    def Draw_frise(self):
        grouper = self.dict_donnees.get("grouper_affectations", False)
        for index_date, date in enumerate(self.dates):
            if index_date:
                self.story.append(PageBreak())
            ferie = self.Ferie(date)
            self.Insert_titre("Planning du %s %d %s %d" % (JOURS[date.weekday()].lower(), date.day, MOIS[date.month - 1], date.year), ferie.nom if ferie else "")
            self.Insert_notes(date)
            # Plage horaire : selon les évènements comptabilisés de la journée
            mini, maxi = None, None
            for collaborateur in self.collaborateurs:
                for evenement in self.Evts(collaborateur.pk, date):
                    categorie = self.categories.get(evenement.type_evenement_id)
                    if categorie and categorie.type == "ADDITION":
                        debut = evenement.date_debut.hour * 60 + evenement.date_debut.minute
                        fin = debut + (evenement.date_fin - evenement.date_debut).total_seconds() / 60
                        mini = debut if mini is None else min(mini, debut)
                        maxi = fin if maxi is None else max(maxi, fin)
            plage = (max(0, int((mini - 30) // 60 * 60)), min(1440, int(-(-(maxi + 30) // 60) * 60))) if mini is not None else (420, 1140)
            if plage[1] - plage[0] < 480:
                plage = (max(0, plage[0] - 60), min(1440, plage[0] + 480))

            def Barres(evenements):
                barres = []
                for evenement in evenements:
                    categorie = self.categories.get(evenement.type_evenement_id)
                    debut = evenement.date_debut.hour * 60 + evenement.date_debut.minute
                    fin = min(1440, debut + (evenement.date_fin - evenement.date_debut).total_seconds() / 60)
                    barres.append({"debut": debut, "fin": fin, "couleur": categorie.couleur if categorie else None,
                                   "texte": "%s-%s %s" % (evenement.date_debut.strftime("%H:%M"), evenement.date_fin.strftime("%H:%M"), evenement.titre or (categorie.nom if categorie else ""))})
                return barres

            lignes = []
            if grouper:
                par_affectation = {}
                for collaborateur in self.collaborateurs:
                    for evenement in self.Evts(collaborateur.pk, date):
                        par_affectation.setdefault(evenement.affectation_id, {}).setdefault(collaborateur, []).append(evenement)
                ordre = [affectation.pk for affectation, niveau in self.arbre.Parcourir()] + [None]
                for idaffectation in ordre:
                    if idaffectation not in par_affectation:
                        continue
                    lignes.append({"titre": self.arbre.Get_chemin(idaffectation) if idaffectation else "Sans affectation"})
                    for collaborateur, evenements in sorted(par_affectation[idaffectation].items(), key=lambda x: x[0].Get_nom()):
                        lignes.append({"libelle": collaborateur.Get_nom(), "barres": Barres(evenements), "niveau": 1,
                                       "total": utils_planning.Format_minutes(sum(self.Duree(evenement) for evenement in evenements))})
            else:
                for collaborateur in self.collaborateurs:
                    evenements = self.Evts(collaborateur.pk, date)
                    lignes.append({"libelle": collaborateur.Get_nom(), "barres": Barres(evenements), "total": utils_planning.Format_minutes(self.Total(collaborateur.pk, [date]))})
            # Découpage en blocs pour la pagination
            hauteur_ligne = 22 if len(lignes) <= 22 else 17
            for debut_bloc in range(0, len(lignes), 24):
                self.story.append(Frise(largeur=self.largeur, lignes=lignes[debut_bloc:debut_bloc + 24], plage=plage, hauteur_ligne=hauteur_ligne))
                self.story.append(Spacer(0, 8))
            # Légende
            categories = {evenement.type_evenement_id for collaborateur in self.collaborateurs for evenement in self.Evts(collaborateur.pk, date)}
            legende = "   ".join("<font color='%s'>&#9632;</font> %s" % (escape(self.categories[idcategorie].couleur), escape(self.categories[idcategorie].nom)) for idcategorie in categories if idcategorie in self.categories)
            self.story.append(Paragraph(legende, self.s_texte))

    # D. Planning par affectation
    def Draw_affectation(self):
        self.Insert_titre("Planning par affectation", self.Periode())
        par_affectation = {}
        for collaborateur in self.collaborateurs:
            for date in self.dates:
                for evenement in self.Evts(collaborateur.pk, date):
                    categorie = self.categories.get(evenement.type_evenement_id)
                    if categorie and categorie.type != "ADDITION" and not evenement.affectation_id:
                        continue
                    par_affectation.setdefault(evenement.affectation_id, []).append((date, collaborateur, evenement))
        ordre = [(affectation.pk, niveau) for affectation, niveau in self.arbre.Parcourir()] + [(None, 0)]
        largeurs = [80, 140, 62, 100, self.largeur - 382] if not self.afficher_realise else [80, 130, 62, 95, self.largeur - 429, 62]
        premier = True
        for idaffectation, niveau in ordre:
            if idaffectation not in par_affectation:
                continue
            elements = []
            titre = self.arbre.Get_chemin(idaffectation) if idaffectation else "Sans affectation"
            total = sum(self.Duree(evenement) for date, collaborateur, evenement in par_affectation[idaffectation])
            elements.append(Paragraph("<b>%s</b> <font color='#5b6472'>· %s</font>" % (escape(titre), utils_planning.Format_minutes(total)),
                                      ParagraphStyle(name="aff", fontName=utils_polices.FONT_BOLD, fontSize=11, leading=14, spaceBefore=0 if premier else 10, spaceAfter=4)))
            premier = False
            entetes = ["Date", "Collaborateur", "Horaires", "Catégorie", "Titre"] + (["Réalisé"] if self.afficher_realise else [])
            lignes = [[Paragraph(entete, self.s_gras) for entete in entetes]]
            styles = [("GRID", (0, 0), (-1, -1), 0.25, GRIS_LIGNE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, 0), GRIS_FOND)]
            date_precedente, debut_date = None, 1
            for date, collaborateur, evenement in sorted(par_affectation[idaffectation], key=lambda x: (x[0], x[2].date_debut, x[1].Get_nom())):
                if date != date_precedente:
                    if date_precedente and len(lignes) - debut_date > 1:
                        styles += [("SPAN", (0, debut_date), (0, len(lignes) - 1)), ("VALIGN", (0, debut_date), (0, len(lignes) - 1), "TOP")]
                    debut_date = len(lignes)
                    date_precedente = date
                categorie = self.categories.get(evenement.type_evenement_id)
                note = self.notes.get((date, idaffectation)) if self.afficher_notes and idaffectation else None
                ligne = [Paragraph("<b>%s %s</b>%s" % (JOURS_COURTS[date.weekday()], date.strftime("%d/%m"), "<br/><font color='#075985'>%s</font>" % escape(note) if note and debut_date == len(lignes) else ""), self.s_texte),
                         Paragraph(escape(collaborateur.Get_nom()), self.s_texte),
                         Paragraph("%s - %s" % (evenement.date_debut.strftime("%H:%M"), evenement.date_fin.strftime("%H:%M")), self.s_texte),
                         Paragraph("<font color='%s'>&#9632;</font> %s" % (escape(categorie.couleur) if categorie else "#999", escape(categorie.nom) if categorie else ""), self.s_texte),
                         Paragraph(escape(evenement.titre or ""), self.s_texte)]
                if self.afficher_realise:
                    ligne.append(Paragraph("%s - %s" % (evenement.realise_debut.strftime("%H:%M"), evenement.realise_fin.strftime("%H:%M")) if evenement.realise_debut else "", self.s_texte))
                lignes.append(ligne)
            if len(lignes) - debut_date > 1:
                styles += [("SPAN", (0, debut_date), (0, len(lignes) - 1)), ("VALIGN", (0, debut_date), (0, len(lignes) - 1), "TOP")]
            tableau = Table(lignes, largeurs, repeatRows=1)
            tableau.setStyle(TableStyle(styles))
            elements.append(tableau)
            self.story.append(CondPageBreak(80))
            self.story += elements

    # E. Feuille d'émargement (une page par date)
    def Draw_emargement(self):
        for index_date, date in enumerate(self.dates):
            if index_date:
                self.story.append(PageBreak())
            ferie = self.Ferie(date)
            self.Insert_titre("Feuille d'émargement", "%s %s%s" % (JOURS[date.weekday()], utils_dates.ConvertDateToFR(date), " - " + ferie.nom if ferie else ""))
            self.Insert_notes(date)
            entetes = ["Collaborateur", "Horaires prévus", "Arrivée", "Départ", "Signature"]
            largeurs = [120, 150, 55, 55, self.largeur - 380]
            lignes = [[Paragraph(entete, self.s_gras) for entete in entetes]]
            for collaborateur in self.collaborateurs:
                evenements = [evenement for evenement in self.Evts(collaborateur.pk, date) if self.categories.get(evenement.type_evenement_id) and self.categories[evenement.type_evenement_id].type == "ADDITION"]
                if not evenements:
                    continue
                horaires = "<br/>".join("%s - %s%s" % (evenement.date_debut.strftime("%H:%M"), evenement.date_fin.strftime("%H:%M"),
                                                         " <font color='#5b6472'>%s</font>" % escape(self.arbre.Get_chemin(evenement.affectation_id, abrege=True)) if self.afficher_affectations and evenement.affectation_id else "")
                                        for evenement in evenements)
                lignes.append([Paragraph("<b>%s</b>" % escape(collaborateur.Get_nom()), self.s_texte), Paragraph(horaires, self.s_texte), "", "", ""])
            if len(lignes) == 1:
                self.story.append(Paragraph("Aucun collaborateur n'est planifié ce jour.", self.s_texte))
                continue
            tableau = Table(lignes, largeurs, repeatRows=1, rowHeights=[None] + [max(30, 12 * (str(ligne[1].text).count("<br/>") + 1) + 8) for ligne in lignes[1:]])
            tableau.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRIS_LIGNE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, 0), GRIS_FOND)]))
            self.story.append(tableau)

    # F. Récapitulatif mensuel des heures (collaborateurs x jours)
    def Draw_recapitulatif(self):
        for index_mois, dates in enumerate(self.Mois(self.dates)):
            if index_mois:
                self.story.append(PageBreak())
            self.Insert_titre("Récapitulatif des heures - %s %d" % (MOIS[dates[0].month - 1], dates[0].year), self.Periode(dates))
            largeur_nom, largeur_totaux = 100, 46
            largeur_jour = (self.largeur - largeur_nom - largeur_totaux * 3) / len(dates)
            taille = 6 if largeur_jour < 20 else 7
            s_cellule = ParagraphStyle(name="cellule", fontName=utils_polices.FONT_NORMAL, fontSize=taille, leading=taille + 1.5, alignment=1)
            s_entete = ParagraphStyle(name="entete", fontName=utils_polices.FONT_BOLD, fontSize=taille, leading=taille + 1.5, alignment=1)
            entete = [Paragraph("Collaborateur", self.s_gras)]
            styles = [("GRID", (0, 0), (-1, -1), 0.25, GRIS_LIGNE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, 0), GRIS_FOND)]
            for colonne, date in enumerate(dates, 1):
                entete.append(Paragraph("%s<br/>%d" % (JOURS_COURTS[date.weekday()][0], date.day), s_entete))
                if self.Ferie(date):
                    styles.append(("BACKGROUND", (colonne, 0), (colonne, -1), colors.HexColor("#fde7ea")))
                elif date.weekday() >= 5:
                    styles.append(("BACKGROUND", (colonne, 1), (colonne, -1), GRIS_CLAIR))
            entete += [Paragraph("Total", s_entete), Paragraph("Contrat", s_entete), Paragraph("Écart", s_entete)]
            lignes = [entete]
            totaux_jours = [0] * len(dates)
            for collaborateur in self.collaborateurs:
                ligne = [Paragraph(escape(collaborateur.Get_nom()), self.s_texte)]
                for colonne, date in enumerate(dates):
                    evenements = self.Evts(collaborateur.pk, date)
                    minutes = sum(self.Duree(evenement) for evenement in evenements)
                    totaux_jours[colonne] += minutes
                    if minutes:
                        texte = Format_heures(minutes, decimal=True)
                    elif evenements:
                        categorie = self.categories.get(evenements[0].type_evenement_id)
                        texte = "<font color='%s'>%s</font>" % (escape(categorie.couleur), escape(categorie.nom[:2].upper())) if categorie else ""
                    else:
                        texte = ""
                    ligne.append(Paragraph(texte, s_cellule))
                total, attendu = self.Total(collaborateur.pk, dates), self.Attendu(collaborateur.pk, dates)
                ligne += [Paragraph("<b>%s</b>" % utils_planning.Format_minutes(total), s_cellule),
                          Paragraph(utils_planning.Format_minutes(attendu) if attendu else "", s_cellule),
                          Paragraph(utils_planning.Format_minutes(total - attendu) if attendu else "", s_cellule)]
                lignes.append(ligne)
            lignes.append([Paragraph("<b>Total</b>", self.s_texte)] + [Paragraph("<b>%s</b>" % Format_heures(minutes, decimal=True), s_cellule) for minutes in totaux_jours] +
                          [Paragraph("<b>%s</b>" % utils_planning.Format_minutes(sum(totaux_jours)), s_cellule), "", ""])
            styles.append(("BACKGROUND", (0, -1), (-1, -1), GRIS_FOND))
            tableau = Table(lignes, [largeur_nom] + [largeur_jour] * len(dates) + [largeur_totaux] * 3, repeatRows=1)
            tableau.setStyle(TableStyle(styles))
            self.story.append(tableau)
            self.story.append(Spacer(0, 6))
            self.story.append(Paragraph("Heures comptabilisées en décimal (7,5 = 7 h 30). Les journées sans temps comptabilisé affichent les initiales de la catégorie (congés...).", self.s_petit))
            visa = Table([["Visa du responsable :", "Date :", "Signature :"]], [self.largeur / 3] * 3, rowHeights=[46])
            visa.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, GRIS_LIGNE), ("INNERGRID", (0, 0), (-1, -1), 0.4, GRIS_LIGNE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("FONT", (0, 0), (-1, -1), utils_polices.FONT_BOLD, 8)]))
            self.story += [Spacer(0, 10), KeepTogether(visa)]

    # G. Calendrier mensuel individuel
    def Draw_calendrier(self):
        mois_liste = []
        for date in self.dates:
            if (date.year, date.month) not in mois_liste:
                mois_liste.append((date.year, date.month))
        premier = True
        for collaborateur in self.collaborateurs:
            for annee, mois in mois_liste:
                if not premier:
                    self.story.append(PageBreak())
                premier = False
                dates_mois = [datetime.date(annee, mois, jour) for jour in range(1, calendar.monthrange(annee, mois)[1] + 1)]
                total = self.Total(collaborateur.pk, [date for date in dates_mois if date in self.dates_set])
                self.Insert_titre("%s - %s %d" % (collaborateur.Get_nom(), MOIS[mois - 1].capitalize(), annee), "Temps planifié : %s" % utils_planning.Format_minutes(total))
                semaines = calendar.Calendar(firstweekday=0).monthdatescalendar(annee, mois)
                largeur_jour = self.largeur / 7
                hauteur_disponible = self.taille_page[1] - 56 - 70
                hauteur_semaine = (hauteur_disponible - 16) / len(semaines)
                lignes = [[Paragraph("<b>%s</b>" % jour, ParagraphStyle(name="j", fontName=utils_polices.FONT_BOLD, fontSize=8, alignment=1)) for jour in JOURS]]
                styles = [("GRID", (0, 0), (-1, -1), 0.4, GRIS_LIGNE), ("VALIGN", (0, 1), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, 0), GRIS_FOND)]
                for index_semaine, semaine in enumerate(semaines, 1):
                    ligne = []
                    for index_jour, date in enumerate(semaine):
                        if date.month != mois:
                            ligne.append("")
                            styles.append(("BACKGROUND", (index_jour, index_semaine), (index_jour, index_semaine), GRIS_CLAIR))
                            continue
                        ferie = self.Ferie(date)
                        evenements = self.Evts(collaborateur.pk, date) if date in self.dates_set else []
                        minutes = sum(self.Duree(evenement) for evenement in evenements)
                        texte = "<b>%d</b>%s%s" % (date.day, " <font color='#e0485a'>%s</font>" % escape(ferie.nom) if ferie else "",
                                                   " <font color='#5b6472'>(%s)</font>" % utils_planning.Format_minutes(minutes) if minutes else "")
                        for evenement in evenements[:5]:
                            texte += "<br/>" + self.Texte_evt(evenement, affectation=False)
                        if len(evenements) > 5:
                            texte += "<br/>+ %d autre(s)" % (len(evenements) - 5)
                        ligne.append(Paragraph(texte, self.s_petit))
                        if date not in self.dates_set:
                            styles.append(("BACKGROUND", (index_jour, index_semaine), (index_jour, index_semaine), GRIS_CLAIR))
                        elif ferie:
                            styles.append(("BACKGROUND", (index_jour, index_semaine), (index_jour, index_semaine), colors.HexColor("#fde7ea")))
                    lignes.append(ligne)
                tableau = Table(lignes, [largeur_jour] * 7, rowHeights=[16] + [hauteur_semaine] * len(semaines))
                tableau.setStyle(TableStyle(styles))
                self.story.append(tableau)
