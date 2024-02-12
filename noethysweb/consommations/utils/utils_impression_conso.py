# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, operator, datetime, os, uuid
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from django.db.models import Q
from django.conf import settings
from django.templatetags.static import static
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import ParagraphAndImage, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from reportlab.graphics.barcode import code39
from core.utils import utils_dates, utils_impression, utils_infos_individus, utils_dictionnaires
from core.models import Activite, Ouverture, Unite, UniteRemplissage, Consommation, MemoJournee, Note, Information, Individu, Inscription, Scolarite, Classe, Ecole, Evenement
from individus.utils import utils_pieces_manquantes
from cotisations.utils import utils_cotisations_manquantes


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        if kwds["dict_donnees"]["orientation"] == "paysage":
            kwds["taille_page"] = landscape(A4)
        if kwds["dict_donnees"]["orientation"] == "portrait":
            kwds["taille_page"] = portrait(A4)
        if kwds["dict_donnees"]["orientation"] == "automatique":
            if len(kwds["dict_donnees"]["dates"]) > 1:
                kwds["taille_page"] = landscape(A4)
            else:
                kwds["taille_page"] = portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self, mode_export_excel=False):
        # Calcule la largeur du contenu
        largeur_contenu = self.taille_page[0] - 75

        # Colonnes personnalisées
        colonnes_perso = json.loads(self.dict_donnees["colonnes_perso"])
        if colonnes_perso:
            # Chargement des informations individuelles
            infosIndividus = utils_infos_individus.Informations(date_reference=self.dict_donnees["dates"][0], qf=True, inscriptions=True, messages=False, infosMedicales=False,
                                                                cotisationsManquantes=False, piecesManquantes=False, questionnaires=True, scolarite=True)
            dictInfosIndividus = infosIndividus.GetDictValeurs(mode="individu", ID=None, formatChamp=False)
            dictInfosFamilles = infosIndividus.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

        # Préparation des unités
        dictChoixUnites = {}
        for idactivite, liste_valeurs in json.loads(self.dict_donnees["unites"]).items():
            for valeurs in liste_valeurs:
                dictChoixUnites.setdefault(int(idactivite), [])
                categorie, idunite, affichage = valeurs.split("_")
                dictChoixUnites[int(idactivite)].append((categorie, int(idunite), affichage))

        # Récupération de la liste des unités ouvertes ce jour
        liste_groupes = [int(idgroupe) for idgroupe in self.dict_donnees["groupes"].split(";")]
        liste_activites = Activite.objects.filter(groupe__in=liste_groupes).distinct()

        ouvertures = Ouverture.objects.select_related('groupe').filter(groupe_id__in=liste_groupes, date__in=self.dict_donnees["dates"])
        dictOuvertures = {}
        for ouverture in ouvertures:
            utils_dictionnaires.DictionnaireImbrique(dictionnaire=dictOuvertures, cles=[ouverture.activite_id, ouverture.groupe, ouverture.date], valeur=[])
            dictOuvertures[ouverture.activite_id][ouverture.groupe][ouverture.date].append(ouverture.unite_id)

        # Récupération des infos sur les unités
        dictUnites = {unite.pk: unite for unite in Unite.objects.all()}

        # Importation des unités de remplissage
        dictUnitesRemplissage = {unite.pk: unite for unite in UniteRemplissage.objects.prefetch_related('unites').filter(activite__in=liste_activites)}

        # Importation de la scolarité
        dict_scolarites = {}
        if self.dict_donnees["regroupement_scolarite"] != "non":
            # Importation de la scolarité
            scolarites = Scolarite.objects.filter(date_debut__lte=max(self.dict_donnees["dates"]), date_fin__gte=min(self.dict_donnees["dates"]))
            for scolarite in scolarites:
                dict_scolarites.setdefault(scolarite.individu_id, [])
                dict_scolarites[scolarite.individu_id].append(scolarite)

            # Importation des écoles et classes
            dictEcoles = {}
            if self.dict_donnees["regroupement_scolarite"] != "aucun":
                liste_ecoles = [int(idecole) for idecole in self.dict_donnees["ecoles"].split(";")] if self.dict_donnees["ecoles"] else []
                self.liste_ecoles = Ecole.objects.filter(pk__in=liste_ecoles).order_by("nom")

                if self.dict_donnees["regroupement_scolarite"] == "classes":
                    liste_classes = [int(idclasse) for idclasse in self.dict_donnees["classes"].split(";")] if self.dict_donnees["classes"] else []
                    classes = Classe.objects.filter(pk__in=liste_classes).order_by("date_debut")
                    self.dict_classes = {}
                    for classe in classes:
                        self.dict_classes.setdefault(classe.ecole, [])
                        self.dict_classes[classe.ecole].append(classe)

        # Importation des conso
        if self.dict_donnees["afficher_tous_etats"]:
            liste_etats = ("reservation", "present", "refus", "attente", "absenti", "absentj")
        else:
            liste_etats = ("reservation", "present")
        conditions = Q(groupe_id__in=liste_groupes) & Q(date__in=self.dict_donnees["dates"]) & Q(etat__in=liste_etats) & Q(inscription__statut="ok")

        liste_evenements = []
        dict_evenements = {}
        if self.dict_donnees["regroupement_evenements"]:
            liste_evenements = [int(idevenement) for idevenement in self.dict_donnees["evenements"].split(";")] if self.dict_donnees["evenements"] else []
            conditions &= Q(evenement_id__in=liste_evenements)
            dict_evenements = {evenement.pk: evenement for evenement in Evenement.objects.filter(pk__in=liste_evenements)}

        def Get_scolarite(idindividu=None, date=None, donnee=None):
            if idindividu in dict_scolarites:
                for scolarite in dict_scolarites[idindividu]:
                    if scolarite.date_debut <= date <= scolarite.date_fin:
                        if donnee == "classe": return scolarite.classe_id
                        if donnee == "ecole": return scolarite.ecole_id
                        return scolarite
            return None

        liste_conso = Consommation.objects.select_related('individu', 'inscription', 'inscription__famille', 'inscription__activite', 'inscription__individu', 'individu__type_sieste', 'evenement') \
            .prefetch_related("inscription__individu__regimes_alimentaires") \
            .filter(conditions).order_by("date", "heure_debut")

        # Préparation des filtres de scolarité
        liste_ecoles = [int(idecole) for idecole in self.dict_donnees["ecoles"].split(";")] if self.dict_donnees["ecoles"] else []
        liste_classes = [int(idclasse) for idclasse in self.dict_donnees["classes"].split(";")] if self.dict_donnees["classes"] else []

        dictConso = {}
        liste_inscriptions = []
        for conso in liste_conso:
            valide = True

            # Groupe
            IDgroupe = conso.groupe_id
            if not self.dict_donnees["regroupement_groupe"]:
                IDgroupe = None

            # Filtre de scolarité
            scolarite = None
            if self.dict_donnees["regroupement_scolarite"] == "ecoles":
                scolarite = Get_scolarite(conso.individu_id, conso.date, "ecole")
                if scolarite not in liste_ecoles:
                    valide = False
            if self.dict_donnees["regroupement_scolarite"] == "classes":
                scolarite = Get_scolarite(conso.individu_id, conso.date, "classe")
                if scolarite not in liste_classes:
                    valide = False

            if self.dict_donnees["afficher_scolarite_inconnue"]:
                valide = True

            # Mémorisation de l'évènement
            IDevenement = conso.evenement_id
            if not self.dict_donnees["regroupement_evenements"]:
                IDevenement = None

            # Mémorisation de l'étiquette
            # if self.GetPage("etiquettes").checkbox_etiquettes.GetValue() == False :
            #     listeEtiquettes = [None,]
            # else :
            #     listeEtiquettes = etiquettes

            if valide:
                for IDetiquette in [None,]:#listeEtiquettes :
                    utils_dictionnaires.DictionnaireImbrique(dictionnaire=dictConso,
                                                             cles=[conso.activite_id, IDgroupe, scolarite, IDevenement, IDetiquette, conso.inscription],
                                                             valeur={"IDcivilite": conso.individu.civilite, "nom": conso.individu.nom, "prenom": conso.individu.prenom, "date_naiss": conso.individu.date_naiss, "age": conso.individu.Get_age(), "listeConso": {}})

                    utils_dictionnaires.DictionnaireImbrique(dictionnaire=dictConso[conso.activite_id][IDgroupe][scolarite][IDevenement][IDetiquette][conso.inscription]["listeConso"],
                                                             cles=[conso.date, conso.unite_id],
                                                             valeur=[])

                    detail_conso = {"heure_debut": conso.heure_debut, "heure_fin": conso.heure_fin, "etat": conso.etat, "quantite": conso.quantite, "IDfamille": conso.inscription.famille_id, "evenement": conso.evenement}  #, "etiquettes": etiquettes}
                    dictConso[conso.activite_id][IDgroupe][scolarite][IDevenement][IDetiquette][conso.inscription]["listeConso"][conso.date][conso.unite_id].append(detail_conso)
                    if conso.inscription.pk not in liste_inscriptions:
                        liste_inscriptions.append(conso.inscription.pk)

        # Masquer les présents
        if self.dict_donnees["masquer_presents"]:
            dictConso = {}

        # Intégration de tous les inscrits
        if self.dict_donnees["afficher_inscrits"]:

            conditions = Q(activite__in=liste_activites) & Q(statut="ok") & (Q(date_fin__isnull=True) | Q(date_fin__gte=max(self.dict_donnees["dates"])))
            if self.dict_donnees["masquer_presents"]:
                conditions &= ~Q(idinscription__in=liste_inscriptions)

            inscriptions = Inscription.objects.select_related('individu', 'activite', 'famille', 'individu__type_sieste').prefetch_related("individu__regimes_alimentaires").filter(conditions)

            for inscription in inscriptions:
                valide = True

                # Groupe
                IDgroupe = inscription.groupe_id
                if not self.dict_donnees["regroupement_groupe"]:
                    IDgroupe = None

                # Filtre de scolarité
                scolarite = None
                if self.dict_donnees["regroupement_scolarite"] == "ecoles":
                    scolarite = Get_scolarite(inscription.individu_id, min(self.dict_donnees["dates"]), "ecole")
                    if scolarite not in liste_ecoles:
                        valide = False
                if self.dict_donnees["regroupement_scolarite"] == "classes":
                    scolarite = Get_scolarite(inscription.individu_id, min(self.dict_donnees["dates"]), "classe")
                    if scolarite not in liste_classes:
                        valide = False

                if self.dict_donnees["afficher_scolarite_inconnue"]:
                    valide = True

                # Provisoire :
                IDetiquette = None
                IDevenement = None

                if valide:
                    utils_dictionnaires.DictionnaireImbrique(dictionnaire=dictConso,
                                                             cles=[inscription.activite_id, IDgroupe, scolarite, IDevenement, IDetiquette, inscription],
                                                             valeur={"IDcivilite": inscription.individu.civilite, "nom": inscription.individu.nom, "prenom": inscription.individu.prenom, "date_naiss": inscription.individu.date_naiss, "age": inscription.individu.Get_age(), "listeConso": {}})

        # Récupération des mémo-journées
        dictMemos = {}
        for memo in MemoJournee.objects.filter(date__in=self.dict_donnees["dates"]):
            dictMemos.setdefault(memo.inscription_id, {})
            dictMemos[memo.inscription_id][memo.date] = memo.texte

        # Récupération des photos individuelles
        if self.dict_donnees["afficher_photos"] == "petite": tailleImageFinal = 16
        if self.dict_donnees["afficher_photos"] == "moyenne": tailleImageFinal = 32
        if self.dict_donnees["afficher_photos"] == "grande": tailleImageFinal = 64

        # Récupération des notes
        notes = Note.objects.filter(afficher_liste=True)

        dictMessagesFamilles = {}
        dictMessagesIndividus = {}
        for note in notes:
            if note.individu:
                dictMessagesIndividus.setdefault(note.individu_id, [])
                dictMessagesIndividus[note.individu_id].append(note)
            if note.famille:
                dictMessagesFamilles.setdefault(note.famille_id, [])
                dictMessagesFamilles[note.famille_id].append(note)

        # Récupération de la liste des cotisations manquantes
        if self.dict_donnees["afficher_cotisations_manquantes"]:
            dictCotisations = utils_cotisations_manquantes.Get_liste_cotisations_manquantes(date_reference=min(self.dict_donnees["dates"]),
                                                                         activites=liste_activites, presents=(min(self.dict_donnees["dates"]), max(self.dict_donnees["dates"])),
                                                                         only_concernes=True)

        # Récupération de la liste des pièces manquantes
        if self.dict_donnees["afficher_pieces_manquantes"]:
            dictPieces = utils_pieces_manquantes.Get_liste_pieces_manquantes(date_reference=min(self.dict_donnees["dates"]),
                                                                  activites=liste_activites, presents=(min(self.dict_donnees["dates"]), max(self.dict_donnees["dates"])),
                                                                  only_concernes=True)

        # Récupération des informations personnelles
        dictInfosPerso = {}
        conditions = Q(diffusion_listing_conso=True) & (Q(date_debut__lte=min(self.dict_donnees["dates"])) | Q(date_debut__isnull=True)) & (Q(date_fin__gte=max(self.dict_donnees["dates"])) | Q(date_fin__isnull=True))
        infos = Information.objects.select_related("individu", "categorie").filter(conditions)
        for info in infos:
            dictInfosPerso.setdefault(info.individu_id, [])
            dictInfosPerso[info.individu_id].append(info)


        # --------------------------------------- Création du PDF ----------------------------------------------

        # Font normale
        styleNormal = ParagraphStyle(name="normal", fontName="Helvetica", alignment=1, fontSize=7, leading=8)
        styleEntetes = ParagraphStyle(name="entetes", fontName="Helvetica", alignment=1, fontSize=6, leading=7)
        styleDifferences = ParagraphStyle(name="differences", fontName="Helvetica", alignment=1, fontSize=4, spaceAfter=0, leading=5, textColor=colors.grey)

        # Nom du profil
        profil = self.dict_donnees.get("profil", None)
        nom_profil = profil.nom if profil else None

        # Création du header du document
        def CreationTitreDocument():
            self.titre = "Consommations"
            if len(self.dict_donnees["dates"]) == 1:
                self.titre = "Consommations du %s" % utils_dates.DateComplete(min(self.dict_donnees["dates"]))
            self.Insert_header(detail=nom_profil)

        # Création du titre des tableaux
        def CreationTitreTableau(nomActivite="", nomGroupe="", nomEcole="", nomClasse="", couleurTexte=colors.black, tailleGroupe=14):
            dataTableau = []
            largeursColonnes = ((largeur_contenu * 1.0 / 3, largeur_contenu * 2.0 / 3))

            styleActivite = ParagraphStyle(name="activite", fontName="Helvetica", fontSize=self.dict_donnees["activite_taille_nom"], leading=self.dict_donnees["activite_taille_nom"], spaceAfter=0, textColor=couleurTexte)
            styleGroupe = ParagraphStyle(name="groupe", fontName="Helvetica-Bold", fontSize=tailleGroupe, leading=tailleGroupe+2, spaceBefore=0, spaceAfter=2, textColor=couleurTexte)
            styleEcole = ParagraphStyle(name="ecole", fontName="Helvetica", alignment=2, fontSize=5, leading=3, spaceAfter=0, textColor=couleurTexte)
            styleClasse = ParagraphStyle(name="classe", fontName="Helvetica-Bold", alignment=2, fontSize=14, leading=16, spaceBefore=0, spaceAfter=2, textColor=couleurTexte)

            ligne = [(Paragraph(nomActivite, styleActivite), Paragraph(nomGroupe, styleGroupe)), None]

            if self.dict_donnees["regroupement_scolarite"] == "ecoles":
                if not nomEcole: nomEcole = "Ecole inconnue"
                ligne[1] = (Paragraph(nomEcole, styleClasse))

            if self.dict_donnees["regroupement_scolarite"] == "classes":
                if not nomEcole: nomEcole = "Ecole inconnue"
                if not nomClasse: nomClasse = "Classe inconnue"
                ligne[1] = (Paragraph(nomEcole, styleEcole), Paragraph(nomClasse, styleClasse))

            dataTableau.append(ligne)

            if len(self.dict_donnees["dates"]) == 1:
                style = TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                        ('BACKGROUND', (0, 0), (-1, 0), self.dict_donnees["couleur_fond_titre"]),
                        ('LINEABOVE', (0, 0), (-1, 0), 0.25, colors.black),
                        ('LINEBEFORE', (0, 0), (0, 0), 0.25, colors.black),
                        ('LINEAFTER', (-1, 0), (-1, 0), 0.25, colors.black),
                        ])
            else:
                style = TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                        ('BACKGROUND', (0, 0), (-1, 0), self.dict_donnees["couleur_fond_titre"]),
                        ('BOX', (0, 0), (-1, 0), 0.25, colors.black),
                        ])

            tableau = Table(dataTableau, largeursColonnes)
            tableau.setStyle(style)
            self.story.append(tableau)

        def CreationSautPage():
            try :
                element = str(self.story[-3])
                if element != "PageBreak()":
                    self.story.append(PageBreak())
                    CreationTitreDocument()
            except :
                pass

        # Prépare liste pour Export Excel
        listeExport = []

        # Insère un header
        CreationTitreDocument()

        # Activités
        for indexActivite, activite in enumerate(liste_activites, 1):
            # Groupes
            if activite.pk in dictOuvertures:

                # tri des groupes par ordre
                listeGroupesTemp = sorted(list(dictOuvertures[activite.pk].keys()), key=lambda x: x.ordre)
                if not self.dict_donnees["regroupement_groupe"]:
                    listeGroupesTemp = [None]

                for indexGroupe, groupe in enumerate(listeGroupesTemp, 1):
                    IDgroupe = groupe.pk if groupe else None

                    if self.dict_donnees["regroupement_groupe"]:
                        dictDatesUnites = dictOuvertures[activite.pk][groupe]
                    else:
                        dictDatesUnites = {}
                        for groupeTemp, dictUnitesTemp in dictOuvertures[activite.pk].items():
                            dictDatesUnites.update(dictUnitesTemp)

                    # Classes
                    listeScolarite = []
                    if activite.pk in dictConso and IDgroupe in dictConso[activite.pk]:
                        listeScolarite = list(dictConso[activite.pk][IDgroupe].keys())

                    # tri des classes
                    listeInfosScolarite = [] if self.dict_donnees["regroupement_scolarite"] == "aucun" else self.TriClasses(listeScolarite)

                    # Si aucun enfant scolarisé
                    if not listeInfosScolarite or self.dict_donnees["regroupement_scolarite"] == "aucun":
                        listeInfosScolarite = [None,]

                    for indexClasse, dictClasse in enumerate(listeInfosScolarite, 1):

                        # Récupération des infos sur école et classe
                        if dictClasse:
                            IDecole = dictClasse["IDecole"]
                            nomEcole = dictClasse["nomEcole"]
                            IDclasse = dictClasse["IDclasse"]
                            nomClasse = dictClasse["nomClasse"]
                        else:
                            IDecole = None
                            nomEcole = None
                            IDclasse = None
                            nomClasse = None

                        # Mémorisation du regroupement de scolarité
                        if self.dict_donnees["regroupement_scolarite"] == "ecoles":
                            scolarite = IDecole
                        elif self.dict_donnees["regroupement_scolarite"] == "classes":
                            scolarite = IDclasse
                        else:
                            scolarite = None

                        # Recherche des évènements
                        listeEvenements = []
                        if activite.pk in dictConso and IDgroupe in dictConso[activite.pk] and scolarite in dictConso[activite.pk][IDgroupe]:
                            listeEvenements = list(dictConso[activite.pk][IDgroupe][scolarite].keys())

                        # Si regroupement par évènement
                        if not self.dict_donnees["regroupement_evenements"]:
                            listeEvenements = [None,]

                        for IDevenement in listeEvenements:
                            # Recherche nom évènement
                            nomEvenement = None
                            if IDevenement in dict_evenements:
                                nomEvenement = dict_evenements[IDevenement].nom

                            # Parcours les étiquettes
                            listeIDetiquette = []
                            # if IDactivite in dictConso :
                            #     if IDgroupe in dictConso[IDactivite] :
                            #         if scolarite in dictConso[IDactivite][IDgroupe] :
                            #             if IDevenement in dictConso[IDactivite][IDgroupe][scolarite]:
                            #                 for IDetiquette, temp in dictConso[IDactivite][IDgroupe][scolarite][IDevenement].items() :
                            #                     listeIDetiquette.append(IDetiquette)
                            if not listeIDetiquette:
                                listeIDetiquette = [None,]

                            for IDetiquette in listeIDetiquette:

                                # Initialisation du tableau
                                dataTableau = []
                                largeursColonnes = []
                                labelsColonnes = []
                                recapitulatif = {"informations": [], "regimes": []}

                                # Recherche des entêtes de colonnes :
                                if self.dict_donnees["afficher_photos"] != "non":
                                    labelsColonnes.append(Paragraph("Photo", styleEntetes))
                                    largeursColonnes.append(tailleImageFinal + 6)

                                labelsColonnes.append(Paragraph("Nom - prénom", styleEntetes))
                                if self.dict_donnees["largeur_colonne_nom"] == "automatique":
                                    largeurColonneNom = 120
                                else :
                                    largeurColonneNom = int(self.dict_donnees["largeur_colonne_nom"])
                                largeursColonnes.append(largeurColonneNom)

                                if self.dict_donnees["afficher_age"]:
                                    labelsColonnes.append(Paragraph("Age", styleEntetes))
                                    if self.dict_donnees["largeur_colonne_age"] == "automatique":
                                        largeurColonneAge = 20
                                    else:
                                        largeurColonneAge = int(self.dict_donnees["largeur_colonne_age"])
                                    largeursColonnes.append(largeurColonneAge)

                                # Recherche des entetes de colonnes UNITES
                                if self.dict_donnees["largeur_colonne_unite"] == "automatique":
                                    largeurColonneUnite = 30
                                else :
                                    largeurColonneUnite = int(self.dict_donnees["largeur_colonne_unite"])

                                listePositionsDates = []
                                indexCol = len(labelsColonnes)
                                for date in self.dict_donnees["dates"]:
                                    if date in dictDatesUnites:
                                        listeUnites = dictDatesUnites[date]
                                        positionG = indexCol
                                        for typeTemp, IDunite, affichage in dictChoixUnites[activite.pk]:
                                            if (affichage == "ouvert" and IDunite in listeUnites) or affichage == "afficher":
                                                if typeTemp == "consommation":
                                                    abregeUnite = dictUnites[IDunite].abrege
                                                else:
                                                    if IDunite in dictUnitesRemplissage:
                                                        abregeUnite = dictUnitesRemplissage[IDunite].abrege
                                                    else:
                                                        abregeUnite = "?"
                                                labelsColonnes.append(Paragraph(abregeUnite, styleEntetes))
                                                largeur = largeurColonneUnite

                                                # Agrandit si unité de type multihoraires
                                                if typeTemp == "consommation" and dictUnites[IDunite].type == "Multihoraires" and self.dict_donnees["largeur_colonne_unite"] == "automatique":
                                                    largeur = 55

                                                # Agrandit si évènements à afficher
                                                if self.dict_donnees["afficher_evenements"] and self.dict_donnees["largeur_colonne_unite"] == "automatique":
                                                    largeur += 30

                                                # Agrandit si étiquettes à afficher
                                                # if self.dict_donnees["afficher_etiquettes"] and self.dict_donnees["largeur_colonne_unite"] == "automatique":
                                                #     largeur += 10

                                                largeursColonnes.append(largeur)
                                                indexCol += 1
                                        positionD = indexCol-1
                                        listePositionsDates.append((date, positionG, positionD))

                                # Colonnes personnalisées
                                for dictColonnePerso in colonnes_perso:
                                    labelsColonnes.append(Paragraph(dictColonnePerso["nom"], styleEntetes))
                                    if dictColonnePerso["largeur"] == "automatique":
                                        largeurColonnePerso = int(self.dict_donnees["largeur_colonne_perso"])
                                        if dictColonnePerso["code"].startswith("codebarres"):
                                            largeurColonnePerso = 85
                                    else:
                                        largeurColonnePerso = int(dictColonnePerso["largeur"])
                                    largeursColonnes.append(largeurColonnePerso)

                                # Colonne Informations
                                if self.dict_donnees["afficher_informations"]:
                                    labelsColonnes.append(Paragraph("Informations", styleEntetes))
                                    if self.dict_donnees["largeur_colonne_informations"] == "automatique":
                                        largeurColonneInformations = largeur_contenu - sum(largeursColonnes)
                                    else :
                                        largeurColonneInformations = int(self.dict_donnees["largeur_colonne_informations"])
                                    largeursColonnes.append(largeurColonneInformations)

                                # ------ Création de l'entete de groupe ------
                                CreationTitreTableau(activite.nom, groupe.nom if groupe else "&nbsp;", nomEcole, nomClasse)

                                if IDevenement:
                                    nomEvenement = dict_evenements[IDevenement].nom
                                    CreationTitreTableau(nomGroupe=nomEvenement, couleurTexte=colors.black, tailleGroupe=10)
                                else:
                                    nomEvenement = None

                                if IDetiquette:
                                    # nomEtiquette = dictEtiquettes[IDetiquette]["label"] # todo : provisoire
                                    couleurEtiquette = colors.grey
                                    CreationTitreTableau(nomGroupe=nomEtiquette, couleurTexte=couleurEtiquette, tailleGroupe=10)
                                else:
                                    nomEtiquette = None

                                listeLignesExport = []

                                # Création de l'entete des DATES
                                if len(self.dict_donnees["dates"]) > 1:
                                    ligneTempExport = []
                                    styleDate = ParagraphStyle(name="date", fontName="Helvetica-Bold", fontSize=8, spaceAfter=0, leading=9)
                                    ligne = []
                                    for index in range(0, len(labelsColonnes)-1):
                                        ligne.append("")
                                        ligneTempExport.append("")

                                    index = 0
                                    for date, positionG, positionD in listePositionsDates :
                                        listeJours = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")
                                        listeJoursAbrege = ("Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim.")
                                        listeMoisAbrege = ("janv.", "fév.", "mars", "avril", "mai", "juin", "juil.", "août", "sept.", "oct", "nov.", "déc.")
                                        try:
                                            if (positionD-positionG) < 1:
                                                jourStr = listeJoursAbrege[date.weekday()]
                                                ligne[positionG] = "%s\n%d\n%s\n%d" % (jourStr, date.day, listeMoisAbrege[date.month-1], date.year)
                                            else:
                                                jourStr = listeJours[date.weekday()]
                                                dateStr = "<para align='center'>%s %d %s %d</para>" % (jourStr, date.day, listeMoisAbrege[date.month-1], date.year)
                                                ligne[positionG] = Paragraph(dateStr, styleDate)
                                            ligneTempExport[positionG] = utils_dates.ConvertDatetoFR(date)
                                        except:
                                            pass
                                        index += 1
                                    dataTableau.append(ligne)
                                    listeLignesExport.append(ligneTempExport)

                                # Création des entêtes
                                ligne = []
                                for label in labelsColonnes:
                                    ligne.append(label)
                                dataTableau.append(ligne)
                                listeLignesExport.append(ligne)

                                # --------- Création des lignes -----------

                                # Création d'une liste temporaire pour le tri
                                listeInscriptions = []
                                try:
                                    for inscription, dictInscription in dictConso[activite.pk][IDgroupe][scolarite][IDevenement][IDetiquette].items():
                                        listeInscriptions.append((
                                            inscription,
                                            dictInscription["nom"],
                                            dictInscription["prenom"],
                                            dictInscription["age"],
                                            "%s %s" % (dictInscription["nom"], dictInscription["prenom"] or ""),
                                            "%s %s" % (dictInscription["prenom"] or "", dictInscription["nom"]),
                                        ))
                                except:
                                    pass

                                if self.dict_donnees["tri"] == "nom": paramTri = 4
                                if self.dict_donnees["tri"] == "prenom": paramTri = 5
                                if self.dict_donnees["tri"] == "age": paramTri = 3
                                listeInscriptions = sorted(listeInscriptions, key=operator.itemgetter(paramTri), reverse=self.dict_donnees["ordre"] != "croissant")

                                # Recherche des différences entre les inscriptions
                                dict_differences = {}
                                for inscription, nom, prenom, age, nom_complet, prenom_complet in listeInscriptions:
                                    dict_differences.setdefault(inscription.individu, {})
                                    dict_differences[inscription.individu].setdefault(inscription.activite, {"famille": []})
                                    if inscription.famille not in dict_differences[inscription.individu][inscription.activite]["famille"]:
                                        dict_differences[inscription.individu][inscription.activite]["famille"].append(inscription.famille)
                                for inscription, nom, prenom, age, nom_complet, prenom_complet in listeInscriptions:
                                    inscription.infos_differentes = []
                                    for info in ("famille",):
                                        if len(dict_differences[inscription.individu][inscription.activite][info]) > 1:
                                            inscription.infos_differentes.append(getattr(inscription, info).nom)
                                    inscription.infos_differentes = " | ".join(inscription.infos_differentes)

                                # Récupération des lignes inscriptions
                                dictTotauxColonnes = {}
                                indexLigne = 0
                                for inscription, nom, prenom, age, nom_complet, prenom_complet in listeInscriptions:

                                    dictInscription = dictConso[activite.pk][IDgroupe][scolarite][IDevenement][IDetiquette][inscription]
                                    ligne = []
                                    indexColonne = 0
                                    ligneVide = True

                                    # Photo
                                    if self.dict_donnees["afficher_photos"] != "non":
                                        nom_fichier = inscription.individu.Get_photo(forTemplate=False)
                                        if "media/" in nom_fichier:
                                            nom_fichier = settings.MEDIA_ROOT + nom_fichier.replace("media/", "")
                                        img = Image(nom_fichier, width=tailleImageFinal, height=tailleImageFinal)
                                        ligne.append(img)
                                        indexColonne += 1

                                    # Nom
                                    nom_complet = [Paragraph(u"%s %s" % (nom, prenom), styleNormal),]
                                    infos_differentes = getattr(inscription, "infos_differentes")
                                    if infos_differentes:
                                        nom_complet.append(Paragraph(infos_differentes, styleDifferences))
                                    ligne.append(nom_complet)
                                    indexColonne += 1

                                    # Age
                                    if self.dict_donnees["afficher_age"]:
                                        if age:
                                            ligne.append(Paragraph(str(age), styleNormal))
                                        else:
                                            ligne.append("")
                                        indexColonne += 1

                                    # Unites
                                    for date in self.dict_donnees["dates"]:
                                        if date in dictDatesUnites:
                                            listeUnites = dictDatesUnites[date]

                                            for typeTemp, IDunite, affichage in dictChoixUnites[activite.pk]:
                                                if (affichage == "ouvert" and IDunite in listeUnites) or affichage == "afficher":
                                                    listeLabels = []
                                                    quantite = None

                                                    styleConso = ParagraphStyle(name="label_conso", fontName="Helvetica", alignment=1, fontSize=6, leading=6, spaceBefore=0, spaceAfter=0, textColor=colors.black)
                                                    styleEvenement = ParagraphStyle(name="label_evenement", fontName="Helvetica", alignment=1, fontSize=5, leading=5, spaceBefore=2, spaceAfter=0, textColor=colors.black)
                                                    styleEtiquette = ParagraphStyle(name="label_etiquette", fontName="Helvetica", alignment=1, fontSize=5, leading=5, spaceBefore=2, spaceAfter=0, textColor=colors.grey)

                                                    if typeTemp == "consommation":
                                                        # Unité de Conso
                                                        if date in dictInscription["listeConso"]:
                                                            if IDunite in dictInscription["listeConso"][date]:
                                                                typeUnite = dictUnites[IDunite].type

                                                                label = ""
                                                                for dictConsoTemp in dictInscription["listeConso"][date][IDunite]:
                                                                    etat = dictConsoTemp["etat"]
                                                                    heure_debut = dictConsoTemp["heure_debut"]
                                                                    heure_fin = dictConsoTemp["heure_fin"]
                                                                    quantite = dictConsoTemp["quantite"]
                                                                    # etiquettes = dictConsoTemp["etiquettes"]

                                                                    if typeUnite == "Unitaire":
                                                                         label = "X"
                                                                    if typeUnite in ("Horaire", "Multihoraires"):
                                                                        if heure_debut == None: heure_debut = "?"
                                                                        if heure_fin == None: heure_fin = "?"
                                                                        if type(heure_debut) == datetime.time: heure_debut = heure_debut.strftime('%H:%M')
                                                                        if type(heure_fin) == datetime.time: heure_fin = heure_fin.strftime('%H:%M')
                                                                        heure_debut = heure_debut.replace(":", "h")
                                                                        heure_fin = heure_fin.replace(":", "h")
                                                                    if typeUnite == "Horaire":
                                                                        label = "%s\n%s" % (heure_debut, heure_fin)
                                                                    if typeUnite == "Multihoraires":
                                                                        label = "%s > %s" % (heure_debut, heure_fin)
                                                                    if typeUnite == "Evenement":
                                                                         label = "X"
                                                                    if typeUnite == "Quantite":
                                                                         label = str(quantite)

                                                                    if self.dict_donnees["masquer_horaires"]:
                                                                        label = "X"
                                                                    if self.dict_donnees["afficher_tous_etats"]:
                                                                        label += "<br/>%s" % self.Formate_etat(etat)
                                                                    if self.dict_donnees["masquer_consommations"]:
                                                                        label = ""

                                                                    listeLabels.append(Paragraph(label, styleConso))

                                                                    # Affichage de l'évènement
                                                                    if self.dict_donnees["afficher_evenements"] and dictConsoTemp["evenement"] != None:
                                                                        texteEvenement = dictConsoTemp["evenement"].nom
                                                                        listeLabels.append(Paragraph(texteEvenement, styleEvenement))

                                                                    # Affichage de l'étiquette
                                                                    # if self.dict_donnees["afficher_etiquettes"] and len(etiquettes) > 0 :
                                                                    #     texteEtiquette = []
                                                                    #     for IDetiquetteTemp in etiquettes:
                                                                    #         texteEtiquette.append(self.dict_donnees[IDetiquetteTemp]["label"])
                                                                    #     etiquette = "\n\n" + ", ".join(texteEtiquette)
                                                                    #     listeLabels.append(Paragraph(etiquette, styleEtiquette))

                                                    else:
                                                        # Unité de Remplissage
                                                        unitesLiees, etiquettesUnitesRemplissage = [], []
                                                        if IDunite in dictUnitesRemplissage:
                                                            unitesLiees = dictUnitesRemplissage[IDunite].unites.all()
                                                            # etiquettesUnitesRemplissage = dictUnitesRemplissage[IDunite]["etiquettes"]

                                                        for unite in unitesLiees:
                                                            if date in dictInscription["listeConso"]:
                                                                if unite.pk in dictInscription["listeConso"][date]:

                                                                    for dictConsoTemp in dictInscription["listeConso"][date][unite.pk]:
                                                                        etat = dictConsoTemp["etat"]
                                                                        quantite = dictConsoTemp["quantite"]
                                                                        # etiquettes = dictConsoTemp["etiquettes"]
                                                                        heure_debut = dictConsoTemp["heure_debut"]
                                                                        heure_fin = dictConsoTemp["heure_fin"]

                                                                        valide = True

                                                                        # Validation de la condition étiquettes
                                                                        # if len(etiquettesUnitesRemplissage) > 0 :
                                                                        #     valide = False
                                                                        #     for IDetiquetteTemp in etiquettesUnitesRemplissage :
                                                                        #         if IDetiquetteTemp in etiquettes :
                                                                        #             valide = True

                                                                        # Validation de la condition tranche horaire
                                                                        try:
                                                                            heure_min = dictUnitesRemplissage[IDunite].heure_min
                                                                            heure_max = dictUnitesRemplissage[IDunite].heure_max
                                                                            if heure_min and heure_max and heure_debut and heure_fin:
                                                                                # heure_min_TM = UTILS_Dates.HeureStrEnTime(heure_min)
                                                                                # heure_max_TM = UTILS_Dates.HeureStrEnTime(heure_max)
                                                                                # heure_debut_TM = UTILS_Dates.HeureStrEnTime(heure_debut)
                                                                                # heure_fin_TM = UTILS_Dates.HeureStrEnTime(heure_fin)
                                                                                # if heure_debut_TM <= heure_max_TM and heure_fin_TM >= heure_min_TM:
                                                                                if heure_debut <= heure_max and heure_fin >= heure_min:
                                                                                    valide = True
                                                                                else:
                                                                                    valide = False
                                                                        except:
                                                                            pass

                                                                        if valide:

                                                                            if quantite:
                                                                                label = str(quantite)
                                                                            else:
                                                                                label = "X"

                                                                            if self.dict_donnees["masquer_horaires"]:
                                                                                label = "X"
                                                                            if self.dict_donnees["afficher_tous_etats"]:
                                                                                label += "<br/>%s" % self.Formate_etat(etat)
                                                                            if self.dict_donnees["masquer_consommations"]:
                                                                                label = ""

                                                                            listeLabels.append(Paragraph(label, styleConso))

                                                                            # Affichage de l'évènement
                                                                            if self.dict_donnees["afficher_evenements"] and dictConsoTemp["evenement"]:
                                                                                texteEvenement = dictConsoTemp["evenement"].nom
                                                                                listeLabels.append(Paragraph(texteEvenement, styleEvenement))

                                                                            # Affichage de l'étiquette
                                                                            # if self.dict_donnees["afficher_etiquettes"] == True and len(etiquettes) > 0 :
                                                                            #     texteEtiquette = []
                                                                            #     for IDetiquetteTemp in etiquettes :
                                                                            #         texteEtiquette.append(dictEtiquettes[IDetiquetteTemp]["label"])
                                                                            #         etiquette = "\n\n" + ", ".join(texteEtiquette)
                                                                            #     listeLabels.append(Paragraph(etiquette, styleEtiquette))


                                                    if not quantite:
                                                        quantite = 1

                                                    if listeLabels:
                                                        ligneVide = False
                                                        if indexColonne in dictTotauxColonnes:
                                                            dictTotauxColonnes[indexColonne] += quantite
                                                        else:
                                                            dictTotauxColonnes[indexColonne] = quantite
                                                    ligne.append(listeLabels)
                                                    indexColonne += 1

                                    # Colonnes personnalisées
                                    for dictColonnePerso in colonnes_perso:
                                        type_donnee = "unicode"
                                        if not dictColonnePerso["code"]:
                                            donnee = ""
                                        else:
                                            try:
                                                if dictColonnePerso["code"] == "aucun": donnee = ""
                                                if dictColonnePerso["code"] == "ville_residence": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_VILLE"] or ""
                                                if dictColonnePerso["code"] == "secteur": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_SECTEUR"] or ""
                                                if dictColonnePerso["code"] == "genre": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_SEXE"] or ""
                                                if dictColonnePerso["code"] == "ville_naissance": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_VILLE_NAISS"] or ""
                                                if dictColonnePerso["code"] == "nom_ecole": donnee = dictInfosIndividus[inscription.individu_id]["SCOLARITE_NOM_ECOLE"] or ""
                                                if dictColonnePerso["code"] == "nom_classe": donnee = dictInfosIndividus[inscription.individu_id]["SCOLARITE_NOM_CLASSE"] or ""
                                                if dictColonnePerso["code"] == "nom_niveau_scolaire": donnee = dictInfosIndividus[inscription.individu_id]["SCOLARITE_NOM_NIVEAU"] or ""
                                                if dictColonnePerso["code"] == "famille": donnee = dictInfosFamilles[inscription.famille_id]["FAMILLE_NOM"] or ""
                                                if dictColonnePerso["code"] == "regime": donnee = dictInfosFamilles[inscription.famille_id]["FAMILLE_NOM_REGIME"] or ""
                                                if dictColonnePerso["code"] == "caisse": donnee = dictInfosFamilles[inscription.famille_id]["FAMILLE_NOM_CAISSE"] or ""
                                                if dictColonnePerso["code"] == "date_naiss": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_DATE_NAISS"] or ""
                                                if dictColonnePerso["code"] == "medecin_nom": donnee = dictInfosIndividus[inscription.individu_id]["MEDECIN_NOM"] or ""
                                                if dictColonnePerso["code"] == "tel_mobile": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_TEL_MOBILE"] or ""
                                                if dictColonnePerso["code"] == "tel_domicile": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_TEL_DOMICILE"] or ""
                                                if dictColonnePerso["code"] == "mail": donnee = dictInfosIndividus[inscription.individu_id]["INDIVIDU_MAIL"] or ""
                                                if dictColonnePerso["code"] == "regimes_alimentaires": donnee = ", ".join([regime.nom for regime in inscription.individu.regimes_alimentaires.all()])

                                                if dictColonnePerso["code"] == "adresse_residence":
                                                    rue = dictInfosIndividus[inscription.individu_id]["INDIVIDU_RUE"]
                                                    cp = dictInfosIndividus[inscription.individu_id]["INDIVIDU_CP"]
                                                    ville = dictInfosIndividus[inscription.individu_id]["INDIVIDU_VILLE"]
                                                    donnee = u"%s %s %s" % (rue or "", cp or "", ville or "")

                                                # Questionnaires
                                                if dictColonnePerso["code"].startswith("question_") and "famille" in dictColonnePerso["code"]:
                                                    donnee = dictInfosFamilles[inscription.famille_id]["QUESTION_%s" % dictColonnePerso["code"][17:]]
                                                if dictColonnePerso["code"].startswith("question_") and "individu" in dictColonnePerso["code"]:
                                                    donnee = dictInfosIndividus[inscription.individu_id]["QUESTION_%s" % dictColonnePerso["code"][18:]]

                                                # Code-barre individu
                                                if dictColonnePerso["code"] == "codebarres_individu":
                                                    type_donnee = "code-barres"
                                                    donnee = code39.Extended39("I%06d" % inscription.individu_id, humanReadable=False)

                                            except :
                                                donnee = ""

                                        if type_donnee == "unicode":
                                            ligne.append(Paragraph(str(donnee), styleNormal))
                                        else:
                                            ligne.append(donnee)


                                    # Informations personnelles
                                    listeInfos = []
                                    paraStyle = ParagraphStyle(name="infos", fontName="Helvetica", fontSize=7, leading=8, spaceAfter=2)

                                    # Mémo-journée
                                    if inscription.pk in dictMemos:
                                        for date in self.dict_donnees["dates"]:
                                            if date in dictMemos[inscription.pk]:
                                                memo_journee = dictMemos[inscription.pk][date]
                                                if len(self.dict_donnees["dates"]) > 1:
                                                    memo_journee = "%02d/%02d/%04d : %s" % (date.day, date.month, date.year, memo_journee)
                                                if len(memo_journee) > 0 and memo_journee[-1] != ".": memo_journee += "."
                                                listeInfos.append(ParagraphAndImage(Paragraph(memo_journee, paraStyle), Image(settings.STATIC_ROOT + "/images/attention.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Messages individuels
                                    if inscription.individu_id in dictMessagesIndividus:
                                        for note in dictMessagesIndividus[inscription.individu_id]:
                                            listeInfos.append(ParagraphAndImage(Paragraph(note.texte, paraStyle), Image(settings.STATIC_ROOT + "/images/mail.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Récupère la liste des familles rattachées à cet individu
                                    listeIDfamille = []
                                    for date, dictUnitesTemps in dictInscription["listeConso"].items():
                                        for temp, listeConso in dictUnitesTemps.items():
                                            for dictConsoTemp in listeConso :
                                                if dictConsoTemp["IDfamille"] not in listeIDfamille:
                                                    listeIDfamille.append(dictConsoTemp["IDfamille"])

                                    # Messages familiaux
                                    for IDfamille in listeIDfamille:
                                        if IDfamille in dictMessagesFamilles:
                                            for note in dictMessagesFamilles[IDfamille]:
                                                listeInfos.append(ParagraphAndImage(Paragraph(note.texte, paraStyle), Image(settings.STATIC_ROOT + "/images/mail.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Cotisations manquantes
                                    if self.dict_donnees["afficher_cotisations_manquantes"]:
                                        for IDfamille in listeIDfamille:
                                            if IDfamille in dictCotisations:
                                                if dictCotisations[IDfamille]["nbre"] == 1:
                                                    texteCotisation = "1 adhésion manquante : %s" % dictCotisations[IDfamille]["texte"]
                                                else:
                                                    texteCotisation = "%d adhésions manquantes : %s" % (dictCotisations[IDfamille]["nbre"], dictCotisations[IDfamille]["texte"])
                                                listeInfos.append(ParagraphAndImage(Paragraph(texteCotisation, paraStyle), Image(settings.STATIC_ROOT + "/images/cotisation.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Pièces manquantes
                                    if self.dict_donnees["afficher_pieces_manquantes"]:
                                        for IDfamille in listeIDfamille:
                                            if IDfamille in dictPieces:
                                                if dictPieces[IDfamille]["nbre"] == 1:
                                                    textePiece = "1 pièce manquante : %s." % dictPieces[IDfamille]["texte"]
                                                else:
                                                    textePiece = "%d pièces manquantes : %s." % (dictPieces[IDfamille]["nbre"], dictPieces[IDfamille]["texte"])
                                                listeInfos.append(ParagraphAndImage(Paragraph(textePiece, paraStyle), Image(settings.STATIC_ROOT + "/images/piece.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Sieste
                                    texte_sieste = inscription.individu.type_sieste.nom if inscription.individu.type_sieste else None
                                    if texte_sieste:
                                        if texte_sieste and texte_sieste[-1] != ".": texte_sieste += "."
                                        listeInfos.append(ParagraphAndImage(Paragraph(texte_sieste, paraStyle), Image(settings.STATIC_ROOT + "/images/reveil.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Anniversaire
                                    for date in self.dict_donnees["dates"]:
                                        if inscription.individu.date_naiss and inscription.individu.date_naiss.strftime("%d/%m") == date.strftime("%d/%m"):
                                            if len(self.dict_donnees["dates"]) > 1:
                                                texte_anniversaire = "C'est l'anniversaire de %s le %s (%s ans) !" % (prenom, date.strftime("%d/%m"), inscription.individu.Get_age(today=date))
                                            else:
                                                texte_anniversaire = "C'est l'anniversaire de %s (%s ans) !" % (prenom, inscription.individu.Get_age(today=date))
                                            listeInfos.append(ParagraphAndImage(Paragraph(texte_anniversaire, paraStyle), Image(settings.STATIC_ROOT + "/images/anniversaire.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Informations personnelles
                                    if inscription.individu_id in dictInfosPerso:
                                        for info in dictInfosPerso[inscription.individu_id]:
                                            recapitulatif["informations"].append(info)

                                            # Intitulé et description
                                            if info.description:
                                                texte = "<b>%s</b> : %s" % (info.intitule, info.description)
                                            else:
                                                texte = "%s" % info.intitule
                                            if len(texte) > 0 and texte[-1] != ".": texte += "."
                                            # Traitement médical
                                            if info.traitement_medical and info.description_traitement:
                                                texteDatesTraitement = ""
                                                if info.date_debut_traitement != None and info.date_fin_traitement != None :
                                                    texteDatesTraitement = " du %s au %s" % (utils_dates.ConvertDateToFR(info.date_debut_traitement), utils_dates.ConvertDateToFR(info.date_fin_traitement))
                                                if info.date_debut_traitement != None and info.date_fin_traitement == None :
                                                    texteDatesTraitement = " à partir du %s" % utils_dates.ConvertDateToFR(info.date_debut_traitement)
                                                if info.date_debut_traitement == None and info.date_fin_traitement != None :
                                                    texteDatesTraitement = " jusqu'au %s" % utils_dates.ConvertDateToFR(info.date_fin_traitement)
                                                texte += "Traitement%s : %s." % (texteDatesTraitement, info.description_traitement)
                                            listeInfos.append(ParagraphAndImage(Paragraph(texte, paraStyle), Image(settings.STATIC_ROOT + "/images/information.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    # Régimes alimentaires
                                    if self.dict_donnees["afficher_regimes_alimentaires"] and inscription.individu.regimes_alimentaires.exists():
                                        texte_regimes = ", ".join([regime.nom for regime in inscription.individu.regimes_alimentaires.all()])
                                        recapitulatif["regimes"].append((inscription.individu, texte_regimes))
                                        listeInfos.append(ParagraphAndImage(Paragraph(texte_regimes, paraStyle), Image(settings.STATIC_ROOT + "/images/repas.png", width=8, height=8), xpad=1, ypad=0, side="left"))

                                    if self.dict_donnees["afficher_informations"]:
                                        if not self.dict_donnees["masquer_informations"]:
                                            ligne.append(listeInfos)
                                        else:
                                            ligne.append("")

                                    if not ligneVide or self.dict_donnees["afficher_inscrits"]:
                                        # Ajout de la ligne individuelle dans le tableau
                                        dataTableau.append(ligne)
                                        # Mémorise les lignes pour export Excel
                                        listeLignesExport.append(ligne)
                                        indexLigne += 1

                                # Création des lignes vierges
                                for x in range(0, self.dict_donnees["nbre_lignes_vierges"]):
                                    ligne = []
                                    for col in labelsColonnes:
                                        ligne.append("")
                                    dataTableau.append(ligne)

                                # Style du tableau
                                colPremiereUnite = 1
                                if self.dict_donnees["afficher_photos"] != "non":
                                    colPremiereUnite += 1
                                if self.dict_donnees["afficher_age"]:
                                    colPremiereUnite += 1

                                style = [
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                                    ('ALIGN', (0, 0), (-2, -1), 'CENTRE'),
                                    ('ALIGN', (0, 0), (-1, 0), 'CENTRE'),
                                    ('FONT', (0, 0), (-1, 0), "Helvetica", 6),
                                    ('LEFTPADDING', (0, 0), (-1, 0), 0),
                                    ('RIGHTPADDING', (0, 0), (-1, 0), 0),
                                    ('LEFTPADDING', (1, 1), (-2, -1), 1),
                                    ('RIGHTPADDING', (1, 1), (-2, -1), 1),
                                ]

                                # Formatage de la ligne DATES
                                if len(self.dict_donnees["dates"]) > 1:
                                    style.append(('BACKGROUND', (0, 0), (-1, 0), self.dict_donnees["couleur_fond_titre"]))
                                    style.append(('BACKGROUND', (0, 1), (-1, 1), self.dict_donnees["couleur_fond_entetes"]))
                                    style.append(('GRID', (0, 1), (-1, -1), 0.25, colors.black))
                                    style.append(('LINEBEFORE', (0, 0), (0, 0), 0.25, colors.black))
                                    style.append(('LINEAFTER', (-1, 0), (-1, 0), 0.25, colors.black))
                                    style.append(('ALIGN', (0, 1), (-1, 1), 'CENTRE'))
                                    style.append(('FONT', (0, 0), (-1, 0), "Helvetica-Bold", 8))
                                    for date, positionG, positionD in listePositionsDates:
                                        style.append(('SPAN', (positionG, 0), (positionD, 0)))
                                        style.append(('BACKGROUND', (positionG, 0), (positionD, 0), (1, 1, 1)))
                                        style.append(('BOX', (positionG, 0), (positionD, -1), 1, colors.black))
                                else:
                                    style.append(('GRID', (0,0), (-1, -1), 0.25, colors.black))
                                    style.append(('BACKGROUND', (0, 0), (-1, 0), self.dict_donnees["couleur_fond_entetes"]))

                                # Vérifie si la largeur du tableau est inférieure à la largeur de la page
                                if not mode_export_excel:
                                    for largeur in largeursColonnes:
                                        if largeur < 0:
                                            self.erreurs.append("Il y a trop de colonnes dans le tableau ! Veuillez sélectionner moins de jours dans le calendrier.")
                                            return False

                                # Création du tableau
                                if len(self.dict_donnees["dates"]) > 1:
                                    repeatRows = 2
                                else :
                                    repeatRows = 1

                                # Hauteur de ligne individus
                                if self.dict_donnees["hauteur_ligne_individu"] == "automatique":
                                    hauteursLignes = None
                                else :
                                    hauteursLignes = [int(self.dict_donnees["hauteur_ligne_individu"]) for x in range(len(dataTableau))]
                                    hauteursLignes[0] = 12
                                    hauteursLignes[-1] = 10

                                tableau = Table(dataTableau, largeursColonnes, rowHeights=hauteursLignes, repeatRows=repeatRows)
                                tableau.setStyle(TableStyle(style))
                                self.story.append(tableau)

                                # Création du tableau des totaux
                                if self.dict_donnees["afficher_photos"] != "non":
                                    colNomsIndividus = 1
                                else:
                                    colNomsIndividus = 0

                                ligne = []
                                for indexCol in range(0, len(labelsColonnes)):
                                    if indexCol in dictTotauxColonnes:
                                        valeur = dictTotauxColonnes[indexCol]
                                    else:
                                        valeur = ""
                                    if indexCol == colNomsIndividus:
                                        if indexLigne == 1:
                                            valeur = "1 individu"
                                        else:
                                            valeur = "%d individus" % indexLigne
                                    ligne.append(valeur)
                                listeLignesExport.append(ligne)

                                if self.dict_donnees["afficher_informations"]:
                                    colDerniereUnite = -2
                                else :
                                    colDerniereUnite = -1

                                style = [
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
                                    ('GRID', (colPremiereUnite, -1), (colDerniereUnite, -1), 0.25, colors.black),
                                    ('BACKGROUND', (colPremiereUnite, -1), (colDerniereUnite, -1), self.dict_donnees["couleur_fond_total"])
                                    ]

                                if len(self.dict_donnees["dates"]) > 1:
                                    for date, positionG, positionD in listePositionsDates:
                                        style.append(('BOX', (positionG, 0), (positionD, 0), 1, colors.black))

                                tableau = Table([ligne,], largeursColonnes)
                                tableau.setStyle(TableStyle(style))
                                self.story.append(tableau)

                                # Récapitulatif
                                if self.dict_donnees["afficher_recapitulatif"]:

                                    dataTableauRecap = []

                                    style_categorie = ParagraphStyle(name="recap_categorie", fontName="Helvetica-Bold", fontSize=7, leading=8, spaceAfter=2)
                                    style_info = ParagraphStyle(name="recap_info", fontName="Helvetica", fontSize=7, leading=8, spaceAfter=2)

                                    info_par_categories = {}
                                    for info in recapitulatif["informations"]:
                                        info_par_categories.setdefault(info.categorie, [])
                                        info_par_categories[info.categorie].append(info)

                                    for categorie, infos in info_par_categories.items():
                                        dataTableauRecap.append(Paragraph(categorie.nom, style_categorie))
                                        for info in infos:
                                            dataTableauRecap.append(Paragraph("%s : %s." % (info.individu, info.intitule), style_info, bulletText='   -'))

                                    if recapitulatif["regimes"]:
                                        dataTableauRecap.append(Paragraph("Régimes alimentaires", style_categorie))
                                        for individu, texte_regimes in recapitulatif["regimes"]:
                                            dataTableauRecap.append(Paragraph("%s : %s." % (individu.Get_nom(), texte_regimes), style_info, bulletText='   -'))

                                    if dataTableauRecap:
                                        styleRecap = [
                                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                            ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                                            ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
                                            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                                            ('BACKGROUND', (0, 0), (-1, -1), self.dict_donnees["couleur_fond_entetes"])
                                        ]
                                        self.story.append(Spacer(0, 10))
                                        tableauRecap = Table([(dataTableauRecap,),], [largeur_contenu,])
                                        tableauRecap.setStyle(styleRecap)
                                        self.story.append(tableauRecap)

                                self.story.append(Spacer(0, 10))

                                # Export
                                listeExport.append({"activite": activite.nom, "groupe": groupe.nom if groupe else "", "ecole": nomEcole, "classe": nomClasse, "evenement": nomEvenement, "etiquette": nomEtiquette, "lignes": listeLignesExport})

                                # Saut de page après une étiquette
                                # if self.GetPage("etiquettes").checkbox_etiquettes.GetValue() == True and self.GetPage("etiquettes").checkbox_saut_etiquettes.GetValue() == True :
                                #     CreationSautPage()

                            # Saut de page après un évènement
                            if self.dict_donnees["regroupement_evenements"] and self.dict_donnees["saut_page_evenements"]:
                                CreationSautPage()

                        # Saut de page après une classe
                        if self.dict_donnees["regroupement_scolarite"] == "classes" and self.dict_donnees["saut_page_classes"] and indexClasse <= len(listeInfosScolarite):
                            CreationSautPage()

                        # Saut de page après une école
                        if self.dict_donnees["regroupement_scolarite"] in ("classes", "ecoles") and self.dict_donnees["saut_page_ecoles"]:
                            if indexClasse < len(listeInfosScolarite) and IDecole != listeInfosScolarite[indexClasse]["IDecole"]:
                                CreationSautPage()

                    # Saut de page après un groupe
                    if self.dict_donnees["saut_page_groupes"] and indexGroupe < len(dictOuvertures[activite.pk]):
                        CreationSautPage()

            # Saut de page après une activité
            if self.dict_donnees["saut_page_activites"] and indexActivite < len(liste_activites):
                CreationSautPage()

        # Suppression de la dernière page si elle est vide
        try :
            element = str(self.story[-3])
            if element == "PageBreak()":
                self.story.pop(-1)
                self.story.pop(-1)
                self.story.pop(-1)
        except :
            pass

        # Suppression du dernier spacer s'il y en a un
        try:
            element = str(self.story[-1])
            if element == "Spacer(0, 20)":
                self.story.pop(-1)
        except :
            pass

        # Si mode export Excel
        if mode_export_excel:
            return listeExport, largeursColonnes


    def TriClasses(self, listeScolarite=[]):
        """ Tri des classes par nom d'école, par nom de classe et par niveau """
        listeResultats = []

        # Insertion des écoles et classes inconnues
        if self.dict_donnees["afficher_scolarite_inconnue"]:
            if self.dict_donnees["regroupement_scolarite"] == "ecoles" and None in listeScolarite:
                listeResultats.append({"IDecole": None, "nomEcole": "Ecole inconnue", "nomClasse": None, "IDclasse": None})
            if self.dict_donnees["regroupement_scolarite"] == "classes" and None in listeScolarite:
                listeResultats.append({"IDecole": None, "nomEcole": "Ecole inconnue", "nomClasse": "Classe inconnue", "IDclasse": None})

        # Insertion des écoles
        # listeEcoles = []
        # for IDecole, ecole in dictEcoles.items():
        #     listeEcoles.append((ecole.nom, IDecole))
        # listeEcoles.sort()

        # listeEcoles = sorted(self.liste_ecoles, key=lambda x: x.nom)

        # Insertion des classes
        for ecole in self.liste_ecoles:
            if self.dict_donnees["regroupement_scolarite"] == "ecoles":
                if ecole.pk in listeScolarite:
                    listeResultats.append({"IDecole": ecole.pk, "nomEcole": ecole.nom, "nomClasse": None, "IDclasse": None})

            if self.dict_donnees["regroupement_scolarite"] == "classes":
                # Tri des classes par niveau
                liste_classes_temp = []
                for classe in self.dict_classes.get(ecole, []):
                    temp = []
                    for niveau in classe.niveaux.all().order_by("ordre"):
                        temp.append(niveau.ordre)
                    liste_classes_temp.append((temp, classe))
                liste_classes_temp = sorted(liste_classes_temp, key=operator.itemgetter(0))

                for niveau, classe in liste_classes_temp:
                    if classe.pk in listeScolarite:
                        listeResultats.append({"IDecole": ecole.pk, "nomEcole": ecole.nom, "nomClasse": classe.nom, "IDclasse": classe.pk, "date_debut": classe.date_debut, "date_fin": classe.date_fin})

                # listeClassesTemp = dictEcoles[IDecole]["classes"]
                # listeClassesTemp.sort()
                # for listeOrdresNiveaux, nomClasse, txtNiveaux, IDclasse, date_debut, date_fin in listeClassesTemp:
                #     if IDclasse in listeScolarite:
                #         listeResultats.append({"IDecole": IDecole, "nomEcole": nomEcole, "nomClasse": nomClasse, "IDclasse": IDclasse, "date_debut": date_debut, "date_fin": date_fin})

        return listeResultats

    def Formate_etat(self, etat=None):
        if etat == "reservation": return "<FONT face='Helvetica' color='#FF9E1E'>(Résa)</FONT>"
        if etat == "present": return "<FONT face='Helvetica' color='#28a745'>(Prés)</FONT>"
        if etat == "attente": return "<FONT face='Helvetica' color='#abcbff'>(Att)</FONT>"
        if etat == "refus": return "<FONT face='Helvetica' color='#ff1904'>(Refus)</FONT>"
        if etat == "absenti": return "<FONT face='Helvetica' color='#a371ff'>(AbsI)</FONT>"
        if etat == "absentj": return "<FONT face='Helvetica' color='#e83e8c'>(AbsJ)</FONT>"
        return ""

    def Exporter_excel(self, dict_donnees=None):
        self.dict_donnees = dict_donnees
        self.erreurs = []
        self.story = []

        donnees = self.Draw(mode_export_excel=True)
        if not donnees:
            return
        listeExport, largeursColonnes = donnees

        # Création du répertoire et du nom du fichier
        rep_temp = os.path.join("temp", str(uuid.uuid4()))
        rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
        if not os.path.isdir(rep_destination):
            os.makedirs(rep_destination)
        nom_fichier = "%s.xlsx" % self.titre
        chemin_fichier = os.path.join(rep_destination, nom_fichier)
        self.nom_fichier = os.path.join(rep_temp, nom_fichier)

        # Création du classeur
        import xlsxwriter
        classeur = xlsxwriter.Workbook(chemin_fichier)

        numFeuille = 1
        for dictFeuille in listeExport:
            # Nom de la feuille
            titre = "Page %d" % numFeuille
            feuille = classeur.add_worksheet(titre)

            # Titre de la page
            listeLabels = []
            if dictFeuille["activite"]: listeLabels.append(dictFeuille["activite"])
            if dictFeuille["groupe"]: listeLabels.append(dictFeuille["groupe"])
            if dictFeuille["ecole"]: listeLabels.append(dictFeuille["ecole"])
            if dictFeuille["classe"]: listeLabels.append(dictFeuille["classe"])
            if dictFeuille["evenement"]: listeLabels.append(dictFeuille["evenement"])
            if dictFeuille["etiquette"]: listeLabels.append(dictFeuille["etiquette"])
            titre = " - ".join(listeLabels)
            feuille.write(0, 0, titre)

            numLigne = 2
            for ligne in dictFeuille["lignes"]:

                numColonne = 0
                for valeur in ligne:
                    # Si c'est un Paragraph
                    if isinstance(valeur, Paragraph):
                        valeur = valeur.text
                    # Largeur colonne
                    if type(valeur) == str and ("Nom - " in valeur or valeur == "Informations"):
                        feuille.set_column(numColonne, numColonne, 50)
                    # Valeur case
                    if type(valeur) in (str, int):
                        # Formatage des heures
                        if type(valeur) == str and len(valeur) == 11 and valeur[2] == "h" and valeur[8] == "h":
                            valeur = valeur.replace("\n", "-")
                        feuille.write(numLigne, numColonne, valeur or "")
                    # Si c'est une liste
                    if type(valeur) == list:
                        listeInfos = []
                        for element in valeur:
                            try:
                                valeur = element.text
                            except:
                                valeur = element.P.text
                            if valeur == "X":
                                valeur = "1"
                            listeInfos.append(valeur)
                        if len(listeInfos) == 1 and listeInfos[0] == "1":
                            texte = int(valeur)
                        else:
                            texte = " - ".join(listeInfos)
                        feuille.write(numLigne, numColonne, texte)

                    numColonne += 1
                numLigne += 1
            numFeuille += 1

        # Finalisation du fichier xlsx
        classeur.close()
