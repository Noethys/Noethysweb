# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
from django.db.models import Q, Sum, Count
from xml.sax.saxutils import escape
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import PrelevementsLot, Prelevements, Prestation, Organisateur
from core.utils import utils_dates, utils_impression, utils_texte, utils_polices


class Impression(utils_impression.Impression):
    def Draw(self):
        # Importation du lot et des pièces
        lot = PrelevementsLot.objects.select_related("modele").get(pk=self.dict_donnees["idlot"])
        pieces = Prelevements.objects.select_related("famille", "facture", "mandat").filter(lot=lot).order_by("famille__nom")

        # Importation des prestations
        dict_prestations = {}
        for prestation in Prestation.objects.select_related("activite", "individu", "facture").filter(facture_id__in=[piece.facture_id for piece in pieces]).order_by("individu__prenom"):
            dict_prestations.setdefault(prestation.facture, [])
            dict_prestations[prestation.facture].append(prestation)

        # Préparation du détail des factures
        dict_prestations_piece = {}
        for piece in pieces:
            dict_prestations_piece.setdefault(piece, [])

            dict_prestations_temp = {}
            for prestation in dict_prestations.get(piece.facture, []):
                prix_unitaire = prestation.montant / prestation.quantite
                if prestation.individu:
                    libelle = "%s - %s" % (prestation.individu.prenom or prestation.individu.nom, prestation.label)
                else:
                    libelle = prestation.label
                key = (libelle, prix_unitaire)
                dict_prestations_temp.setdefault(key, {"quantite": 0, "montant": decimal.Decimal(0), "label": prestation.label, "individus": {}})
                dict_prestations_temp[key]["quantite"] += prestation.quantite
                dict_prestations_temp[key]["montant"] += prestation.montant
                if prestation.individu:
                    dict_prestations_temp[key]["individus"][prestation.individu] = True

            keys = list(dict_prestations_temp.keys())
            keys.sort()
            for key in keys:
                dict_prestation = dict_prestations_temp[key]
                dict_prestation.update({"libelle": key[0], "prix": key[1]})
                dict_prestations_piece[piece].append(dict_prestation)

        # Importation des stats du lot
        stats = pieces.aggregate(total=Sum("montant"), nbre=Count("idprelevement"))

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName=utils_polices.FONT_NORMAL, fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName=utils_polices.FONT_NORMAL, alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_titre = ParagraphStyle(name="titre", fontName=utils_polices.FONT_BOLD, alignment=1, fontSize=11, spaceAfter=0, leading=11)

        # Création du titre du document
        self.Insert_header()

        # Tableau de description du lot
        dataTableau = [(
            Paragraph(lot.nom, style_titre),
            Paragraph("<br/>".join((
                "Modèle : %s" % lot.modele.nom,
                "Format : %s" % lot.modele.get_format_display(),
            )), style_defaut),
            Paragraph("<br/>".join((
                "Date : %s" % lot.date.strftime("%d/%m/%Y") if lot.date else "---",
                "Motif : %s" % lot.motif if lot.motif else "---",
            )), style_defaut)
        )]
        tableau = Table(dataTableau, [220, 200, 100])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        self.story.append(tableau)

        # Tableau des totaux du lot
        dataTableau = [(
            Paragraph("Total : <b>%s (%d)</b>" % (utils_texte.Formate_montant(stats["total"]), stats["nbre"]), style_centre),
        )]
        tableau = Table(dataTableau, [520,])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
        ]))
        self.story.append(tableau)

        self.story.append(Spacer(0, 15))

        # Remplissage du tableau
        dataTableau = [("N° Facture", "Famille", "Montant", "Détail", "Qté", "Prix", "Total")]

        for piece in pieces:
            ligne = []

            # N° Facture
            ligne.append(piece.facture.numero if piece.facture else "")

            # Famille
            texte = "%s<br/>%s<br/>%s %s" % (piece.famille, piece.famille.Get_rue_resid() or "", piece.famille.cp_resid or "", piece.famille.ville_resid or "")
            ligne.append(Paragraph(texte, style_defaut))

            # Montant de la facture
            ligne.append(Paragraph(utils_texte.Formate_montant(piece.montant), style_centre))

            # Libellé prestation
            if piece.type == "facture":
                ligne.append(Paragraph("<br/>".join([ligne_detail["libelle"] for ligne_detail in dict_prestations_piece[piece]]), style_defaut))
            else:
                ligne.append(Paragraph(piece.libelle, style_defaut))

            # Quantité
            ligne.append(Paragraph("<br/>".join([str(ligne_detail["quantite"]) for ligne_detail in dict_prestations_piece[piece]]), style_centre))

            # Prix unitaire
            ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["prix"]) for ligne_detail in dict_prestations_piece[piece]]), style_centre))

            # Montant ligne de détail
            ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["montant"]) for ligne_detail in dict_prestations_piece[piece]]), style_centre))

            # Finalisation de la ligne
            dataTableau.append(ligne)

        # Finalisation du tableau
        style = TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTRE"),
        ])
        # Création du tableau
        tableau = Table(dataTableau, [45, 170, 45, 145, 30, 40, 45], repeatRows=1)
        tableau.setStyle(style)
        self.story.append(tableau)

        self.story.append(Spacer(0, 15))

        # Récapitulatif
        lignes_recap = {}
        totaux = {"quantite": 0, "montant": decimal.Decimal(0)}
        for piece, lignes_detail in dict_prestations_piece.items():
            for ligne_detail in lignes_detail:
                key = (ligne_detail["label"], ligne_detail["prix"])
                lignes_recap.setdefault(key, {"quantite": 0, "montant": decimal.Decimal(0), "familles": {}, "individus": {}})
                lignes_recap[key]["quantite"] += ligne_detail["quantite"]
                lignes_recap[key]["montant"] += ligne_detail["montant"]
                lignes_recap[key]["familles"][piece.famille] = True
                lignes_recap[key]["individus"].update(ligne_detail["individus"])
                totaux["quantite"] += ligne_detail["quantite"]
                totaux["montant"] += ligne_detail["montant"]

        keys = list(lignes_recap.keys())
        keys.sort()

        dataTableau = [("Prestation", "Nbre familles", "Nbre individus", "Tarif unitaire", "Quantité", "Total")]
        for key in keys:
            ligne_recap = lignes_recap[key]
            dataTableau.append((
                Paragraph(key[0], style_centre),
                Paragraph(str(len(ligne_recap["familles"])), style_centre),
                Paragraph(str(len(ligne_recap["individus"])), style_centre),
                Paragraph(utils_texte.Formate_montant(key[1]), style_centre),
                Paragraph(str(ligne_recap["quantite"]), style_centre),
                Paragraph(utils_texte.Formate_montant(ligne_recap["montant"]), style_centre),
            ))
        dataTableau.append((
            Paragraph("", style_centre), Paragraph("", style_centre), Paragraph("", style_centre), Paragraph("", style_centre),
            Paragraph("<b>%s</b>" % totaux["quantite"], style_centre), Paragraph("<b>%s</b>" % utils_texte.Formate_montant(totaux["montant"]), style_centre),
        ))
        tableau = Table(dataTableau, [195, 65, 65, 65, 65, 65])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7),
            ("GRID", (0, 0), (-1, -2), 0.25, colors.black),
            ("GRID", (-2, -1), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTRE"),
        ]))
        self.story.append(tableau)



# ---------------------------------------------------------------------------------------------------------------------
#  Documents complémentaires du menu "Imprimer" du lot
# ---------------------------------------------------------------------------------------------------------------------

def E(texte):
    """ Echappe un texte pour l'insérer dans un Paragraph """
    return escape(str(texte)) if texte not in (None, "") else ""


def Masquer_iban(iban=""):
    """ Masque un IBAN : FR76 **** **** 4521 """
    iban = (iban or "").replace(" ", "")
    if len(iban) < 8:
        return iban
    return "%s **** **** %s" % (iban[:4], iban[-4:])


def Formater_iban(iban=""):
    """ Formate un IBAN par blocs de 4 caractères """
    iban = (iban or "").replace(" ", "")
    return " ".join([iban[i:i + 4] for i in range(0, len(iban), 4)])


def Formate_date(date=None):
    return date.strftime("%d/%m/%Y") if date else "---"


LABELS_SEQUENCES = {"OOFF": "Ponctuel (OOFF)", "FRST": "Premier (FRST)", "RCUR": "Récurrent (RCUR)", "FNAL": "Dernier (FNAL)"}


class Impression_base_lot(utils_impression.Impression):
    """ Classe de base des documents imprimables depuis un lot de prélèvements """
    largeur = 520

    def Importation(self):
        self.Importation_styles()
        self.lot = PrelevementsLot.objects.select_related("modele", "modele__compte", "modele__perception").get(pk=self.dict_donnees["idlot"])
        self.pieces = list(Prelevements.objects.select_related("famille", "facture", "mandat", "mandat__individu").filter(lot=self.lot).order_by("famille__nom", "idprelevement"))
        self.organisateur = Organisateur.objects.filter(pk=1).first()
        self.compte = self.lot.modele.compte
        self.perception = self.lot.modele.perception

    def Importation_styles(self):
        # Marges ajustées pour que les paragraphes s'alignent sur les tableaux
        self.doc.leftMargin = self.doc.rightMargin = (self.taille_page[0] - self.largeur) / 2

        # Styles
        self.style_defaut = ParagraphStyle(name="defaut", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=11)
        self.style_petit = ParagraphStyle(name="petit", fontName=utils_polices.FONT_NORMAL, fontSize=7, leading=9)
        self.style_centre = ParagraphStyle(name="centre", parent=self.style_petit, alignment=1)
        self.style_droite = ParagraphStyle(name="droite", parent=self.style_petit, alignment=2)
        self.style_titre_bloc = ParagraphStyle(name="titre_bloc", fontName=utils_polices.FONT_BOLD, fontSize=9, leading=12, spaceAfter=3)
        self.style_titre = ParagraphStyle(name="titre", fontName=utils_polices.FONT_BOLD, fontSize=13, leading=16, alignment=1)
        self.style_total = ParagraphStyle(name="total", fontName=utils_polices.FONT_BOLD, fontSize=11, leading=14, alignment=1)

    def Get_stats_sequences(self, pieces=None):
        """ Renvoie le nombre et le montant des pièces par séquence """
        pieces = self.pieces if pieces is None else pieces
        resultats = []
        for sequence in ("OOFF", "FRST", "RCUR", "FNAL"):
            pieces_sequence = [piece for piece in pieces if piece.sequence == sequence]
            if pieces_sequence:
                resultats.append({"sequence": sequence, "label": LABELS_SEQUENCES[sequence], "pieces": pieces_sequence,
                                  "nbre": len(pieces_sequence), "montant": sum([piece.montant for piece in pieces_sequence], decimal.Decimal(0))})
        return resultats

    def Get_total(self):
        return sum([piece.montant for piece in self.pieces], decimal.Decimal(0))

    def Get_ventilation(self, fonction_cle=None):
        """ Ventile le montant prélevé de chaque pièce sur les prestations de sa facture, au prorata """
        dict_prestations = {}
        for prestation in Prestation.objects.select_related("activite").filter(facture_id__in=[piece.facture_id for piece in self.pieces if piece.facture_id]).order_by("pk"):
            dict_prestations.setdefault(prestation.facture_id, []).append(prestation)

        resultats = {}

        def Ajouter(cle, montant, famille):
            resultats.setdefault(cle, {"montant": decimal.Decimal(0), "familles": set()})
            resultats[cle]["montant"] += montant
            resultats[cle]["familles"].add(famille.pk)

        for piece in self.pieces:
            prestations = dict_prestations.get(piece.facture_id, []) if piece.facture_id else []
            total_prestations = sum([prestation.montant for prestation in prestations], decimal.Decimal(0))
            if not prestations or not total_prestations:
                Ajouter(fonction_cle(None, piece), piece.montant, piece.famille)
                continue
            reste = piece.montant
            for index, prestation in enumerate(prestations):
                if index == len(prestations) - 1:
                    montant = reste
                else:
                    montant = (piece.montant * prestation.montant / total_prestations).quantize(decimal.Decimal("0.01"))
                    reste -= montant
                Ajouter(fonction_cle(prestation, piece), montant, piece.famille)
        return resultats

    def Insert_tableau_sequences(self):
        """ Tableau récapitulatif par séquence """
        dataTableau = [(Paragraph("<b>Séquence</b>", self.style_centre), Paragraph("<b>Nombre d'opérations</b>", self.style_centre), Paragraph("<b>Montant</b>", self.style_centre))]
        for stat in self.Get_stats_sequences():
            dataTableau.append((Paragraph(stat["label"], self.style_centre), Paragraph(str(stat["nbre"]), self.style_centre), Paragraph(utils_texte.Formate_montant(stat["montant"]), self.style_centre)))
        dataTableau.append((Paragraph("<b>Total</b>", self.style_centre), Paragraph("<b>%d</b>" % len(self.pieces), self.style_centre), Paragraph("<b>%s</b>" % utils_texte.Formate_montant(self.Get_total()), self.style_centre)))
        tableau = Table(dataTableau, [220, 150, 150])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), (0.85, 0.85, 0.85)),
            ("BACKGROUND", (0, -1), (-1, -1), (0.93, 0.93, 0.93)),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        self.story.append(tableau)

    def Insert_blocs(self, blocs=[]):
        """ Insère des blocs d'informations côte à côte. blocs = [(titre, [lignes]), ...] """
        largeur_bloc = self.largeur / len(blocs)
        ligne = []
        for titre, lignes in blocs:
            contenu = [Paragraph(titre, self.style_titre_bloc)]
            contenu.extend([Paragraph(texte, self.style_defaut) for texte in lignes if texte])
            ligne.append(contenu)
        tableau = Table([ligne], [largeur_bloc] * len(blocs))
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 12))

    def Insert_signatures(self, signataires=[]):
        """ Zones de signature """
        ligne_lieu = Paragraph("Fait à ..............................................., le ......../......../............", self.style_defaut)
        self.story.append(Spacer(0, 20))
        self.story.append(ligne_lieu)
        self.story.append(Spacer(0, 10))
        largeur_bloc = self.largeur / len(signataires)
        tableau = Table([[Paragraph("<b>%s</b>" % signataire, self.style_defaut) for signataire in signataires]], [largeur_bloc] * len(signataires), rowHeights=[90])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        self.story.append(KeepTogether([tableau]))

    def Insert_infos_lot(self):
        self.Insert_blocs([
            ("Lot de prélèvements", [
                "Nom du lot : <b>%s</b>" % E(self.lot.nom),
                "Motif : %s" % E(self.lot.motif) if self.lot.motif else None,
                "Modèle : %s (%s)" % (E(self.lot.modele.nom), E(self.lot.modele.get_format_display())),
            ]),
            ("Echéance", [
                "Date de prélèvement : <b>%s</b>" % Formate_date(self.lot.date),
                "Nombre d'opérations : <b>%d</b>" % len(self.pieces),
                "Montant total : <b>%s</b>" % utils_texte.Formate_montant(self.Get_total()),
            ]),
        ])


class Impression_etat_nominatif(Impression_base_lot):
    """ Etat nominatif détaillé, par séquence """
    def Draw(self):
        self.Importation()
        self.Insert_header(detail=self.lot.nom)
        self.Insert_infos_lot()

        entetes = ("Famille", "Titulaire du compte", "RUM", "Signature", "IBAN", "Facture", "Statut", "Montant")
        largeurs = [95, 85, 75, 50, 85, 40, 38, 52]

        for stat in self.Get_stats_sequences():
            self.story.append(Paragraph("Séquence %s - %d opération(s) - %s" % (stat["label"], stat["nbre"], utils_texte.Formate_montant(stat["montant"])), self.style_titre_bloc))
            dataTableau = [[Paragraph("<b>%s</b>" % entete, self.style_centre) for entete in entetes]]
            for piece in stat["pieces"]:
                mandat = piece.mandat
                titulaire = mandat.individu.Get_nom() if mandat and mandat.individu else (mandat.individu_nom if mandat else "")
                dataTableau.append((
                    Paragraph(E(piece.famille.nom), self.style_petit),
                    Paragraph(E(titulaire), self.style_petit),
                    Paragraph(E(mandat.rum if mandat else ""), self.style_centre),
                    Paragraph(Formate_date(mandat.date) if mandat else "", self.style_centre),
                    Paragraph(Masquer_iban(mandat.iban if mandat else ""), self.style_centre),
                    Paragraph(E(piece.facture.numero if piece.facture else "Manuel"), self.style_centre),
                    Paragraph(piece.get_statut_display(), self.style_centre),
                    Paragraph(utils_texte.Formate_montant(piece.montant), self.style_droite),
                ))
            dataTableau.append([""] * 6 + [Paragraph("<b>Total</b>", self.style_centre), Paragraph("<b>%s</b>" % utils_texte.Formate_montant(stat["montant"]), self.style_droite)])
            tableau = Table(dataTableau, largeurs, repeatRows=1)
            tableau.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -2), 0.25, colors.black),
                ("GRID", (-2, -1), (-1, -1), 0.25, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), (0.85, 0.85, 0.85)),
            ]))
            self.story.append(tableau)
            self.story.append(Spacer(0, 15))


class Impression_recap_activites(Impression_base_lot):
    """ Récapitulatif des montants prélevés par activité """
    def Draw(self):
        self.Importation()
        self.Insert_header(detail=self.lot.nom)
        self.Insert_infos_lot()

        def Get_cle(prestation, piece):
            if not prestation:
                return "Prélèvements manuels" if piece.type == "manuel" else "Non ventilé"
            return prestation.activite.nom if prestation.activite else "Autres prestations"

        ventilation = self.Get_ventilation(Get_cle)
        total = self.Get_total()

        dataTableau = [[Paragraph("<b>%s</b>" % texte, self.style_centre) for texte in ("Activité", "Nbre familles", "Montant", "Part")]]
        for cle in sorted(ventilation.keys()):
            valeurs = ventilation[cle]
            dataTableau.append((
                Paragraph(E(cle), self.style_petit),
                Paragraph(str(len(valeurs["familles"])), self.style_centre),
                Paragraph(utils_texte.Formate_montant(valeurs["montant"]), self.style_droite),
                Paragraph("%.1f %%" % (valeurs["montant"] * 100 / total) if total else "", self.style_centre),
            ))
        dataTableau.append((Paragraph("<b>Total</b>", self.style_petit), Paragraph("<b>%d</b>" % len({piece.famille_id for piece in self.pieces}), self.style_centre),
                            Paragraph("<b>%s</b>" % utils_texte.Formate_montant(total), self.style_droite), Paragraph("<b>100 %</b>" if total else "", self.style_centre)))
        tableau = Table(dataTableau, [250, 80, 110, 80], repeatRows=1)
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), (0.85, 0.85, 0.85)),
            ("BACKGROUND", (0, -1), (-1, -1), (0.93, 0.93, 0.93)),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 8))
        self.story.append(Paragraph("Le montant prélevé sur chaque facture est réparti au prorata des prestations qui la composent.", self.style_petit))


class Impression_bordereau_banque(Impression_base_lot):
    """ Bordereau de remise à la banque (secteur privé) """
    def Draw(self):
        self.Importation()
        self.Insert_header()
        self.story.append(Paragraph("Bordereau de remise de prélèvements SEPA", self.style_titre))
        self.story.append(Spacer(0, 15))

        adresse = " ".join([texte for texte in (self.compte.adresse_numero, self.compte.adresse_rue) if texte])
        ville = " ".join([texte for texte in (self.compte.adresse_cp, self.compte.adresse_ville) if texte])
        self.Insert_blocs([
            ("Créancier", [
                "<b>%s</b>" % E(self.compte.raison or self.organisateur.nom),
                E(self.compte.adresse_service),
                E(adresse), E(ville),
                "SIRET : %s" % E(self.organisateur.num_siret) if self.organisateur.num_siret else None,
                "ICS : <b>%s</b>" % E(self.compte.code_ics) if self.compte.code_ics else "ICS : non renseigné",
            ]),
            ("Compte à créditer", [
                "<b>%s</b>" % E(self.compte.nom),
                "IBAN : %s" % E(Formater_iban(self.compte.iban)),
                "BIC : %s" % E(self.compte.bic),
            ]),
        ])
        self.Insert_infos_lot()
        self.Insert_tableau_sequences()
        self.Insert_signatures(["Cachet de l'organisme", "Nom, qualité et signature"])


class Impression_bordereau_public(Impression_base_lot):
    """ Bordereau de remise au comptable public (secteur public) """
    def Draw(self):
        self.Importation()
        self.Insert_header()
        self.story.append(Paragraph("Bordereau de remise au comptable public", self.style_titre))
        self.story.append(Spacer(0, 15))

        lignes_comptable = ["Perception non renseignée dans le modèle de prélèvements"]
        if self.perception:
            lignes_comptable = [
                "<b>%s</b>" % E(self.perception.nom),
                E(self.perception.service),
                E(" ".join([texte for texte in (self.perception.numero, self.perception.rue_resid) if texte])),
                E(" ".join([texte for texte in (self.perception.cp_resid, self.perception.ville_resid) if texte])),
            ]
        self.Insert_blocs([
            ("Ordonnateur / Régie", [
                "<b>%s</b>" % E(self.organisateur.nom),
                E(self.organisateur.rue),
                E(" ".join([texte for texte in (self.organisateur.cp, self.organisateur.ville) if texte])),
                "SIRET : %s" % E(self.organisateur.num_siret) if self.organisateur.num_siret else None,
                "ICS : %s" % E(self.compte.code_ics) if self.compte.code_ics else None,
            ]),
            ("Comptable public", lignes_comptable + [
                "Identifiant du service : %s" % E(self.lot.modele.identifiant_service) if self.lot.modele.identifiant_service else None,
                "Poste comptable : %s" % E(self.lot.modele.poste_comptable) if self.lot.modele.poste_comptable else None,
            ]),
        ])
        self.Insert_infos_lot()
        self.Insert_tableau_sequences()
        self.story.append(Spacer(0, 15))

        # Ventilation par imputation comptable
        def Get_cle(prestation, piece):
            if not prestation:
                return ("", "Prélèvements manuels" if piece.type == "manuel" else "Non ventilé")
            code = prestation.code_compta or (prestation.activite.code_comptable if prestation.activite else None) or ""
            return (code, prestation.activite.nom if prestation.activite else "Autres prestations")

        ventilation = self.Get_ventilation(Get_cle)
        self.story.append(Paragraph("Ventilation par imputation", self.style_titre_bloc))
        dataTableau = [[Paragraph("<b>%s</b>" % texte, self.style_centre) for texte in ("Imputation", "Libellé", "Nbre familles", "Montant")]]
        for cle in sorted(ventilation.keys()):
            dataTableau.append((
                Paragraph(E(cle[0]) or "Non renseignée", self.style_centre),
                Paragraph(E(cle[1]), self.style_petit),
                Paragraph(str(len(ventilation[cle]["familles"])), self.style_centre),
                Paragraph(utils_texte.Formate_montant(ventilation[cle]["montant"]), self.style_droite),
            ))
        dataTableau.append(("", "", Paragraph("<b>Total</b>", self.style_centre), Paragraph("<b>%s</b>" % utils_texte.Formate_montant(self.Get_total()), self.style_droite)))
        tableau = Table(dataTableau, [90, 250, 80, 100], repeatRows=1)
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -2), 0.25, colors.black),
            ("GRID", (-2, -1), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), (0.85, 0.85, 0.85)),
        ]))
        self.story.append(tableau)
        self.Insert_signatures(["Le régisseur / l'ordonnateur", "Visa du comptable public"])


class Impression_avis_familles(Impression_base_lot):
    """ Avis de prélèvement (pré-notification SEPA), une page par pièce """
    def Draw(self):
        self.Importation()
        pieces = [piece for piece in self.pieces if piece.statut != "refus"]
        if not pieces:
            self.erreurs.append("Aucun prélèvement à notifier dans ce lot")
            return

        style_lettre = ParagraphStyle(name="lettre", fontName=utils_polices.FONT_NORMAL, fontSize=10, leading=14, spaceAfter=8)
        nom_creancier = self.compte.raison or self.organisateur.nom

        for index, piece in enumerate(pieces):
            if index:
                self.story.append(PageBreak())

            # Expéditeur et destinataire
            expediteur = "<br/>".join([E(texte) for texte in (self.organisateur.nom, self.organisateur.rue, " ".join([t for t in (self.organisateur.cp, self.organisateur.ville) if t])) if texte])
            destinataire = "<br/>".join([E(texte) for texte in (piece.famille.nom, piece.famille.Get_rue_resid(), " ".join([t for t in (piece.famille.cp_resid, piece.famille.ville_resid) if t])) if texte])
            tableau = Table([[Paragraph(expediteur, style_lettre), Paragraph(destinataire, style_lettre)]], [280, 240])
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (1, 0), (1, 0), 60)]))
            self.story.append(tableau)
            self.story.append(Spacer(0, 40))

            self.story.append(Paragraph("<b>Avis de prélèvement SEPA</b>", ParagraphStyle(name="titre_avis", parent=style_lettre, fontSize=13, leading=16)))
            self.story.append(Spacer(0, 10))
            self.story.append(Paragraph("Madame, Monsieur,", style_lettre))
            self.story.append(Paragraph(
                "Conformément au mandat de prélèvement SEPA que vous avez signé, nous vous informons qu'un prélèvement de "
                "<b>%s</b> sera effectué sur votre compte à partir du <b>%s</b>." % (utils_texte.Formate_montant(piece.montant), Formate_date(self.lot.date)), style_lettre))
            self.story.append(Spacer(0, 6))

            mandat = piece.mandat
            if piece.facture:
                objet = "Facture n°%s" % piece.facture.numero
            else:
                objet = piece.libelle or self.lot.motif or ""
            lignes = [
                ("Créancier", nom_creancier),
                ("Identifiant créancier SEPA (ICS)", self.compte.code_ics),
                ("Référence unique du mandat (RUM)", mandat.rum if mandat else ""),
                ("Compte débité", Masquer_iban(mandat.iban if mandat else "")),
                ("Objet", objet),
                ("Montant", utils_texte.Formate_montant(piece.montant)),
                ("Date d'échéance", Formate_date(self.lot.date)),
            ]
            tableau = Table([(Paragraph(E(label), style_lettre), Paragraph("<b>%s</b>" % E(valeur), style_lettre)) for label, valeur in lignes], [200, 320])
            tableau.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), (0.93, 0.93, 0.93)),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            self.story.append(tableau)
            self.story.append(Spacer(0, 14))
            self.story.append(Paragraph("Nous vous remercions de veiller à ce que votre compte soit suffisamment approvisionné à cette date.", style_lettre))
            self.story.append(Paragraph("Veuillez agréer, Madame, Monsieur, nos salutations distinguées.", style_lettre))


# Documents disponibles dans le menu Imprimer : code => (classe, titre)
DOCUMENTS = {
    "liste": (Impression, "Prélèvements"),
    "etat_nominatif": (Impression_etat_nominatif, "Etat nominatif"),
    "recap_activites": (Impression_recap_activites, "Récapitulatif par activité"),
    "bordereau_banque": (Impression_bordereau_banque, "Bordereau de remise"),
    "bordereau_public": (Impression_bordereau_public, "Bordereau de remise"),
    "avis_familles": (Impression_avis_familles, "Avis de prélèvement"),
}
