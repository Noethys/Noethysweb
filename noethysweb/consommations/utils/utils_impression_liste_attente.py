# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from xml.sax.saxutils import escape
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib import colors
from core.utils import utils_dates, utils_impression, utils_polices


class Impression(utils_impression.Impression):
    """ Impression PDF des lignes affichées (après filtrage) dans la liste d'attente ou la liste des refus """
    def __init__(self, *args, **kwds):
        kwds["taille_page"] = landscape(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        lignes = self.dict_donnees.get("lignes", [])
        etat = self.dict_donnees.get("etat", "attente")
        if not lignes:
            self.erreurs.append("Aucune donnée à exporter")
            return

        # Titre du document
        texte_nbre = "%d demande%s" % (len(lignes), "s" if len(lignes) > 1 else "")
        if etat == "attente":
            nbre_dispo = len([1 for ligne in lignes if ligne.get("place_dispo", False)])
            texte_nbre += " dont %d place%s disponible%s" % (nbre_dispo, "s" if nbre_dispo > 1 else "", "s" if nbre_dispo > 1 else "")
        self.Insert_header(detail=texte_nbre)

        # Styles
        style_normal = ParagraphStyle(name="normal", fontName=utils_polices.FONT_NORMAL, fontSize=7, leading=9)
        style_centre = ParagraphStyle(name="centre", parent=style_normal, alignment=1)
        style_entete = ParagraphStyle(name="entete", parent=style_centre, fontName=utils_polices.FONT_BOLD)
        style_date = ParagraphStyle(name="date", parent=style_normal, fontName=utils_polices.FONT_BOLD, fontSize=8, textColor=colors.white)

        # Colonnes
        largeur_contenu = self.taille_page[0] - 75
        colonnes = [("Rang", 30), ("Individu", 130), ("Famille", 140), ("Activité - Groupe", 150), ("Consommations", 120), ("Réservation", 75), ("Ancienneté", 55)]
        if etat == "attente":
            colonnes.append(("Place dispo.", 60))
        # La colonne Consommations absorbe l'espace restant
        largeurs_colonnes = [largeur for label, largeur in colonnes]
        largeurs_colonnes[4] += largeur_contenu - sum(largeurs_colonnes)

        # Regroupement des lignes par date (dans l'ordre d'affichage)
        groupes = []
        for ligne in lignes:
            if not groupes or groupes[-1][0] != ligne.get("date"):
                groupes.append((ligne.get("date"), []))
            groupes[-1][1].append(ligne)

        maintenant = datetime.datetime.now()
        for date, lignes_date in groupes:
            # Barre de titre de la date + entêtes (répétées en haut de chaque page)
            label_date = utils_dates.DateComplete(utils_dates.ConvertDateENGtoDate(date)) or date or ""
            data_tableau = [
                [Paragraph(escape(label_date.capitalize()), style_date)] + [""] * (len(colonnes) - 1),
                [Paragraph(label, style_entete) for label, largeur in colonnes],
            ]
            styles = [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), (0.5, 0.5, 0.5)),
                ('BACKGROUND', (0, 1), (-1, 1), (0.9, 0.9, 0.9)),
            ]
            for num_ligne, ligne in enumerate(lignes_date, start=2):
                activite_groupe = escape(ligne.get("label_groupe") or "")
                if ligne.get("nom_evenement"):
                    activite_groupe += "<br/><i>%s</i>" % escape(ligne["nom_evenement"])

                date_reservation, anciennete = "", ""
                try:
                    date_saisie = datetime.datetime.strptime(ligne.get("date_saisie") or "", "%d/%m/%Y %H:%M:%S")
                    date_reservation = date_saisie.strftime("%d/%m/%Y %H:%M")
                    jours = max((maintenant - date_saisie).days, 0)
                    anciennete = "%d jour%s" % (jours, "s" if jours > 1 else "")
                except ValueError:
                    pass

                data_ligne = [
                    Paragraph(escape(str(ligne.get("rang") or "")), style_centre),
                    Paragraph(escape(ligne.get("nom_individu") or ""), style_normal),
                    Paragraph(escape(ligne.get("nom_famille") or ""), style_normal),
                    Paragraph(activite_groupe, style_normal),
                    Paragraph(escape(ligne.get("unites") or ""), style_normal),
                    Paragraph(date_reservation, style_centre),
                    Paragraph(anciennete, style_centre),
                ]
                if etat == "attente":
                    dispo = bool(ligne.get("place_dispo", False))
                    data_ligne.append(Paragraph("Oui" if dispo else "Non", style_centre))
                    if dispo:
                        styles.append(('BACKGROUND', (-1, num_ligne), (-1, num_ligne), colors.HexColor("#d4edda")))
                data_tableau.append(data_ligne)

            tableau = Table(data_tableau, largeurs_colonnes, repeatRows=2)
            tableau.setStyle(TableStyle(styles))
            self.story.append(tableau)
            self.story.append(Spacer(0, 15))


class Impression_individu(utils_impression.Impression):
    """ Impression PDF des places en attente d'un individu (document destiné à la famille) """
    def __init__(self, *args, **kwds):
        kwds["taille_page"] = portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        individu = self.dict_donnees["individu"]
        famille = self.dict_donnees["famille"]
        lignes = self.dict_donnees.get("lignes", [])
        if not lignes:
            self.erreurs.append("Aucune place en attente à imprimer pour cet individu")
            return

        # Entête
        self.Insert_header(espace_apres=15)

        # Styles
        largeur_contenu = self.taille_page[0] - 75
        style_normal = ParagraphStyle(name="normal", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10)
        style_centre = ParagraphStyle(name="centre", parent=style_normal, alignment=1)
        style_entete = ParagraphStyle(name="entete", parent=style_centre, fontName=utils_polices.FONT_BOLD)
        style_nom = ParagraphStyle(name="nom", parent=style_normal, fontName=utils_polices.FONT_BOLD, fontSize=12, leading=15)
        style_discret = ParagraphStyle(name="discret", parent=style_normal, textColor=colors.HexColor("#555555"))
        style_activite = ParagraphStyle(name="activite", parent=style_normal, fontName=utils_polices.FONT_BOLD, textColor=colors.white)
        style_note = ParagraphStyle(name="note", parent=style_discret, fontSize=7, leading=9)

        # Bloc identité et synthèse
        infos_individu = [Paragraph(escape(individu.Get_nom()), style_nom)]
        if individu.date_naiss:
            age = individu.Get_age()
            infos_individu.append(Paragraph("Né%s le %s (%d an%s)" % ("e" if individu.civilite in (2, 3, 5) else "", utils_dates.ConvertDateToFR(individu.date_naiss), age, "s" if age > 1 else ""), style_discret))
        infos_individu.append(Paragraph("Famille : %s" % escape(famille.nom or ""), style_discret))
        nbre_demandes = len(lignes)
        # Pastille avec le nombre de demandes
        pastille = Table([[Paragraph("<b>%d</b> demande%s en attente" % (nbre_demandes, "s" if nbre_demandes > 1 else ""),
                                     ParagraphStyle(name="pastille", parent=style_normal, alignment=1, textColor=colors.white))]], [110])
        pastille.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), (0.5, 0.5, 0.5)), ('ROUNDEDCORNERS', [8, 8, 8, 8]),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        # Bloc sur fond gris clair avec un liseré gris à gauche
        tableau = Table([[infos_individu, pastille]], [largeur_contenu * 0.65, largeur_contenu * 0.35])
        tableau.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), (0.95, 0.95, 0.95)), ('LINEBEFORE', (0, 0), (0, 0), 2, (0.5, 0.5, 0.5)),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (1, 0), (1, 0), 'RIGHT'), ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (0, 0), 10), ('RIGHTPADDING', (1, 0), (1, 0), 10),
        ]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 15))

        # Colonnes (la colonne Groupe absorbe l'espace restant)
        # Les colonnes Groupe et Consommations se partagent à parts égales l'espace restant
        colonnes = [("Rang", 35), ("Date", 125), ("Groupe / Évènement", 0), ("Consommations", 0)]
        largeurs_colonnes = [largeur for label, largeur in colonnes]
        largeurs_colonnes[2] = largeurs_colonnes[3] = (largeur_contenu - sum(largeurs_colonnes)) / 2

        # Regroupement par activité
        dict_activites = {}
        for ligne in sorted(lignes, key=lambda ligne: (ligne["activite"], ligne["date"], ligne["groupe"])):
            dict_activites.setdefault(ligne["activite"], []).append(ligne)

        for activite, lignes_activite in dict_activites.items():
            data_tableau = [
                [Paragraph(escape(activite), style_activite)] + [""] * (len(colonnes) - 1),
                [Paragraph(label, style_entete) for label, largeur in colonnes],
            ]
            styles = [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), (0.5, 0.5, 0.5)),
                ('BACKGROUND', (0, 1), (-1, 1), (0.9, 0.9, 0.9)),
            ]
            for num_ligne, ligne in enumerate(lignes_activite, start=2):
                groupe = escape(ligne["groupe"])
                if ligne["evenement"]:
                    groupe += "<br/><i>%s</i>" % escape(ligne["evenement"])
                data_tableau.append([
                    Paragraph(str(ligne["rang"] or ""), style_centre),
                    Paragraph(utils_dates.DateComplete(ligne["date"]).capitalize(), style_normal),
                    Paragraph(groupe, style_normal),
                    Paragraph(escape(ligne["unites"]), style_normal),
                ])
            tableau = Table(data_tableau, largeurs_colonnes, repeatRows=2)
            tableau.setStyle(TableStyle(styles))
            self.story.append(tableau)
            self.story.append(Spacer(0, 12))

        # Note explicative
        note = Paragraph("Le rang indique la position de la demande dans la liste d'attente du groupe (ou de l'évènement) à la date d'édition. "
                         "Il peut évoluer en fonction des annulations et des réattributions de places.", style_note)
        tableau = Table([[note]], [largeur_contenu])
        tableau.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0)]))
        self.story.append(tableau)
