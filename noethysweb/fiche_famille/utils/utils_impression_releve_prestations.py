# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal, datetime
logger = logging.getLogger(__name__)
from django.db.models import Sum
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.utils import utils_dates, utils_impression, utils_preferences
from core.models import Prestation, Ventilation, Facture, Famille, Consommation


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        self.Insert_header()

        couleur_fond_titre = "#D0D0D0"

        # Importation de la famille
        famille = Famille.objects.get(pk=self.dict_donnees["idfamille"])

        # Importation des factures
        factures = Facture.objects.select_related("prefixe").filter(famille_id=self.dict_donnees["idfamille"]).exclude(etat="annulation").order_by("date_edition")

        # Importation des prestations
        prestations = Prestation.objects.select_related("individu").filter(famille_id=famille.pk).order_by("date")
        prestations_facture = {}
        for prestation in prestations:
            prestations_facture.setdefault(prestation.facture_id, [])
            prestations_facture[prestation.facture_id].append(prestation.pk)

        # Importation des ventilations
        ventilations = {temp["prestation"]: temp["total"] for temp in Ventilation.objects.values("prestation").filter(famille_id=famille.pk).annotate(total=Sum("montant"))}

        # Importation des consommations
        consommations = {}
        for conso in Consommation.objects.select_related("unite").filter(inscription__famille_id=famille.pk):
            consommations.setdefault(conso.prestation_id, [])
            consommations[conso.prestation_id].append(conso)

        # Nom de la famille
        self.story.append(Paragraph("<para align='center'>%s</para>" % famille.nom, ParagraphStyle(name="standard", fontName="Helvetica-bold", fontSize=10, leading=10, spaceAfter=0)))
        self.story.append(Spacer(0,20))

        # Création des périodes
        total_reste_global = decimal.Decimal(0)
        dictPrestationsAffichees = {}

        for periode in self.dict_donnees["periodes"]:
            date_debut, date_fin = utils_dates.ConvertDateRangePicker(periode["periode"])

            # ---------------------------------------------------------------------------------------------
            # ----------------------------------------- PRESTATIONS ---------------------------------------
            # ---------------------------------------------------------------------------------------------

            if periode["type_donnee"] == "PRESTATIONS":

                # Regroupement
                mode_regroupement = periode["regroupement"]
                detail = mode_regroupement != "AUCUN"
                if mode_regroupement == "DATE": label_regroupement = "Date"
                if mode_regroupement == "MOIS": label_regroupement = "Mois"
                if mode_regroupement == "ANNEE": label_regroupement = "Année"

                # Dessin du tableau de titre pour cette période
                dataTableau = [[periode["label"],]]

                listeStyles = [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black), ('FONT', (0, 0), (-1, -1), "Helvetica", 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONT', (0, 1), (-1, -1), "Helvetica", 8),
                    ('BACKGROUND', (-1, -1), (-1, -1), couleur_fond_titre),
                ]

                tableau_titre = Table(dataTableau, [520, ])
                tableau_titre.setStyle(TableStyle(listeStyles))

                # Dessin du tableau pour les prestations
                dataTableau = []
                if detail:
                    largeursColonnes = [60, 190, 120, 50, 50, 50]
                    dataTableau.append([label_regroupement, "Prestation", "Individu", "Total dû", "Réglé", "Reste dû"])
                else:
                    largeursColonnes = [370, 50, 50, 50]
                    dataTableau.append([label_regroupement, "Total dû", "Réglé", "Reste dû"])
                paraStyle = ParagraphStyle(name="standard", fontName="Helvetica", fontSize=8, leading=10, spaceAfter=0)

                total_du = decimal.Decimal(0)
                total_regle = decimal.Decimal(0)
                total_reste = decimal.Decimal(0)

                # Regroupement
                dict_regroupement = {}
                for prestation in prestations:
                    valide = True

                    montant = prestation.montant
                    montant_ventilation = ventilations.get(prestation.pk, decimal.Decimal("0"))
                    reste_du = montant - montant_ventilation

                    # Filtre impayes
                    if periode["impayes"] and reste_du <= decimal.Decimal("0"):
                        valide = False

                    # Filtre Date
                    if periode["type_periode"] == "SELECTION" and (prestation.date < date_debut or prestation.date > date_fin):
                        valide = False

                    if valide:
                        # Création de la Key de regroupement
                        if mode_regroupement == "DATE": key = prestation.date
                        if mode_regroupement == "MOIS": key = (prestation.date.year, prestation.date.month)
                        if mode_regroupement == "ANNEE": key = prestation.date.year

                        # Mémorisation
                        dict_regroupement.setdefault(key, [])
                        dict_regroupement[key].append(prestation)

                # Tri des keys
                liste_keys = list(dict_regroupement.keys())
                liste_keys.sort()

                # Parcours des éléments
                for key in liste_keys:
                    # Key
                    if type(key) == datetime.date: label_key = utils_dates.ConvertDateToFR(key)
                    if type(key) == tuple: label_key = utils_dates.FormateMois(key)
                    if type(key) == int: label_key = "Année %d" % key
                    texteKey = Paragraph(u"<para align='center'>%s</para>" % label_key, paraStyle)

                    listeLabels = []
                    listeIndividus = []
                    listeTotalDu = []
                    listeTotalRegle = []
                    listeTotalReste = []

                    total_du_groupe = decimal.Decimal(0)
                    total_regle_groupe = decimal.Decimal(0)
                    total_reste_groupe = decimal.Decimal(0)

                    # Détail
                    for prestation in dict_regroupement[key]:

                        # Calcul des montants
                        montant = prestation.montant
                        montant_ventilation = ventilations.get(prestation.pk, decimal.Decimal(0))
                        reste_du = montant - montant_ventilation

                        # Label de la prestation
                        labelPrestation = prestation.label

                        if periode["detail_conso"]:
                            liste_consommations = consommations.get(prestation.pk, [])
                            if liste_consommations:
                                listeConsoTemp = []
                                doublons = False
                                for conso in liste_consommations:
                                    nomUnite = conso.unite.abrege
                                    if nomUnite in listeConsoTemp:
                                        doublons = True
                                    listeConsoTemp.append(nomUnite)
                                if listeConsoTemp and not doublons:
                                    labelPrestation = "%s (%s)" % (labelPrestation, "+".join(listeConsoTemp))

                        if prestation.quantite and prestation.quantite != 1:
                            labelPrestation += " - %d" % prestation.quantite

                        listeLabels.append(Paragraph(labelPrestation, paraStyle))

                        # Individu
                        listeIndividus.append(Paragraph(prestation.individu.Get_nom() if prestation.individu else "", paraStyle))

                        # Total dû
                        listeTotalDu.append(Paragraph(u"<para align='right'>%.02f %s</para>" % (montant, utils_preferences.Get_symbole_monnaie()), paraStyle))
                        total_du += montant
                        total_du_groupe += montant

                        # Réglé
                        listeTotalRegle.append(Paragraph(u"<para align='right'>%.02f %s</para>" % (montant_ventilation, utils_preferences.Get_symbole_monnaie()), paraStyle))
                        total_regle += montant_ventilation
                        total_regle_groupe += montant_ventilation

                        # Reste dû
                        listeTotalReste.append(
                            Paragraph(u"<para align='right'>%.02f %s</para>" % (reste_du, utils_preferences.Get_symbole_monnaie()), paraStyle))
                        total_reste += reste_du
                        total_reste_groupe += reste_du
                        total_reste_global += reste_du

                        dictPrestationsAffichees.setdefault(prestation.pk, 0)
                        dictPrestationsAffichees[prestation.pk] += 1

                    # Si détails ou non
                    if detail:
                        dataTableau.append([texteKey, listeLabels, listeIndividus, listeTotalDu, listeTotalRegle, listeTotalReste])
                    else:
                        dataTableau.append([
                            texteKey,
                            Paragraph(u"<para align='right'>%.02f %s</para>" % (total_du_groupe, utils_preferences.Get_symbole_monnaie()), paraStyle),
                            Paragraph(u"<para align='right'>%.02f %s</para>" % (total_regle_groupe, utils_preferences.Get_symbole_monnaie()), paraStyle),
                            Paragraph(u"<para align='right'>%.02f %s</para>" % (total_reste_groupe, utils_preferences.Get_symbole_monnaie()), paraStyle),
                        ])

                listeStyles = [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                    ('FONT', (0, 0), (-1, 0), "Helvetica", 6), ('ALIGN', (0, 0), (-1, 0), 'CENTRE'),
                    ('FONT', (0, 1), (-1, 1), "Helvetica", 8),
                ]

                if dataTableau:
                    self.story.append(tableau_titre)

                    tableau = Table(dataTableau, largeursColonnes)
                    tableau.setStyle(TableStyle(listeStyles))
                    self.story.append(tableau)

                    # Insertion du total par période
                    dataTableau = []
                    listeLigne = [
                        Paragraph("<para align='right'>Totaux :</para>", paraStyle),
                        Paragraph("<para align='right'>%.02f %s</para>" % (total_du, utils_preferences.Get_symbole_monnaie()), paraStyle),
                        Paragraph("<para align='right'>%.02f %s</para>" % (total_regle, utils_preferences.Get_symbole_monnaie()), paraStyle),
                        Paragraph("<para align='right'><b>%.02f %s</b></para>" % (total_reste, utils_preferences.Get_symbole_monnaie()),paraStyle),
                    ]
                    dataTableau.append(listeLigne)

                    listeStyles = [
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONT', (0, 0), (-1, -1), "Helvetica", 8), ('GRID', (1, -1), (-1, -1), 0.25, colors.black),
                        ('ALIGN', (-1, -1), (-1, -1), 'CENTRE'),
                        ('BACKGROUND', (-1, 0), (-1, -1), couleur_fond_titre),
                    ]

                    # Création du tableau
                    largeursColonnesTotal = [370, 50, 50, 50]
                    tableau = Table(dataTableau, largeursColonnesTotal)
                    tableau.setStyle(TableStyle(listeStyles))
                    self.story.append(tableau)
                    self.story.append(Spacer(0, 12))

            # -----------------------------------------------------------------------------------------------
            # ----------------------------------------- FACTURES --------------------------------------------
            # -----------------------------------------------------------------------------------------------

            if periode["type_donnee"] == "FACTURES":

                # Dessin du tableau de titre pour cette période
                dataTableau = [[periode["label"], ]]

                listeStyles = [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black), ('FONT', (0, 0), (-1, -1), "Helvetica", 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONT', (0, 1), (-1, -1), "Helvetica", 8),
                    ('BACKGROUND', (-1, -1), (-1, -1), couleur_fond_titre),
                ]

                tableau_titre = Table(dataTableau, [520,])
                tableau_titre.setStyle(TableStyle(listeStyles))

                # Dessin du tableau pour les prestations
                dataTableau = []
                largeursColonnes = [60, 110, 200, 50, 50, 50]
                dataTableau.append(["Date d'édition", "Numéro", "Période", "Total dû", "Réglé", "Reste dû"])

                paraStyle = ParagraphStyle(name="standard", fontName="Helvetica", fontSize=8, leading=10, spaceAfter=0)

                total_du = decimal.Decimal(0)
                total_regle = decimal.Decimal(0)
                total_reste = decimal.Decimal(0)

                for facture in factures:
                    valide = True

                    # Filtre impayes
                    if periode["impayes"] and facture.solde_actuel <= decimal.Decimal(0):
                        valide = False

                    # Filtre Date
                    if periode["type_periode"] == "SELECTION" and (facture.date_edition < date_debut or facture.date_edition > date_fin):
                        valide = False

                    if valide:
                        listeLigne = []

                        # Date d'édition
                        listeLigne.append(Paragraph(u"<para align='center'>%s</para>" % utils_dates.ConvertDateToFR(facture.date_edition), paraStyle))

                        # Numéro de facture
                        numero = "%s-%s" % (facture.prefixe, facture.numero) if facture.prefixe else facture.numero
                        listeLigne.append(Paragraph("Facture n°%s" % numero, paraStyle))

                        # Période facture
                        listeLigne.append(Paragraph("Du %s au %s" % (utils_dates.ConvertDateToFR(facture.date_debut), utils_dates.ConvertDateToFR(facture.date_fin)), paraStyle))

                        # Total dû
                        listeLigne.append(Paragraph(u"<para align='right'>%.02f %s</para>" % (facture.total, utils_preferences.Get_symbole_monnaie()), paraStyle))
                        total_du += facture.total

                        # Réglé
                        listeLigne.append(Paragraph(u"<para align='right'>%.02f %s</para>" % (facture.regle, utils_preferences.Get_symbole_monnaie()), paraStyle))
                        total_regle += facture.regle

                        # Reste dû
                        listeLigne.append(
                            Paragraph(u"<para align='right'>%.02f %s</para>" % (facture.solde_actuel, utils_preferences.Get_symbole_monnaie()), paraStyle))
                        total_reste += facture.solde_actuel
                        total_reste_global += facture.solde_actuel

                        for idprestation in prestations_facture.get(facture.pk, []):
                            dictPrestationsAffichees.setdefault(idprestation, 0)
                            dictPrestationsAffichees[idprestation] += 1

                        dataTableau.append(listeLigne)

                listeStyles = [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                    ('FONT', (0, 0), (-1, 0), "Helvetica", 6), ('ALIGN', (0, 0), (-1, 0), 'CENTRE'),
                    ('FONT', (0, 1), (-1, 1), "Helvetica", 8),
                ]

                if dataTableau:
                    self.story.append(tableau_titre)

                    tableau = Table(dataTableau, largeursColonnes)
                    tableau.setStyle(TableStyle(listeStyles))
                    self.story.append(tableau)

                    # Insertion du total par période
                    dataTableau = [[
                        Paragraph("<para align='right'>Totaux :</para>", paraStyle),
                        Paragraph("<para align='right'>%.02f %s</para>" % (total_du, utils_preferences.Get_symbole_monnaie()), paraStyle),
                        Paragraph("<para align='right'>%.02f %s</para>" % (total_regle, utils_preferences.Get_symbole_monnaie()), paraStyle),
                        Paragraph("<para align='right'><b>%.02f %s</b></para>" % (total_reste, utils_preferences.Get_symbole_monnaie()), paraStyle),
                    ]]

                    listeStyles = [
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONT', (0, 0), (-1, -1), "Helvetica", 8), ('GRID', (1, -1), (-1, -1), 0.25, colors.black),
                        ('ALIGN', (-1, -1), (-1, -1), 'CENTRE'),
                        ('BACKGROUND', (-1, 0), (-1, -1), couleur_fond_titre),
                    ]

                    # Création du tableau
                    largeursColonnesTotal = [370, 50, 50, 50]
                    tableau = Table(dataTableau, largeursColonnesTotal)
                    tableau.setStyle(TableStyle(listeStyles))
                    self.story.append(tableau)
                    self.story.append(Spacer(0, 12))


        # ---------------------------- Insertion du total du document ---------------------------
        dataTableau = []
        listeLigne = [
            Paragraph("<para align='right'><b>Reste dû :</b></para>", paraStyle),
            Paragraph(u"<para align='right'><b>%.02f %s</b></para>" % (total_reste_global, utils_preferences.Get_symbole_monnaie()), paraStyle),
        ]
        dataTableau.append(listeLigne)

        # Champs pour fusion email
        self.dict_donnees["{RESTE_DU}"] = "%.02f %s" % (total_reste_global, utils_preferences.Get_symbole_monnaie())
        self.dict_donnees["{DATE_EDITION_RELEVE}"] = utils_dates.ConvertDateToFR(datetime.date.today())

        listeStyles = [
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (-1, -1), "Helvetica", 8),
            ('GRID', (1, -1), (-1, -1), 0.25, colors.black), ('ALIGN', (-1, -1), (-1, -1), 'CENTRE'),
            ('BACKGROUND', (-1, 0), (-1, -1), couleur_fond_titre),
        ]

        # Création du tableau
        largeursColonnesTotal = [370, 150]
        tableau = Table(dataTableau, largeursColonnesTotal)
        tableau.setStyle(TableStyle(listeStyles))
        self.story.append(tableau)
        self.story.append(Spacer(0, 12))

        # Vérifie que des prestations ne sont pas présentes dans plusieurs périodes
        nbreDoublons = 0
        for IDprestation, nbre in dictPrestationsAffichees.items():
            if nbre > 1:
                nbreDoublons += 1
        if nbreDoublons > 0:
            if nbreDoublons == 1:
                texte = "Une prestation apparaît simultanément dans plusieurs périodes. Vérifiez votre paramétrage des périodes !"
            else:
                texte = "%d prestations apparaissent simultanément dans plusieurs périodes. Vérifiez votre paramétrage des périodes !" % nbreDoublons
            self.erreurs.append(texte)
