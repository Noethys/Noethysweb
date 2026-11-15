# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Editions des collaborateurs : fiches, trombinoscope, liste téléphonique, liste personnalisable, étiquettes et badges """

import datetime, os, re, uuid
from django.conf import settings
from django.http import JsonResponse
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Table, TableStyle, Spacer, PageBreak, KeepTogether, CondPageBreak
from core.models import PieceCollaborateur, QuestionnaireReponse, QuestionnaireChoix
from core.utils import utils_fichiers
from collaborateurs.forms.editions import COLONNES_LISTE, GABARITS_ETIQUETTES
from collaborateurs.utils import utils_pieces_manquantes
from collaborateurs.utils.utils_editions import Impression_edition, Get_contrats, Get_situation, Style, P, Date, Image_photo, Chemin_photo, Style_tableau, \
    Titre_section, Texte_periode_contrat, COULEUR_TEXTE_CLAIR, COULEUR_PRINCIPALE, FONT, FONT_BOLD, Get_organisateur


def Taille_page(orientation="PORTRAIT"):
    return landscape(A4) if orientation == "PAYSAGE" else A4


def Age(date_naiss=None, date=None):
    if not date_naiss:
        return None
    date = date or datetime.date.today()
    return date.year - date_naiss.year - ((date.month, date.day) < (date_naiss.month, date_naiss.day))


def Texte_anciennete(debut=None, date=None):
    """ Ancienneté depuis le début du premier contrat : "3 ans 2 mois" """
    if not debut:
        return ""
    date = date or datetime.date.today()
    mois = (date.year - debut.year) * 12 + date.month - debut.month - (1 if date.day < debut.day else 0)
    if mois < 0:
        return "à venir"
    annees, mois = divmod(mois, 12)
    morceaux = []
    if annees:
        morceaux.append("%d an%s" % (annees, "s" if annees > 1 else ""))
    if mois or not annees:
        morceaux.append("%d mois" % mois)
    return " ".join(morceaux)


def Adresse(collaborateur=None):
    return " ".join(valeur for valeur in (collaborateur.rue_resid, collaborateur.cp_resid, collaborateur.ville_resid) if valeur)


def Exporter_tableau_xlsx(titre="", entetes=[], lignes=[]):
    """ Export d'un tableau simple vers Excel. Renvoie l'URL du fichier. """
    import xlsxwriter
    utils_fichiers.GetTempRep()
    rep_base = os.path.join("temp", str(uuid.uuid4()))
    os.makedirs(os.path.join(settings.MEDIA_ROOT, rep_base))
    nom_fichier = "%s.xlsx" % (re.sub(r"[^\w\-]+", "_", titre, flags=re.UNICODE).strip("_") or "Export")
    classeur = xlsxwriter.Workbook(os.path.join(settings.MEDIA_ROOT, rep_base, nom_fichier))
    feuille = classeur.add_worksheet("Liste")
    f_entete = classeur.add_format({"bold": True, "bg_color": "#EEF1F5", "border": 1, "text_wrap": True, "valign": "vcenter"})
    f_date = classeur.add_format({"num_format": "dd/mm/yyyy"})
    largeurs = [len(entete) + 2 for entete in entetes]
    for index, entete in enumerate(entetes):
        feuille.write(0, index, entete, f_entete)
    for num_ligne, ligne in enumerate(lignes, 1):
        for index, valeur in enumerate(ligne):
            if isinstance(valeur, datetime.date):
                feuille.write_datetime(num_ligne, index, datetime.datetime.combine(valeur, datetime.time(0)), f_date)
                largeurs[index] = max(largeurs[index], 11)
            elif valeur is None:
                feuille.write_blank(num_ligne, index, None)
            else:
                feuille.write(num_ligne, index, valeur)
                largeurs[index] = max(largeurs[index], min(len(str(valeur)) + 2, 60))
    for index, largeur in enumerate(largeurs):
        feuille.set_column(index, index, largeur)
    feuille.autofilter(0, 0, max(len(lignes), 1), max(len(entetes) - 1, 0))
    feuille.freeze_panes(1, 0)
    classeur.close()
    return os.path.join(settings.MEDIA_URL, rep_base, nom_fichier)


# ------------------------------------------------- Fiches -------------------------------------------------

class Impression_fiches(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        collaborateurs = self.dict_donnees["collaborateurs"]
        rubriques = parametres["rubriques"]
        masquer_vides = parametres.get("masquer_vides")
        largeur = self.largeur_utile
        contrats = Get_contrats(collaborateurs)
        pieces = {}
        for piece in PieceCollaborateur.objects.select_related("type_piece").filter(collaborateur__in=collaborateurs).order_by("type_piece__nom", "-date_fin"):
            pieces.setdefault(piece.collaborateur_id, []).append(piece)
        reponses = {}
        if "questionnaire" in rubriques:
            dict_choix = {choix.pk: choix for choix in QuestionnaireChoix.objects.all()}
            for reponse in QuestionnaireReponse.objects.select_related("question").filter(collaborateur__in=collaborateurs).order_by("question__ordre"):
                texte = re.sub(r"<[^>]+>", "", str(reponse.Get_reponse_fr(dict_choix=dict_choix))).strip()
                reponses.setdefault(reponse.collaborateur_id, []).append((reponse.question.label, texte))

        style_label = Style("label", 8, couleur=COULEUR_TEXTE_CLAIR)
        style_valeur = Style("valeur", 8.5)

        def Tableau_valeurs(valeurs=[], nbre_colonnes=2):
            """ Couples libellé / valeur répartis sur plusieurs colonnes """
            valeurs = [(label, valeur) for label, valeur in valeurs if valeur or not masquer_vides]
            if not valeurs:
                return None
            lignes = []
            for index in range(0, len(valeurs), nbre_colonnes):
                ligne = []
                for label, valeur in valeurs[index:index + nbre_colonnes]:
                    ligne += [P(label, style_label), P(valeur or "-", style_valeur)]
                ligne += ["", ""] * (nbre_colonnes - len(valeurs[index:index + nbre_colonnes]))
                lignes.append(ligne)
            largeur_label = 32 * mm
            largeur_valeur = largeur / nbre_colonnes - largeur_label
            tableau = Table(lignes, [largeur_label, largeur_valeur] * nbre_colonnes)
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                                         ("LEFTPADDING", (0, 0), (-1, -1), 2), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#EDF0F3"))]))
            return tableau

        def Section(titre="", contenu=None):
            if contenu is None:
                return
            self.story.append(KeepTogether([Titre_section(titre, largeur), Spacer(0, 2 * mm), contenu]))
            self.story.append(Spacer(0, 5 * mm))

        for index, collaborateur in enumerate(collaborateurs):
            if index:
                self.story.append(PageBreak())
            liste_contrats = contrats.get(collaborateur.pk, [])
            contrat = Get_situation(liste_contrats)

            # En-tête de la fiche
            self.Entete("Fiche collaborateur", "Situation au %s" % Date(datetime.date.today()), espace_apres=4 * mm)
            bloc = [P(collaborateur.Get_nom(), Style("nom", 17, gras=True, interligne=21))]
            if contrat:
                bloc.append(P("%s%s - %s" % (contrat.type_poste.nom, " (%s)" % contrat.type_contrat.nom if contrat.type_contrat else "", Texte_periode_contrat(contrat)),
                              Style("poste", 10, couleur=COULEUR_PRINCIPALE)))
            else:
                bloc.append(P("Aucun contrat", Style("poste", 10, couleur=COULEUR_TEXTE_CLAIR)))
            if liste_contrats:
                bloc.append(P("Ancienneté : %s" % Texte_anciennete(liste_contrats[0].date_debut), Style("anciennete", 8.5, couleur=COULEUR_TEXTE_CLAIR)))
            if parametres.get("afficher_photo"):
                tableau = Table([[Image_photo(collaborateur, 24 * mm, 30 * mm), bloc]], [30 * mm, largeur - 30 * mm])
            else:
                tableau = Table([[bloc]], [largeur])
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            self.story.append(tableau)
            self.story.append(Spacer(0, 5 * mm))

            if "identite" in rubriques:
                age = Age(collaborateur.date_naiss)
                Section("Identité et coordonnées", Tableau_valeurs([
                    ("Civilité", collaborateur.get_civilite_display()), ("Nom de naissance", collaborateur.nom_jfille),
                    ("Date de naissance", "%s (%d ans)" % (Date(collaborateur.date_naiss), age) if age is not None else ""), ("Nationalité", collaborateur.nationalite),
                    ("Adresse", Adresse(collaborateur)), ("Tél. portable", collaborateur.tel_mobile), ("Tél. domicile", collaborateur.tel_domicile),
                    ("Tél. professionnel", collaborateur.travail_tel), ("Email personnel", collaborateur.mail), ("Email professionnel", collaborateur.travail_mail),
                ]))

            if "groupes" in rubriques:
                Section("Groupes et qualifications", Tableau_valeurs([
                    ("Groupes", ", ".join(groupe.nom for groupe in collaborateur.groupes.all())),
                    ("Qualifications", ", ".join(qualification.nom for qualification in collaborateur.qualifications.all())),
                ], nbre_colonnes=1))

            if "contrats" in rubriques and (liste_contrats or not masquer_vides):
                lignes = [["Type", "Poste", "Début", "Fin", "Heures/sem.", "Objectif"]]
                for item in reversed(liste_contrats):
                    lignes.append([item.type_contrat.nom if item.type_contrat else "", item.type_poste.nom, Date(item.date_debut), Date(item.date_fin) or "Indéterminée",
                                   ("%s h" % ("%g" % float(item.heures_hebdo)).replace(".", ",")) if item.heures_hebdo else "", item.get_objectif_mode_display()])
                if len(lignes) == 1:
                    lignes.append(["Aucun contrat", "", "", "", "", ""])
                tableau = Table(lignes, [largeur * part for part in (0.17, 0.25, 0.13, 0.15, 0.12, 0.18)], repeatRows=1)
                tableau.setStyle(Style_tableau(nbre_lignes=len(lignes)))
                Section("Contrats", tableau)

            if "pieces" in rubriques:
                liste_pieces = pieces.get(collaborateur.pk, [])
                manquantes = utils_pieces_manquantes.Get_pieces_manquantes(collaborateur=collaborateur, only_invalides=True)
                if liste_pieces or manquantes or not masquer_vides:
                    lignes = [["Pièce", "Début", "Fin de validité", "Etat"]]
                    aujourdhui = datetime.date.today()
                    for piece in liste_pieces:
                        if piece.statut == "VALIDE":
                            etat = "Valide" if not piece.date_fin or piece.date_fin >= aujourdhui else "Expirée"
                        else:
                            etat = piece.get_statut_display()
                        fin = "Illimitée" if piece.date_fin and piece.date_fin.year >= 2999 else Date(piece.date_fin)
                        lignes.append([P(piece.type_piece.nom if piece.type_piece else (piece.titre or "Autre pièce")), Date(piece.date_debut), fin, etat])
                    for manquante in manquantes:
                        lignes.append([P(manquante["label"]), "", "", "A fournir"])
                    if len(lignes) == 1:
                        lignes.append(["Aucune pièce", "", "", ""])
                    tableau = Table(lignes, [largeur * part for part in (0.5, 0.15, 0.17, 0.18)], repeatRows=1)
                    style = Style_tableau(nbre_lignes=len(lignes))
                    for num_ligne, ligne in enumerate(lignes[1:], 1):
                        if ligne[3] in ("Expirée", "A fournir", "Refusée"):
                            style.add("TEXTCOLOR", (3, num_ligne), (3, num_ligne), colors.HexColor("#A8323E"))
                            style.add("FONT", (3, num_ligne), (3, num_ligne), FONT_BOLD, 8)
                    tableau.setStyle(style)
                    Section("Pièces", tableau)

            if "questionnaire" in rubriques:
                Section("Questionnaire", Tableau_valeurs(reponses.get(collaborateur.pk, []), nbre_colonnes=1))

            if "memo" in rubriques and (collaborateur.memo or not masquer_vides):
                Section("Mémo", P(collaborateur.memo or "-", style_valeur))


# ------------------------------------------------- Trombinoscope -------------------------------------------------

def Regrouper(collaborateurs=[], regroupement="AUCUN", contrats={}):
    """ [(titre du groupe, [collaborateurs])] """
    if regroupement == "GROUPE":
        groupes, sans_groupe = {}, []
        for collaborateur in collaborateurs:
            liste_groupes = list(collaborateur.groupes.all())
            if not liste_groupes:
                sans_groupe.append(collaborateur)
            for groupe in liste_groupes:
                groupes.setdefault(groupe.nom, []).append(collaborateur)
        resultat = sorted(groupes.items())
        if sans_groupe:
            resultat.append(("Sans groupe", sans_groupe))
        return resultat
    if regroupement == "POSTE":
        postes = {}
        for collaborateur in collaborateurs:
            contrat = Get_situation(contrats.get(collaborateur.pk, []))
            postes.setdefault(contrat.type_poste.nom if contrat else "Sans poste", []).append(collaborateur)
        return sorted(postes.items())
    return [("", list(collaborateurs))]


class Impression_trombinoscope(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        collaborateurs = self.dict_donnees["collaborateurs"]
        contrats = Get_contrats(collaborateurs)
        nbre_colonnes = parametres["nbre_colonnes"]
        largeur_cellule = self.largeur_utile / nbre_colonnes
        largeur_photo = min(largeur_cellule - 8 * mm, 60 * mm)
        hauteur_photo = largeur_photo * 1.25
        self.Entete(parametres["titre"], "%d collaborateur%s" % (len(collaborateurs), "s" if len(collaborateurs) > 1 else ""))
        style_nom = Style("trombi_nom", 11 if nbre_colonnes <= 2 else (9 if nbre_colonnes <= 4 else 8), gras=True, alignement="centre")
        style_detail = Style("trombi_detail", 9 if nbre_colonnes <= 2 else (7.5 if nbre_colonnes <= 4 else 7), couleur=COULEUR_TEXTE_CLAIR, alignement="centre")

        for num_groupe, (titre, membres) in enumerate(Regrouper(collaborateurs, parametres["regroupement"], contrats)):
            if num_groupe and parametres.get("saut_page"):
                self.story.append(PageBreak())
                self.Entete(parametres["titre"], titre)
            cellules = []
            for collaborateur in membres:
                contenu = [Image_photo(collaborateur, largeur_photo, hauteur_photo), Spacer(0, 1.5 * mm), P(collaborateur.Get_nom(), style_nom)]
                contrat = Get_situation(contrats.get(collaborateur.pk, []))
                if parametres.get("afficher_poste") and contrat:
                    contenu.append(P(contrat.type_poste.nom, style_detail))
                if parametres.get("afficher_telephone") and collaborateur.tel_mobile:
                    contenu.append(P(collaborateur.tel_mobile, style_detail))
                cellules.append(contenu)
            lignes = [cellules[index:index + nbre_colonnes] for index in range(0, len(cellules), nbre_colonnes)]
            lignes[-1] += [""] * (nbre_colonnes - len(lignes[-1]))
            tableau = Table(lignes, [largeur_cellule] * nbre_colonnes)
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                         ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm)]))
            elements = []
            if titre:
                elements += [Titre_section("%s (%d)" % (titre, len(membres)), self.largeur_utile), Spacer(0, 1 * mm)]
            self.story.append(CondPageBreak(hauteur_photo + 30 * mm))
            self.story += elements + [tableau, Spacer(0, 4 * mm)]


# ------------------------------------------------- Liste téléphonique -------------------------------------------------

LABELS_TELEPHONES = {"poste": "Poste", "tel_mobile": "Tél. portable", "tel_domicile": "Tél. domicile", "travail_tel": "Tél. professionnel",
                     "mail": "Email personnel", "travail_mail": "Email professionnel"}


def Donnees_telephones(collaborateurs=[], parametres={}):
    contrats = Get_contrats(collaborateurs)
    colonnes = [code for code in LABELS_TELEPHONES if code in parametres["colonnes"]]
    entetes = ["Nom", "Prénom"] + [LABELS_TELEPHONES[code] for code in colonnes]
    groupes = []
    for titre, membres in Regrouper(collaborateurs, parametres.get("regroupement", "AUCUN"), contrats):
        lignes = []
        for collaborateur in membres:
            ligne = [collaborateur.nom, collaborateur.prenom or ""]
            for code in colonnes:
                if code == "poste":
                    contrat = Get_situation(contrats.get(collaborateur.pk, []))
                    ligne.append(contrat.type_poste.nom if contrat else "")
                else:
                    ligne.append(getattr(collaborateur, code) or "")
            lignes.append(ligne)
        groupes.append((titre, lignes))
    return entetes, groupes


class Impression_telephones(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        collaborateurs = self.dict_donnees["collaborateurs"]
        entetes, groupes = Donnees_telephones(collaborateurs, parametres)
        self.Entete(parametres["titre"], "%d collaborateur%s - document confidentiel, à usage interne" % (len(collaborateurs), "s" if len(collaborateurs) > 1 else ""))
        poids = {"Nom": 1.1, "Prénom": 1, "Poste": 1.2, "Email personnel": 1.9, "Email professionnel": 1.9}
        total = sum(poids.get(entete, 1) for entete in entetes)
        largeurs = [self.largeur_utile * poids.get(entete, 1) / total for entete in entetes]
        style_cellule = Style("tel", 8.5)
        style_nom = Style("tel_nom", 8.5, gras=True)
        for titre, lignes in groupes:
            donnees = [[P(entete, Style("tel_entete", 8.5, gras=True)) for entete in entetes]]
            donnees += [[P(valeur, style_nom if index == 0 else style_cellule) for index, valeur in enumerate(ligne)] for ligne in lignes]
            tableau = Table(donnees, largeurs, repeatRows=1)
            tableau.setStyle(Style_tableau(nbre_lignes=len(donnees), taille=8.5, padding=4))
            if titre:
                self.story.append(KeepTogether([Titre_section(titre, self.largeur_utile), Spacer(0, 1 * mm), tableau]))
            else:
                self.story.append(tableau)
            self.story.append(Spacer(0, 5 * mm))


# ------------------------------------------------- Liste personnalisable -------------------------------------------------

LABELS_COLONNES = dict(COLONNES_LISTE)
POIDS_COLONNES = {"adresse": 2.4, "mail": 2, "travail_mail": 2, "qualifications": 1.8, "groupes": 1.5, "nom": 1.3, "civilite": 0.7, "age": 0.5, "idcollaborateur": 0.5,
                  "cp_resid": 0.7, "heures_hebdo": 0.7, "date_naiss": 0.9, "contrat_debut": 0.9, "contrat_fin": 0.9}


def Donnees_liste(collaborateurs=[], parametres={}, pour_excel=False):
    contrats = Get_contrats(collaborateurs)
    colonnes = [code for code, label in COLONNES_LISTE if code in parametres["colonnes"]]
    lignes = []
    for collaborateur in collaborateurs:
        liste_contrats = contrats.get(collaborateur.pk, [])
        contrat = Get_situation(liste_contrats)
        valeurs = {
            "civilite": collaborateur.get_civilite_display(), "adresse": collaborateur.rue_resid or "", "age": Age(collaborateur.date_naiss),
            "groupes": ", ".join(groupe.nom for groupe in collaborateur.groupes.all()),
            "qualifications": ", ".join(qualification.nom for qualification in collaborateur.qualifications.all()),
            "poste": contrat.type_poste.nom if contrat else "", "type_contrat": contrat.type_contrat.nom if contrat and contrat.type_contrat else "",
            "contrat_debut": contrat.date_debut if contrat else None, "contrat_fin": contrat.date_fin if contrat else None,
            "heures_hebdo": float(contrat.heures_hebdo) if contrat and contrat.heures_hebdo else None,
            "anciennete": Texte_anciennete(liste_contrats[0].date_debut) if liste_contrats else "",
        }
        ligne = []
        for code in colonnes:
            valeur = valeurs[code] if code in valeurs else getattr(collaborateur, code, "")
            ligne.append(valeur)
        lignes.append((collaborateur, contrat, ligne))

    # Tri
    tri = parametres.get("tri", "nom")
    if tri == "poste":
        lignes.sort(key=lambda item: ((item[1].type_poste.nom if item[1] else "~"), item[0].nom, item[0].prenom or ""))
    elif tri == "contrat_debut":
        lignes.sort(key=lambda item: (item[1].date_debut if item[1] else datetime.date(2999, 1, 1), item[0].nom))
    elif tri == "ville_resid":
        lignes.sort(key=lambda item: ((item[0].ville_resid or "~").upper(), item[0].nom))

    resultat = []
    for collaborateur, contrat, ligne in lignes:
        if not pour_excel:
            ligne = [Date(valeur) if isinstance(valeur, datetime.date) else ("" if valeur is None else (("%g" % valeur).replace(".", ",") if isinstance(valeur, float) else valeur)) for valeur in ligne]
        resultat.append(ligne)
    return [LABELS_COLONNES[code] for code in colonnes], resultat


class Impression_liste(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        collaborateurs = self.dict_donnees["collaborateurs"]
        entetes, lignes = Donnees_liste(collaborateurs, parametres)
        colonnes = [code for code, label in COLONNES_LISTE if code in parametres["colonnes"]]
        self.Entete(parametres["titre"], "%d collaborateur%s" % (len(lignes), "s" if len(lignes) > 1 else ""))
        total = sum(POIDS_COLONNES.get(code, 1) for code in colonnes)
        largeurs = [self.largeur_utile * POIDS_COLONNES.get(code, 1) / total for code in colonnes]
        taille = 8 if len(colonnes) <= 8 else 7
        style_cellule = Style("liste", taille)
        donnees = [[P(entete, Style("liste_entete", taille, gras=True)) for entete in entetes]]
        donnees += [[P(valeur, style_cellule) for valeur in ligne] for ligne in lignes]
        tableau = Table(donnees, largeurs, repeatRows=1)
        tableau.setStyle(Style_tableau(nbre_lignes=len(donnees), taille=taille))
        self.story.append(tableau)


# ------------------------------------------------- Etiquettes et badges -------------------------------------------------

def Impression_etiquettes(collaborateurs=[], parametres={}):
    """ Planche d'étiquettes ou de badges (dessin direct sur le canvas). Renvoie la réponse JSON avec le nom du fichier. """
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.utils import ImageReader, simpleSplit

    gabarit = GABARITS_ETIQUETTES[parametres["gabarit"]]
    modele = parametres["modele"]
    contrats = Get_contrats(collaborateurs)
    organisateur = Get_organisateur()
    texte_badge = parametres.get("texte_badge") or (organisateur.nom if organisateur else "")

    utils_fichiers.GetTempRep()
    nom_fichier = "/temp/%s.pdf" % uuid.uuid4()
    canvas = Canvas(settings.MEDIA_ROOT + nom_fichier, pagesize=A4)
    canvas.setTitle("Etiquettes et badges")
    largeur_page, hauteur_page = A4
    l, h = gabarit["largeur"] * mm, gabarit["hauteur"] * mm
    par_page = gabarit["colonnes"] * gabarit["lignes"]

    def Texte_ajuste(texte="", police=FONT, taille=10, largeur_max=0, taille_min=6):
        while taille > taille_min and canvas.stringWidth(texte, police, taille) > largeur_max:
            taille -= 0.5
        return taille

    def Dessiner(collaborateur, x, y):
        contrat = Get_situation(contrats.get(collaborateur.pk, []))
        poste = contrat.type_poste.nom if contrat and parametres.get("afficher_poste") else ""
        marge = 4 * mm
        if parametres.get("contours"):
            canvas.setStrokeColor(colors.HexColor("#B8C2CC"))
            canvas.setLineWidth(0.3)
            canvas.roundRect(x, y, l, h, 2 * mm if modele == "BADGE" else 1 * mm, stroke=1, fill=0)

        if modele == "ADRESSE":
            lignes = ["%s %s" % (collaborateur.get_civilite_display(), collaborateur.Get_nom()), collaborateur.rue_resid or "",
                      " ".join(valeur for valeur in (collaborateur.cp_resid, collaborateur.ville_resid) if valeur)]
            lignes_finales = []
            for ligne in lignes:
                lignes_finales += simpleSplit(ligne, FONT, 9.5, l - 2 * marge) if ligne else []
            hauteur_bloc = len(lignes_finales) * 12
            ligne_y = y + h / 2 + hauteur_bloc / 2 - 9.5
            for index, ligne in enumerate(lignes_finales):
                canvas.setFont(FONT_BOLD if index == 0 else FONT, 9.5)
                canvas.setFillColor(colors.black)
                canvas.drawString(x + marge, ligne_y, ligne)
                ligne_y -= 12

        elif modele == "NOM":
            taille = Texte_ajuste(collaborateur.Get_nom(), FONT_BOLD, 16, l - 2 * marge)
            canvas.setFont(FONT_BOLD, taille)
            canvas.setFillColor(colors.black)
            canvas.drawCentredString(x + l / 2, y + h / 2 + (2 * mm if poste else -taille / 3), collaborateur.Get_nom())
            if poste:
                canvas.setFont(FONT, 9)
                canvas.setFillColor(COULEUR_PRINCIPALE)
                canvas.drawCentredString(x + l / 2, y + h / 2 - 5 * mm, poste[:60])

        else:
            # Badge : bandeau, photo, nom, poste
            hauteur_bandeau = min(9 * mm, h * 0.17)
            canvas.setFillColor(COULEUR_PRINCIPALE)
            canvas.roundRect(x, y + h - hauteur_bandeau, l, hauteur_bandeau, 2 * mm, stroke=0, fill=1)
            canvas.rect(x, y + h - hauteur_bandeau, l, hauteur_bandeau / 2, stroke=0, fill=1)
            canvas.setFillColor(colors.white)
            taille = Texte_ajuste(texte_badge, FONT_BOLD, 9, l - 2 * marge)
            canvas.setFont(FONT_BOLD, taille)
            canvas.drawCentredString(x + l / 2, y + h - hauteur_bandeau / 2 - taille / 3, texte_badge)
            chemin_photo = Chemin_photo(collaborateur)
            vertical = h > l
            if vertical:
                cadre_l, cadre_h = l * 0.55, h * 0.42
                photo_x, photo_y = x + (l - cadre_l) / 2, y + h - hauteur_bandeau - 5 * mm - cadre_h
                texte_x, texte_y, largeur_texte, centre = x + l / 2, photo_y - 8 * mm, l - 2 * marge, True
            else:
                cadre_h = h - hauteur_bandeau - 2 * marge
                cadre_l = cadre_h * 0.8
                photo_x, photo_y = x + marge, y + marge
                texte_x, largeur_texte, centre = photo_x + cadre_l + 4 * mm, l - cadre_l - 3 * marge, False
                texte_y = y + (h - hauteur_bandeau) / 2 + (3 * mm if poste else -1 * mm)
            if chemin_photo:
                try:
                    image = ImageReader(chemin_photo)
                    largeur_image, hauteur_image = image.getSize()
                    ratio = min(cadre_l / largeur_image, cadre_h / hauteur_image)
                    lp, hp = largeur_image * ratio, hauteur_image * ratio
                    canvas.drawImage(image, photo_x + (cadre_l - lp) / 2, photo_y + (cadre_h - hp) / 2, lp, hp, mask="auto")
                except Exception:
                    pass
            canvas.setFillColor(colors.black)
            for index, texte in enumerate([collaborateur.prenom or "", collaborateur.nom]):
                taille = Texte_ajuste(texte, FONT_BOLD, 15 if vertical else 13, largeur_texte)
                canvas.setFont(FONT_BOLD, taille)
                position_y = texte_y - index * (taille + 2)
                if centre:
                    canvas.drawCentredString(texte_x, position_y, texte)
                else:
                    canvas.drawString(texte_x, position_y, texte)
            if poste:
                taille = Texte_ajuste(poste, FONT, 9, largeur_texte)
                canvas.setFont(FONT, taille)
                canvas.setFillColor(COULEUR_PRINCIPALE)
                position_y = texte_y - 2 * (17 if vertical else 15)
                if centre:
                    canvas.drawCentredString(texte_x, position_y, poste)
                else:
                    canvas.drawString(texte_x, position_y, poste)

    position = max(1, parametres.get("premiere_position") or 1) - 1
    position = position % par_page
    for collaborateur in collaborateurs:
        for copie in range(parametres.get("nbre_copies") or 1):
            if position >= par_page:
                canvas.showPage()
                position = 0
            colonne, ligne = position % gabarit["colonnes"], position // gabarit["colonnes"]
            x = gabarit["marge_gauche"] * mm + colonne * (l + gabarit["espace_h"] * mm)
            y = hauteur_page - gabarit["marge_haut"] * mm - (ligne + 1) * h - ligne * gabarit["espace_v"] * mm
            canvas.saveState()
            Dessiner(collaborateur, x, y)
            canvas.restoreState()
            position += 1
    canvas.save()
    return JsonResponse({"nom_fichier": nom_fichier})
