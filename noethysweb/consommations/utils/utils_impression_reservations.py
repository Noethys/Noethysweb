# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.utils import utils_dates, utils_impression, utils_preferences
from core.models import Evenement


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        self.Insert_header()

        largeurContenu = 520
        couleurFond = (0.8, 0.8, 1)
        couleurFondActivite = (0.92, 0.92, 1)

        # Texte si aucune réservation
        if len(self.dict_donnees["reservations"]) == 0:
            paraStyle = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=11)
            self.story.append(Paragraph("&nbsp;", paraStyle))
            self.story.append(Paragraph("&nbsp;", paraStyle))
            self.story.append(Paragraph("<para align='centre'><b>Aucune réservation</b></para>", paraStyle))

        # Importation des évènements utilisés
        dict_evenements = {evt.pk: evt for evt in Evenement.objects.filter(idevenement__in=self.dict_donnees["evenements"])}

        # Tableau NOM INDIVIDU
        totalFacturationFamille = 0.0
        for IDindividu, dictIndividu in self.dict_donnees["reservations"].items():
            nom = dictIndividu["nom"]
            prenom = dictIndividu["prenom"] or ""
            date_naiss = dictIndividu["date_naiss"]
            sexe = dictIndividu["sexe"]
            if date_naiss != None :
                if sexe == "M":
                    texteNaiss = ", né le %s" % utils_dates.ConvertDateToFR(str(date_naiss))
                else :
                    texteNaiss = ", née le %s" % utils_dates.ConvertDateToFR(str(date_naiss))
            else:
                texteNaiss = ""
            texteIndividu = "%s %s%s" % (nom, prenom, texteNaiss)

            totalFacturationIndividu = 0.0

            # Insertion du nom de l'individu
            paraStyle = ParagraphStyle(name="individu", fontName="Helvetica", fontSize=9, spaceBefore=0, spaceafter=0)
            texteIndividu = Paragraph(texteIndividu, paraStyle)
            dataTableau = []
            dataTableau.append([texteIndividu,])
            tableau = Table(dataTableau, [largeurContenu,])
            listeStyles = [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONT', (0, 0), (-1, -1), "Helvetica", 8),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), couleurFond),
                    ]
            tableau.setStyle(TableStyle(listeStyles))
            self.story.append(tableau)

            # Tableau NOM ACTIVITE
            listePrestationsUtilisees = []
            for IDactivite, dictActivite in dictIndividu["activites"].items() :
                texteActivite = dictActivite["nom"]
                if dictActivite["agrement"] != None :
                    texteActivite += " - Agrément n°%s" % dictActivite["agrement"]

                if texteActivite != None :
                    dataTableau = []
                    dataTableau.append([texteActivite,])
                    tableau = Table(dataTableau, [largeurContenu,])
                    listeStyles = [
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONT', (0, 0), (-1, -1), "Helvetica", 6),
                        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('BACKGROUND', (0, 0), (-1, 0), couleurFondActivite),
                        ]
                    tableau.setStyle(TableStyle(listeStyles))
                    self.story.append(tableau)

                # Colonnes : Date, Consos, Etat, Prestations, Montant
                dataTableau = []
                largeursColonnes = [55, 165, 80, 160, 60]
                dataTableau.append(["Date", "Consommations", "Etat", "Prestations", "Total"])

                paraStyle = ParagraphStyle(name="standard", fontName="Helvetica", fontSize=8, leading=10, spaceAfter=0)

                # lignes DATES
                listeDates = []
                for date, dictDates in dictActivite["dates"].items():
                    listeDates.append(date)
                listeDates.sort()

                for date in listeDates:
                    dictDate = dictActivite["dates"][date]
                    listeLigne = []

                    # Insertion de la date
                    texteDate = Paragraph(utils_dates.ConvertDateToFR(str(date)), paraStyle)

                    # Insertion des consommations
                    listeEtats = []
                    listeConso = []
                    listePrestations = []
                    for IDunite, dictUnite in dictDate.items():
                        nomUnite = dictUnite["nomUnite"]
                        etat = dictUnite["etat"]
                        idevenement = dictUnite["conso"]["evenement"]

                        if etat != None :
                            labelUnite = nomUnite
                            if dictUnite["type"] == "Horaire":
                                heure_debut = dictUnite["heure_debut"]
                                if heure_debut == None : heure_debut = "?"
                                heure_debut = heure_debut.replace(":", "h")
                                heure_fin = dictUnite["heure_fin"]
                                if heure_fin == None : heure_fin = "?"
                                heure_fin = heure_fin.replace(":", "h")
                                labelUnite += " (de %s à %s)" % (heure_debut, heure_fin)

                            if dictUnite["type"] == "Evenement":
                                evenement = dict_evenements[idevenement]
                                labelUnite += " : %s" % evenement.nom
                                if evenement.description:
                                    labelUnite += " <font color='#7e7e7e' size='7'>(%s)</font>" % evenement.description

                            listeConso.append(labelUnite)

                            if etat not in listeEtats :
                                listeEtats.append(etat)

                            IDprestation = dictUnite["IDprestation"]
                            if dictUnite["prestation"] != None and IDprestation not in listePrestationsUtilisees:
                                listePrestations.append(dictUnite["prestation"])
                                listePrestationsUtilisees.append(IDprestation)

                    texteConsos = Paragraph(" + ".join(listeConso), paraStyle)

                    # Insertion de l'état
                    texteEtat = Paragraph(" / ".join(listeEtats), paraStyle)

                    # Insertion des prestations et montants
                    textePrestations = []
                    texteMontants = []
                    for dictPrestation in listePrestations :
                        montant = dictPrestation["montant"]
                        label = dictPrestation["label"]
                        textePrestations.append(Paragraph(label, paraStyle))
                        texteMontants.append(Paragraph("<para align='right'>%.02f %s</para>" % (montant, utils_preferences.Get_symbole_monnaie()), paraStyle))

                        # Pour le total par individu :
                        if montant != None :
                            totalFacturationIndividu += montant
                            totalFacturationFamille += montant

                    if len(listeConso) > 0:
                        dataTableau.append([texteDate, texteConsos, texteEtat, textePrestations, texteMontants])

                tableau = Table(dataTableau, largeursColonnes)
                listeStyles = [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1,-1), 0.25, colors.black),

                    ('FONT', (0, 0), (-1, 0), "Helvetica", 6),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTRE'),

                    ('FONT', (0, 1), (-1, 1), "Helvetica", 8),
                    ]
                tableau.setStyle(TableStyle(listeStyles))
                self.story.append(tableau)

            # Insertion du total par individu
            dataTableau = []
            montantIndividu = Paragraph("<para align='right'>%.02f %s</para>" % (totalFacturationIndividu, utils_preferences.Get_symbole_monnaie()), paraStyle)
            dataTableau.append([Paragraph("<para align='right'>Total :</para>", paraStyle), montantIndividu])

            listeStyles = [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONT', (0, 0), (-1, -1), "Helvetica", 8),
                    ('GRID', (-1, -1), (-1,-1), 0.25, colors.black),
                    ('ALIGN', (-1, -1), (-1, -1), 'CENTRE'),
                    ('BACKGROUND', (-1, -1), (-1, -1), couleurFond),
                    ]

            # Création du tableau
            largeursColonnesTotal = [460, 60]
            tableau = Table(dataTableau, largeursColonnesTotal)
            tableau.setStyle(TableStyle(listeStyles))
            self.story.append(tableau)
            self.story.append(Spacer(0, 12))

        # Total facturation Famille
        nbreIndividus = len(self.dict_donnees["reservations"])
        if nbreIndividus > 1:
            dataTableau = []
            montantFamille = Paragraph("<para align='right'>%.02f %s</para>" % (totalFacturationFamille, utils_preferences.Get_symbole_monnaie()), paraStyle)
            dataTableau.append([Paragraph("<para align='right'>TOTAL :</para>", paraStyle), montantFamille])
            largeursColonnesTotal = [460, 60]
            tableau = Table(dataTableau, largeursColonnesTotal)
            tableau.setStyle(TableStyle(listeStyles))
            self.story.append(tableau)

        # Champs pour fusion Email
        self.dict_donnees["{SOLDE}"] = "%.02f %s" % (totalFacturationFamille, utils_preferences.Get_symbole_monnaie())

