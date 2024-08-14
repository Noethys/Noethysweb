# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from decimal import Decimal
from operator import itemgetter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import DocAssign
from core.models import MessageFacture
from core.utils import utils_dates, utils_impression, utils_preferences


def PeriodeComplete(mois, annee):
    listeMois = ("Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre")
    periodeComplete = "%s %d" % (listeMois[mois-1], annee)
    return periodeComplete

def GetDatesListes(listeDates):
    listeDatesTemp = []
    for dictTemp in listeDates :
        if type(dictTemp) == dict :
            date = dictTemp["date"]
        else :
            date = dictTemp
        if date not in listeDatesTemp :
            listeDatesTemp.append(date)
    return listeDatesTemp


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        self.mode = kwds.pop("mode", "facture")
        self.messages = MessageFacture.objects.all()
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        styleSheet = getSampleStyleSheet()
        h3 = styleSheet['Heading3']
        styleTexte = styleSheet['BodyText'] 
        styleTexte.fontName = "Helvetica"
        styleTexte.fontSize = 9
        styleTexte.borderPadding = 9
        styleTexte.leading = 12

        # Importation des messages de factures
        messages_factures = []
        for message in self.messages:
            if message.texte[-1] not in "!?.": message.texte += "."
            messages_factures.append("<b>%s : </b>%s" % (message.titre, message.texte))

        # ----------- Insertion du contenu des frames --------------
        listeNomsSansCivilite = []
        for IDfamille, dictValeur in self.dict_donnees.items():
            if isinstance(dictValeur, dict):
                listeNomsSansCivilite.append((dictValeur["nomSansCivilite"], IDfamille))
        listeNomsSansCivilite.sort() 
        
        for nomSansCivilite, IDfamille in listeNomsSansCivilite:
            dictValeur = self.dict_donnees[IDfamille]
            if dictValeur["select"] == True:
                
                self.story.append(DocAssign("ID", IDfamille))
                nomSansCivilite = dictValeur["nomSansCivilite"]
                self.story.append(utils_impression.Bookmark(nomSansCivilite, str(IDfamille)))

                # ------------------- TITRE -----------------
                if self.dict_options["afficher_titre"] == True:
                    titre = ""
                    if self.mode == "facture": titre = "Facture"
                    if self.mode == "attestation": titre = "Attestation de présence"
                    if self.mode == "devis": titre = "Devis"
                    if "texte_titre" in dictValeur: titre = dictValeur["texte_titre"]
                    dataTableau = []
                    largeursColonnes = [self.taille_cadre[2], ]
                    dataTableau.append((titre,))
                    dateDebut = dictValeur["date_debut"]
                    dateFin = dictValeur["date_fin"]

                    # if dictValeur["{NOM_LOT}"] and "PORTAGE" in dictValeur["{NOM_LOT}"].upper():
                    #     dateFin = dateDebut - datetime.timedelta(days=1)
                    #     dateDebut = datetime.date(year=dateFin.year, month=dateFin.month, day=1)

                    if self.dict_options["afficher_periode"] == True:
                        dataTableau.append((u"Période du %s au %s" % (utils_dates.ConvertDateENGtoFR(str(dateDebut)), utils_dates.ConvertDateENGtoFR(str(dateFin))),))
                    styles = [
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('FONT', (0, 0), (0, 0), "Helvetica-Bold", int(self.dict_options["taille_texte_titre"])),
                            ('LINEBELOW', (0, 0), (0 ,0), 0.25, colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ]

                    if self.dict_options["afficher_periode"] == True:
                        styles.append(('FONT', (0, 1), (0, 1), "Helvetica", int(self.dict_options["taille_texte_periode"])))
                    tableau = Table(dataTableau, largeursColonnes)
                    tableau.setStyle(TableStyle(styles))
                    self.story.append(tableau)
                    self.story.append(Spacer(0, 20))

                if self.dict_options["texte_introduction"] != "":
                    paraStyle = ParagraphStyle(name="introduction",
                                          fontName="Helvetica",
                                          fontSize=int(self.dict_options["taille_texte_introduction"]),
                                          leading=14,
                                          spaceBefore=0,
                                          spaceafter=0,
                                          leftIndent=5,
                                          rightIndent=5,
                                          alignment=int(self.dict_options["alignement_texte_introduction"]),
                                          backColor=self.dict_options["couleur_fond_introduction"],
                                          borderColor=self.dict_options["couleur_bord_introduction"],
                                          borderWidth=0.5,
                                          borderPadding=5)
                    texte = dictValeur["texte_introduction"].replace("\\n", "<br/>")
                    if self.dict_options["style_texte_introduction"] == "0": texte = "<para>%s</para>" % texte
                    if self.dict_options["style_texte_introduction"] == "1": texte = "<para><i>%s</i></para>" % texte
                    if self.dict_options["style_texte_introduction"] == "2": texte = "<para><b>%s</b></para>" % texte
                    if self.dict_options["style_texte_introduction"] == "3": texte = "<para><i><b>%s</b></i></para>" % texte
                    self.story.append(Paragraph(texte, paraStyle))
                    self.story.append(Spacer(0, 20))

                    
                couleurFond = self.dict_options["couleur_fond_1"]
                couleurFondActivite = self.dict_options["couleur_fond_2"]

                # ------------------- TABLEAU CONTENU -----------------
                montantPeriode = Decimal(0)
                montantVentilation = Decimal(0)
                nbre_total_prestations_anterieures = 0

                # Recherche si TVA utilisée
                activeTVA = False
                for IDindividu, dictIndividus in dictValeur["individus"].items():
                    for IDactivite, dictActivites in dictIndividus["activites"].items():
                        for date, dictDates in dictActivites["presences"].items():
                            for dictPrestation in dictDates["unites"] :
                                if dictPrestation["tva"] != None and dictPrestation["tva"] != 0.0:
                                    activeTVA = True

                # Remplissage
                listeIndividusTemp = []
                for IDindividu, dictIndividus in dictValeur["individus"].items():
                    listeIndividusTemp.append((dictIndividus["texte"], IDindividu, dictIndividus))
                listeIndividusTemp.sort() 
                
                for texteTemp, IDindividu, dictIndividus in listeIndividusTemp:
                    
                    if dictIndividus["select"] == True :

                        nbre_prestations_anterieures = 0
                        listeIndexActivites = []
                        montantPeriode += dictIndividus["total"]
                        montantVentilation += dictIndividus["ventilation"]
                        
                        # Initialisation des largeurs de tableau
                        largeurColonneDate = int(self.dict_options["largeur_colonne_date"])
                        largeurColonneMontantHT = int(self.dict_options["largeur_colonne_montant_ht"])
                        largeurColonneTVA = int(self.dict_options["largeur_colonne_montant_tva"])
                        largeurColonneMontantTTC = int(self.dict_options["largeur_colonne_montant_ttc"])
                        largeurColonneBaseTTC = int(largeurColonneMontantTTC)
                        
                        if activeTVA == True and self.dict_options["affichage_prestations"] == "0":
                            largeurColonneIntitule = self.taille_cadre[2] - largeurColonneDate - largeurColonneMontantHT - largeurColonneTVA - largeurColonneMontantTTC
                            largeursColonnes = [largeurColonneDate, largeurColonneIntitule, largeurColonneMontantHT, largeurColonneTVA, largeurColonneMontantTTC]
                        else :
                            if self.dict_options["affichage_prestations"] != "0":
                                largeurColonneIntitule = self.taille_cadre[2] - largeurColonneDate - largeurColonneBaseTTC - largeurColonneMontantTTC
                                largeursColonnes = [largeurColonneDate, largeurColonneIntitule, largeurColonneBaseTTC, largeurColonneMontantTTC]
                            else :
                                largeurColonneIntitule = self.taille_cadre[2] - largeurColonneDate - largeurColonneMontantTTC
                                largeursColonnes = [largeurColonneDate, largeurColonneIntitule, largeurColonneMontantTTC]
                        
                        # Insertion du nom de l'individu
                        paraStyle = ParagraphStyle(name="individu",
                                              fontName="Helvetica",
                                              fontSize=int(self.dict_options["taille_texte_individu"]),
                                              leading=int(self.dict_options["taille_texte_individu"]+2),
                                              spaceBefore=0,
                                              spaceafter=0)
                        texteIndividu = Paragraph(dictIndividus["texte"], paraStyle)
                        dataTableau = []
                        dataTableau.append([texteIndividu,])
                        tableau = Table(dataTableau, [self.taille_cadre[2],])
                        listeStyles = [
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('FONT', (0, 0), (-1, -1), "Helvetica", int(self.dict_options["taille_texte_individu"])),
                                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                                ('BACKGROUND', (0, 0), (-1, 0), couleurFond),
                                ]
                        tableau.setStyle(TableStyle(listeStyles))
                        self.story.append(tableau)
                        
                        # Insertion du nom de l'activité
                        listeIDactivite = []
                        for IDactivite, dictActivites in dictIndividus["activites"].items():
                            listeIDactivite.append((dictActivites["texte"] or "", IDactivite, dictActivites))
                        listeIDactivite = sorted(listeIDactivite, key=itemgetter(0))
                        
                        for texteActivite, IDactivite, dictActivites in listeIDactivite:

                            texteActivite = dictActivites["texte"]
                            if texteActivite != None :
                                dataTableau = []
                                dataTableau.append([texteActivite,])
                                tableau = Table(dataTableau, [self.taille_cadre[2],])
                                listeStyles = [
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('FONT', (0, 0), (-1, -1), "Helvetica", int(self.dict_options["taille_texte_activite"])),
                                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                    ('BACKGROUND', (0, 0), (-1, 0), couleurFondActivite),
                                    ]
                                tableau.setStyle(TableStyle(listeStyles))
                                self.story.append(tableau)

                            # Style de paragraphe normal
                            paraStyle = ParagraphStyle(name="prestation",
                                          fontName="Helvetica",
                                          fontSize=int(self.dict_options["taille_texte_prestation"]),
                                          leading=int(self.dict_options["taille_texte_prestation"]),
                                          spaceBefore=0,
                                          spaceAfter=0)

                            paraLabelsColonnes = ParagraphStyle(name="paraLabelsColonnes",
                                          fontName="Helvetica",
                                          fontSize=int(self.dict_options["taille_texte_noms_colonnes"]),
                                          leading=int(self.dict_options["taille_texte_noms_colonnes"]),
                                          spaceBefore=0,
                                          spaceAfter=0)

                            paraStyleDatesForfait = ParagraphStyle(name="prestation", fontName="Helvetica", fontSize=int(self.dict_options["taille_texte_prestation"]),
                                                                   leading=int(self.dict_options["taille_texte_prestation"]), spaceBefore=2, spaceAfter=0)

                            if self.dict_options["affichage_prestations"] != "0":
                                
                                # -------------- MODE REGROUPE ----------------
                                
                                # Regroupement par prestations identiques
                                dictRegroupement = {}
                                for date, dictDates in dictActivites["presences"].items():
                                    total = dictDates["total"]
                                    for dictPrestation in dictDates["unites"]:
                                        label = dictPrestation["label"]
                                        listeDatesUnite = GetDatesListes(dictPrestation["listeDatesConso"])
                                        montant = dictPrestation["montant"]
                                        deductions = dictPrestation["deductions"]
                                        tva = dictPrestation["tva"]
                                        quantite = dictPrestation["quantite"] or 1
                                        montant_unitaire = dictPrestation["montant"] / dictPrestation["quantite"]
                                        
                                        if self.dict_options["affichage_prestations"] in ("1", "3"): labelkey = label
                                        if self.dict_options["affichage_prestations"] in ("2", "4"): labelkey = label + " P.U. " + "%.2f %s" % (montant_unitaire, utils_preferences.Get_symbole_monnaie())

                                        # Si c'est une prestation antérieure
                                        if date < dictValeur["date_debut"]:
                                            nbre_prestations_anterieures += 1
                                            nbre_total_prestations_anterieures += 1
                                            label += "*"

                                        if (labelkey in dictRegroupement) == False:
                                            dictRegroupement[labelkey] = {"labelpresta": label, "total": 0, "nbre": 0, "base": 0, "dates_forfait": None, "dates": []}
                                            dictRegroupement[labelkey]["base"] = montant_unitaire

                                        dictRegroupement[labelkey]["total"] += montant
                                        dictRegroupement[labelkey]["nbre"] += quantite
                                        dictRegroupement[labelkey]["dates"] += listeDatesUnite
                                        
                                        # if self.dict_options["affichage_prestations"] in ("1", "3"):
                                        #     dictRegroupement[labelkey]["base"] = dictRegroupement[labelkey]["total"] / dictRegroupement[labelkey]["nbre"]

                                        if len(listeDatesUnite) > 1:
                                            listeDatesUnite.sort()
                                            date_debut = listeDatesUnite[0]
                                            date_fin = listeDatesUnite[-1]
                                            nbreDates = len(listeDatesUnite)
                                            dictRegroupement[labelkey]["dates_forfait"] = "<BR/><font size=5>Du %s au %s soit %d jours</font>" % (utils_dates.ConvertDateENGtoFR(date_debut), utils_dates.ConvertDateENGtoFR(date_fin), nbreDates)
        
                                # Insertion des prestations regroupées
                                listeLabels = list(dictRegroupement.keys()) 
                                listeLabels.sort() 

                                dataTableau = [(
                                    Paragraph("<para align='center'>Quantité</para>", paraLabelsColonnes),
                                    Paragraph("<para align='center'>Prestation</para>", paraLabelsColonnes),
                                    Paragraph("<para align='center'>Base</para>", paraLabelsColonnes),
                                    Paragraph("<para align='center'>Montant</para>", paraLabelsColonnes),
                                    ),]

                                for labelkey in listeLabels :
                                    label = dictRegroupement[labelkey]["labelpresta"]
                                    nbre = dictRegroupement[labelkey]["nbre"]
                                    total = dictRegroupement[labelkey]["total"]
                                    base = dictRegroupement[labelkey]["base"]

                                    # Ajout des dates
                                    texte_dates = ""
                                    if self.dict_options["affichage_prestations"] in ("3", "4") and dictRegroupement[labelkey]["dates"]:
                                        dictRegroupement[labelkey]["dates"].sort()
                                        texte_dates = u"<br/><font size=5>(%s)</font>" % ", ".join([utils_dates.ConvertDateToFR(date) for date in dictRegroupement[labelkey]["dates"]])

                                    if dictValeur["{NOM_LOT}"] and ("PORTAGE" in dictValeur["{NOM_LOT}"].upper() or "MINIBUS" in dictValeur["{NOM_LOT}"].upper()):
                                        texte_dates = ""

                                    if texte_dates:
                                        label += texte_dates

                                    # recherche d'un commentaire
                                    if "dictCommentaires" in self.dict_options:
                                        key = (label, IDactivite)
                                        if key in self.dict_options["dictCommentaires"]:
                                            commentaire = self.dict_options["dictCommentaires"][key]
                                            label = "%s <i><font color='#939393'>%s</font></i>" % (label, commentaire)
                                            
                                    # Formatage du label
                                    intitule = Paragraph(label, paraStyle)
                                    
                                    # Rajout des dates de forfait
                                    #dates_forfait = dictRegroupement[label]["dates_forfait"]
                                    #if dates_forfait != None :
                                    #    intitule = [intitule, Paragraph(dates_forfait, paraStyle)]

                                    dataTableau.append([Paragraph("<para align='center'>%d</para>" % nbre, paraStyle), intitule, Paragraph("<para align='center'>%.02f %s</para>" % (base, utils_preferences.Get_symbole_monnaie()), paraStyle), Paragraph(u"<para align='center'>%.02f %s</para>" % (total, utils_preferences.Get_symbole_monnaie()), paraStyle)])
 
                            else:
                                
                                # -------------------------------------------------------------- MODE DETAILLE ------------------------------------------------------------------


                                # Insertion de la date
                                listeDates = []
                                for date, dictDates in dictActivites["presences"].items():
                                    listeDates.append(date)
                                listeDates.sort() 
                                
                                paraStyle = ParagraphStyle(name="prestation",
                                              fontName="Helvetica",
                                              fontSize=int(self.dict_options["taille_texte_prestation"]),
                                              leading=int(self.dict_options["taille_texte_prestation"]),
                                              spaceBefore=0,
                                              spaceAfter=0)

                                dataTableau = []

                                if activeTVA == True :
                                    dataTableau.append([
                                        Paragraph("<para align='center'>Date</para>", paraLabelsColonnes),
                                        Paragraph("<para align='center'>Prestation</para>", paraLabelsColonnes),
                                        Paragraph("<para align='center'>Montant HT</para>", paraLabelsColonnes),
                                        Paragraph("<para align='center'>Taux TVA</para>", paraLabelsColonnes),
                                        Paragraph("<para align='center'>Montant TTC</para>", paraLabelsColonnes),
                                        ])

                                for date in listeDates:
                                    dictDates = dictActivites["presences"][date]

                                    dateFr = dictDates["texte"]
                                    prestations = dictDates["unites"]
                                    
                                    # Insertion des unités de présence
                                    listeIntitules = []
                                    listeMontantsHT = []
                                    listeTVA = []
                                    listeMontantsTTC = []
                                    texteIntitules = ""
                                    texteMontantsHT = ""
                                    texteTVA = ""
                                    texteMontantsTTC = ""
                                    
                                    # Tri par ordre alpha des prestations
                                    listeDictPrestations = []
                                    for dictPrestation in prestations:
                                        listeDictPrestations.append((dictPrestation["label"], dictPrestation))
                                    listeDictPrestations = sorted(listeDictPrestations, key=itemgetter(0))
                                    
                                    for labelTemp, dictPrestation in listeDictPrestations:
                                        label = dictPrestation["label"]
                                        listeDatesUnite = GetDatesListes(dictPrestation["listeDatesConso"])
                                        montant_initial = dictPrestation["montant_initial"]
                                        montant = dictPrestation["montant"]
                                        deductions = dictPrestation["deductions"]
                                        tva = dictPrestation["tva"]

                                        # Date
                                        texteDate = Paragraph("<para align='center'>%s</para>" % dateFr, paraStyle)
                                        
                                        # recherche d'un commentaire
                                        if "dictCommentaires" in self.dict_options:
                                            key = (label, IDactivite)
                                            if key in self.dict_options["dictCommentaires"]:
                                                commentaire = self.dict_options["dictCommentaires"][key]
                                                label = "%s <i><font color='#939393'>%s</font></i>" % (label, commentaire)

                                        # Si c'est une prestation antérieure
                                        if date < dictValeur["date_debut"]:
                                            nbre_prestations_anterieures += 1
                                            nbre_total_prestations_anterieures += 1
                                            label += "*"

                                        # Affiche le Label de la prestation
                                        listeIntitules.append(Paragraph(label, paraStyle)) 
                                        
                                        # Recherche si c'est un forfait
                                        if len(listeDatesUnite) > 1:
                                            listeDatesUnite.sort()
                                            date_debut = listeDatesUnite[0]
                                            date_fin = listeDatesUnite[-1]
                                            nbreDates = len(listeDatesUnite)
                                            label = "<font size=5>Du %s au %s soit %d jours</font>" % (utils_dates.ConvertDateENGtoFR(date_debut), utils_dates.ConvertDateENGtoFR(date_fin), nbreDates)
                                            listeIntitules.append(Paragraph(label, paraStyleDatesForfait))
                                                                                
                                        # TVA
                                        if activeTVA == True:
                                            if tva == None : tva = 0.0
                                            montantHT = (100.0 * float(montant)) / (100 + float(tva))
                                            listeMontantsHT.append(Paragraph("<para align='center'>%.02f %s</para>" % (montantHT, utils_preferences.Get_symbole_monnaie()), paraStyle))
                                            listeTVA.append(Paragraph("<para align='center'>%.02f %%</para>" % tva, paraStyle))
                                        else :
                                            listeMontantsHT.append("")
                                            listeTVA.append("")
                                            
                                        # Affiche total
                                        listeMontantsTTC.append(Paragraph(u"<para align='center'>%.02f %s</para>" % (montant, utils_preferences.Get_symbole_monnaie()), paraStyle))
                                    
                                        # Déductions
                                        if len(deductions) > 0:
                                            for dictDeduction in deductions :
                                                listeIntitules.append(Paragraph("<para align='left'><font size=5 color='#939393'>- %.02f %s : %s</font></para>" % (dictDeduction["montant"], utils_preferences.Get_symbole_monnaie(), dictDeduction["label"]), paraStyle))
                                                #listeIntitules.append(Paragraph("<para align='left'><font size=5 color='#939393'>%s</font></para>" % dictDeduction["label"], paraStyle))
                                                listeMontantsHT.append(Paragraph("&nbsp;", paraStyle))
                                                listeTVA.append(Paragraph("&nbsp;", paraStyle))
                                                listeMontantsTTC.append(Paragraph("&nbsp;", paraStyle))
                                                #listeMontantsTTC.append(Paragraph(u"<para align='center'><font size=5 color='#939393'>- %.02f %s</font></para>" % (dictDeduction["montant"], utils_preferences.Get_symbole_monnaie()), paraStyle))
                                                
                                        
                                    if len(listeIntitules) == 1:
                                        texteIntitules = listeIntitules[0]
                                        texteMontantsHT = listeMontantsHT[0]
                                        texteTVA = listeTVA[0]
                                        texteMontantsTTC = listeMontantsTTC[0]
                                    if len(listeIntitules) > 1:
                                        texteIntitules = listeIntitules
                                        texteMontantsHT = listeMontantsHT
                                        texteTVA = listeTVA
                                        texteMontantsTTC = listeMontantsTTC
                                                                        
                                    if activeTVA == True :
                                        dataTableau.append([texteDate, texteIntitules, texteMontantsHT, texteTVA, texteMontantsTTC])
                                    else :
                                        dataTableau.append([texteDate, texteIntitules, texteMontantsTTC])
                                    
                            # Style du tableau des prestations
                            tableau = Table(dataTableau, largeursColonnes)
                            listeStyles = [
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('FONT', (0, 0), (-1, -1), "Helvetica", int(self.dict_options["taille_texte_prestation"])),
                                ('GRID', (0, 0), (-1,-1), 0.25, colors.black), 
                                ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
                                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                                ('TOPPADDING', (0, 0), (-1, -1), 1), 
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 3), 
                                ]
                            tableau.setStyle(TableStyle(listeStyles))
                            self.story.append(tableau)

                        # Préparation du texet des prestations antérieures
                        if nbre_prestations_anterieures == 0:
                            texte_prestations_anterieures = ""
                        elif nbre_prestations_anterieures == 1:
                            texte_prestations_anterieures = "* 1 prestation antérieure reportée"
                        else :
                            texte_prestations_anterieures = "* %d prestations antérieures reportées" % nbre_prestations_anterieures

                        # Insertion des totaux
                        dataTableau = []
                        if activeTVA == True and self.dict_options["affichage_prestations"] == "0":
                            dataTableau.append([texte_prestations_anterieures, "", "", "", Paragraph("<para align='center'>%.02f %s</para>" % (dictIndividus["total"], utils_preferences.Get_symbole_monnaie()), paraStyle)])
                        else :
                            if self.dict_options["affichage_prestations"] != "0" :
                                dataTableau.append([texte_prestations_anterieures, "", "", Paragraph("<para align='center'>%.02f %s</para>" % (dictIndividus["total"], utils_preferences.Get_symbole_monnaie()), paraStyle)])
                            else :
                                dataTableau.append([texte_prestations_anterieures, "", Paragraph("<para align='center'>%.02f %s</para>" % (dictIndividus["total"], utils_preferences.Get_symbole_monnaie()), paraStyle)])
                        
                        listeStyles = [
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('FONT', (0, 0), (-1, -1), "Helvetica", int(self.dict_options["taille_texte_prestation"])),
                                ('GRID', (-1, -1), (-1,-1), 0.25, colors.black), 
                                ('ALIGN', (-1, -1), (-1, -1), 'CENTRE'),
                                ('BACKGROUND', (-1, -1), (-1, -1), couleurFond), 
                                ('TOPPADDING', (0, 0), (-1, -1), 1), 
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                                ('SPAN', (0, -1), (-2, -1)), # Fusion de la dernière ligne pour le texte_prestations_anterieures
                                ('FONT', (0, -1), (0, -1), "Helvetica", int(self.dict_options["taille_texte_prestations_anterieures"])),
                            ]
                            
                        # Création du tableau
                        tableau = Table(dataTableau, largeursColonnes)
                        tableau.setStyle(TableStyle(listeStyles))
                        self.story.append(tableau)
                        self.story.append(Spacer(0, 10))
                
                # Intégration des messages, des reports et des qf
                listeMessages = []
                paraStyle = ParagraphStyle(name="message",
                                          fontName="Helvetica",
                                          fontSize=int(self.dict_options["taille_texte_messages"]),
                                          leading=int(self.dict_options["taille_texte_messages"]),
                                          spaceAfter=2)

                # Texte Prestations antérieures
                texte_prestations_anterieures = self.dict_options["texte_prestations_anterieures"]
                if nbre_total_prestations_anterieures > 0 and len(texte_prestations_anterieures) > 0:
                    texte = "<b>%d prestations antérieures : </b>%s" % (nbre_total_prestations_anterieures, texte_prestations_anterieures)
                    listeMessages.append(Paragraph(texte, paraStyle))

                # QF aux dates de facture
                if self.mode == "facture" and self.dict_options["afficher_qf_dates"] == True:
                    dictQfdates = dictValeur["qfdates"]
                    listeDates = list(dictQfdates.keys()) 
                    listeDates.sort() 
                    if len(listeDates) > 0:
                        for dates in listeDates :
                            qf = dictQfdates[dates]
                            texteQf = "<b>Votre quotient familial : </b>Votre QF est de %s sur la période %s." % (qf, dates)
                            listeMessages.append(Paragraph(texteQf, paraStyle))

                # Reports
                if self.mode == "facture" and self.dict_options["afficher_impayes"] == True:
                    dictReports = dictValeur["reports"]
                    listePeriodes = list(dictReports.keys()) 
                    listePeriodes.sort() 
                    if len(listePeriodes) > 0:
                        if self.dict_options["integrer_impayes"] == True:
                            texteReport = "<b>Détail des impayés : </b>"
                        else :
                            texteReport = "<b>Impayés : </b>Merci de bien vouloir nous retourner également le règlement des prestations impayées suivantes : "
                        for periode in listePeriodes:
                            annee, mois = periode
                            nomPeriode = PeriodeComplete(mois, annee)
                            montant_impaye = dictReports[periode]
                            texteReport += "%s (%.02f %s), " % (nomPeriode, montant_impaye, utils_preferences.Get_symbole_monnaie())
                        texteReport = texteReport[:-2] + "."
                        listeMessages.append(Paragraph(texteReport, paraStyle))
                
                # Règlements
                if self.mode == "facture" and self.dict_options["afficher_reglements"] == True:
                    dictReglements = dictValeur["reglements"]
                    if len(dictReglements) > 0 :
                        listeTextesReglements = []
                        for IDreglement, dictTemp in dictReglements.items():
                            if dictTemp["emetteur"] not in ("", None) :
                                emetteur = " (%s) " % dictTemp["emetteur"]
                            else :
                                emetteur = ""
                            if dictTemp["numero"] not in ("", None) :
                                numero = " n°%s " % dictTemp["numero"]
                            else :
                                numero = ""
                                
                            montantReglement = "%.02f %s" % (dictTemp["montant"], utils_preferences.Get_symbole_monnaie())
                            montantVentilation = "%.02f %s" % (dictTemp["ventilation"], utils_preferences.Get_symbole_monnaie())
                            if dictTemp["ventilation"] != dictTemp["montant"] :
                                texteMontant = u"%s utilisés sur %s" % (montantVentilation, montantReglement)
                            else :
                                texteMontant = montantReglement
                                
                            texte = "%s%s%s de %s (%s)" % (dictTemp["mode"], numero, emetteur, dictTemp["payeur"], texteMontant)
                            listeTextesReglements.append(texte)
                        
                        if dictValeur["solde"] > Decimal(0) :
                            intro = "Période partiellement réglée avec"
                        else :
                            intro = "Période réglée en intégralité avec"
                            
                        texteReglements = "<b>Règlement : </b> %s %s." % (intro, " + ".join(listeTextesReglements))
                        listeMessages.append(Paragraph(texteReglements, paraStyle))
                                
                # Messages
                if self.mode == "facture":
                    if self.dict_options["afficher_messages"] == True:
                        for message in messages_factures:
                            listeMessages.append(Paragraph(message, paraStyle))
                        for note in dictValeur["messages_familiaux"]:
                            texte = note.texte
                            if len(texte) > 0 and texte[-1] not in ".!?":
                                texte = texte + "."
                            texte = "<b>Message : </b>%s" % texte
                            listeMessages.append(Paragraph(texte, paraStyle))

                if len(listeMessages) > 0:
                    listeMessages.insert(0, Paragraph("<u>Informations :</u>", paraStyle))
                
                # ------------------ CADRE TOTAUX ------------------------
                dataTableau = []
                largeurColonneLabel = 110
                largeursColonnes = [self.taille_cadre[2] - largeurColonneMontantTTC - largeurColonneLabel, largeurColonneLabel, largeurColonneMontantTTC]

                if not self.dict_options["afficher_deja_paye"] and not self.dict_options["afficher_reste_regler"]:
                    if dictValeur["total_tva"]:
                        dataTableau.append((listeMessages, "Total HT :", "%.02f %s" % (dictValeur["total"] - dictValeur["total_tva"], utils_preferences.Get_symbole_monnaie())))
                        dataTableau.append((listeMessages, "Total TVA :", "%.02f %s" % (dictValeur["total_tva"], utils_preferences.Get_symbole_monnaie())))
                        dataTableau.append((listeMessages, "Total TTC :", "%.02f %s" % (dictValeur["total"], utils_preferences.Get_symbole_monnaie())))
                    else:
                        dataTableau.append((listeMessages, "Total :", "%.02f %s" % (dictValeur["total"], utils_preferences.Get_symbole_monnaie())))
                else:
                    if dictValeur["total_tva"]:
                        dataTableau.append((listeMessages, "Total HT période :", "%.02f %s" % (dictValeur["total"] - dictValeur["total_tva"], utils_preferences.Get_symbole_monnaie())))
                        dataTableau.append((listeMessages, "Total TVA période :", "%.02f %s" % (dictValeur["total_tva"], utils_preferences.Get_symbole_monnaie())))
                        dataTableau.append((listeMessages, "Total TTC période :", "%.02f %s" % (dictValeur["total"], utils_preferences.Get_symbole_monnaie())))
                    else:
                        dataTableau.append((listeMessages, "Total période :", u"%.02f %s" % (dictValeur["total"], utils_preferences.Get_symbole_monnaie())))

                    if self.dict_options["afficher_deja_paye"]:
                        dataTableau.append(("", "Montant déjà réglé :", u"%.02f %s" % (dictValeur["ventilation"], utils_preferences.Get_symbole_monnaie())))
                
                    if self.mode == "facture" and self.dict_options["integrer_impayes"] == True and dictValeur["total_reports"] > 0.0:
                        dataTableau.append(("", "Report impayés :", "%.02f %s" % (dictValeur["total_reports"], utils_preferences.Get_symbole_monnaie()) ))
                        if self.dict_options["afficher_reste_regler"]:
                            dataTableau.append(("", "Reste à régler :", "%.02f %s" % (dictValeur["solde"] + dictValeur["total_reports"], utils_preferences.Get_symbole_monnaie()) ))
                        rowHeights=[10, 10, 10, None]
                    else :
                        if self.dict_options["afficher_reste_regler"]:
                            dataTableau.append(("", "Reste à régler :", "%.02f %s" % (dictValeur["solde"], utils_preferences.Get_symbole_monnaie()) ))
                        rowHeights=[18, 18, None]
                    
                style = [
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), 

                        # Lignes Période, avoir, impayés
                        ('FONT', (1, 0), (1, -2), "Helvetica", 8),
                        ('FONT', (2, 0), (2, -2), "Helvetica-Bold", 8),
                        
                        # Ligne Reste à régler
                        ('FONT', (1, -1), (1, -1), "Helvetica-Bold", int(self.dict_options["taille_texte_labels_totaux"])),
                        ('FONT', (2, -1), (2, -1), "Helvetica-Bold", int(self.dict_options["taille_texte_montants_totaux"])),
                        
                        ('GRID', (2, 0), (2, -1), 0.25, colors.black),
                        
                        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                        ('ALIGN', (2, 0), (2, -1), 'CENTRE'), 
                        ('BACKGROUND', (2, -1), (2, -1), couleurFond),
                        
                        ('SPAN', (0, 0), (0, -1)), 
                        ]
                
                if self.mode == "facture" and len(listeMessages) > 0:
                    #style.append( ('BACKGROUND', (0, 0), (0, 0), couleurFondActivite) )
                    style.append( ('FONT', (0, 0), (0, -1), "Helvetica", 8))
                    style.append( ('VALIGN', (0, 0), (0, -1), 'TOP'))
                    
                tableau = Table(dataTableau, largeursColonnes)
                tableau.setStyle(TableStyle(style))
                self.story.append(tableau)
                
                # ------------------------- PRELEVEMENTS --------------------
                if self.dict_options.get("afficher_avis_prelevements", False) and dictValeur.get("prelevement", False):
                    paraStyle = ParagraphStyle(name="intro",
                          fontName="Helvetica",
                          fontSize=8,
                          leading=11,
                          spaceBefore=2,
                          spaceafter=2,
                          alignment=1,
                          backColor=couleurFondActivite)
                    self.story.append(Spacer(0, 20))
                    self.story.append(Paragraph(u"<para align='center'><i>%s</i></para>" % dictValeur["prelevement"], paraStyle))
                
                # Texte conclusion
                if self.dict_options["texte_conclusion"] != "":
                    self.story.append(Spacer(0, 20))
                    paraStyle = ParagraphStyle(name="conclusion",
                                          fontName="Helvetica",
                                          fontSize=int(self.dict_options["taille_texte_conclusion"]),
                                          leading=14,
                                          spaceBefore=0,
                                          spaceafter=0,
                                          leftIndent=5,
                                          rightIndent=5,
                                          alignment=int(self.dict_options["alignement_texte_conclusion"]),
                                          backColor=self.dict_options["couleur_fond_conclusion"],
                                          borderColor=self.dict_options["couleur_bord_conclusion"],
                                          borderWidth=0.5,
                                          borderPadding=5)
            
                    texte = dictValeur["texte_conclusion"].replace("\\n", "<br/>")
                    if self.dict_options["style_texte_conclusion"] == "0": texte = "<para>%s</para>" % texte
                    if self.dict_options["style_texte_conclusion"] == "1": texte = "<para><i>%s</i></para>" % texte
                    if self.dict_options["style_texte_conclusion"] == "2": texte = "<para><b>%s</b></para>" % texte
                    if self.dict_options["style_texte_conclusion"] == "3": texte = "<para><i><b>%s</b></i></para>" % texte
                    self.story.append(Paragraph(texte, paraStyle))
                    
                # Image signature
                # if self.dict_options["image_signature"] != "" :
                #     cheminImage = self.dict_options["image_signature"]
                #     if os.path.isfile(cheminImage) :
                #         img = Image(cheminImage)
                #         largeur, hauteur = int(img.drawWidth * 1.0 * self.dict_options["taille_image_signature"] / 100.0), int(img.drawHeight * 1.0 * self.dict_options["taille_image_signature"] / 100.0)
                #         if largeur > self.taille_cadre[2] or hauteur > self.taille_cadre[3] :
                #             raise Exception(_(u"L'image de signature est trop grande. Veuillez diminuer sa taille avec le parametre Taille."))
                #         img.drawWidth, img.drawHeight = largeur, hauteur
                #         if self.dict_options["alignement_image_signature"] == "0" : img.hAlign = "LEFT"
                #         if self.dict_options["alignement_image_signature"] == "1" : img.hAlign = "CENTER"
                #         if self.dict_options["alignement_image_signature"] == "2" : img.hAlign = "RIGHT"
                #         self.story.append(Spacer(0,20))
                #         self.story.append(img)

                # Saut de page
                self.story.append(PageBreak())



if __name__ == u"__main__":
    Impression()
