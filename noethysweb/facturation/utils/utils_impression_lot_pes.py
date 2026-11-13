# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
from django.db.models import Q, Sum, Count
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import PesLot, PesPiece, Prestation, Organisateur
from core.utils import utils_dates, utils_impression, utils_texte, utils_polices


class Impression(utils_impression.Impression):
    def Draw(self):
        # Importation du lot et des pièces
        lot = PesLot.objects.select_related("modele").get(pk=self.dict_donnees["idlot"])
        pieces = PesPiece.objects.select_related("famille", "facture", "prelevement_mandat").filter(lot=lot).order_by("famille__nom")

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
        stats = pieces.aggregate(total=Sum("montant"), nbre=Count("idpiece"),
            total_preleve=Sum("montant", filter=Q(prelevement=True)),
            nbre_preleve=Count("idpiece", filter=Q(prelevement=True)),
            total_non_preleve=Sum("montant", filter=Q(prelevement=False)),
            nbre_non_preleve=Count("idpiece", filter=Q(prelevement=False)),
        )

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
                "Période : %s %s" % (lot.get_mois_display(), lot.exercice),
                "Modèle : %s" % lot.modele.nom,
                "Format : %s" % lot.modele.get_format_display(),
            )), style_defaut),
            Paragraph("<br/>".join((
                "Emission : %s" % lot.date_emission.strftime("%d/%m/%Y") if lot.date_emission else "---",
                "Prélèvement : %s" % lot.date_prelevement.strftime("%d/%m/%Y") if lot.date_prelevement else "---",
                "Envoi : %s" % lot.date_envoi.strftime("%d/%m/%Y") if lot.date_envoi else "---",
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
            Paragraph("Total prélevé : <b>%s (%d)</b>" % (utils_texte.Formate_montant(stats["total_preleve"]), stats["nbre_preleve"]), style_centre),
            Paragraph("Total non-prélevé : <b>%s (%d)</b>" % (utils_texte.Formate_montant(stats["total_non_preleve"]), stats["nbre_non_preleve"]), style_centre),
        )]
        tableau = Table(dataTableau, [173, 174, 173])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
        ]))
        self.story.append(tableau)

        self.story.append(Spacer(0, 15))

        # Remplissage du tableau
        dataTableau = [("N° Facture", "Famille", "Montant", "P", "Détail", "Qté", "Prix", "Total")]

        for piece in pieces:
            ligne = []

            # N° Facture
            ligne.append(piece.facture.numero)

            # Famille
            texte = "%s<br/>%s<br/>%s %s" % (
                piece.famille.facturation_nom or piece.famille,
                piece.famille.facturation_rue_resid or piece.famille.Get_rue_resid() or "",
                piece.famille.facturation_cp_resid or piece.famille.cp_resid or "",
                piece.famille.facturation_ville_resid or piece.famille.ville_resid or ""
            )
            ligne.append(Paragraph(texte, style_defaut))

            # Montant de la facture
            ligne.append(Paragraph(utils_texte.Formate_montant(piece.montant), style_centre))

            # Prélevé
            ligne.append(Paragraph("P" if piece.prelevement else "", style_centre))

            # Libellé prestation
            ligne.append(Paragraph("<br/>".join([ligne_detail["libelle"] for ligne_detail in dict_prestations_piece[piece]]), style_defaut))

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
        tableau = Table(dataTableau, [45, 150, 45, 20, 145, 30, 40, 45], repeatRows=1)
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

        # Légende
        self.story.append(Spacer(0, 5))
        self.story.append(Paragraph("Colonne P = Prélèvement actif", style_centre))



# ---------------------------------------------------------------------------------------------------------------------
#  Documents complémentaires du menu "Imprimer" de l'export
# ---------------------------------------------------------------------------------------------------------------------

from facturation.utils.utils_impression_lot_prelevements import Impression_base_lot, E, Masquer_iban, Formate_date, LABELS_SEQUENCES

SEUIL_RECOUVREMENT = decimal.Decimal("15.00")


class Impression_base_pes(Impression_base_lot):
    """ Classe de base des documents imprimables depuis un export vers le Trésor public """

    def Importation(self):
        super().Importation_styles()
        self.lot = PesLot.objects.select_related("modele", "modele__compte").get(pk=self.dict_donnees["idlot"])
        self.pieces = list(PesPiece.objects.select_related(
            "famille", "facture", "prelevement_mandat", "prelevement_mandat__individu", "titulaire_helios", "famille__titulaire_helios"
        ).filter(lot=self.lot).order_by("idpiece"))
        self.organisateur = Organisateur.objects.filter(pk=1).first()
        self.modele = self.lot.modele

    def Get_debiteur(self, piece):
        titulaire = piece.titulaire_helios or piece.famille.titulaire_helios
        return titulaire.Get_nom() if titulaire else piece.famille.nom

    def Get_objet(self, piece):
        if piece.facture:
            return "Facture n°%s" % piece.facture.numero
        return "Pièce manuelle"

    def Get_cle_imputation(self, prestation, piece):
        """ Même logique de recherche des codes que l'export (utils_export_tresor_public.Get_detail_pieces) """
        id_poste, code_prodloc = self.modele.id_poste, self.modele.code_prodloc
        if not prestation:
            return (id_poste or "", code_prodloc or "", "Pièces manuelles" if piece.type == "manuel" else "Non ventilé")
        if prestation.activite:
            if prestation.activite.code_comptable: id_poste = prestation.activite.code_comptable
            if prestation.activite.code_produit_local: code_prodloc = prestation.activite.code_produit_local
        if prestation.code_compta: id_poste = prestation.code_compta
        if prestation.code_produit_local: code_prodloc = prestation.code_produit_local
        return (id_poste or "", code_prodloc or "", prestation.activite.nom if prestation.activite else "Autres prestations")

    def Insert_infos_lot(self):
        preleves = [piece for piece in self.pieces if piece.prelevement]
        self.Insert_blocs([
            ("Export", [
                "Nom de l'export : <b>%s</b>" % E(self.lot.nom),
                "Période : %s %s" % (E(self.lot.get_mois_display()), self.lot.exercice),
                "Modèle : %s (%s)" % (E(self.modele.nom), E(self.modele.get_format_display())),
            ]),
            ("Dates", [
                "Emission : <b>%s</b>" % Formate_date(self.lot.date_emission),
                "Prélèvement : %s" % Formate_date(self.lot.date_prelevement),
                "Envoi : %s" % Formate_date(self.lot.date_envoi),
            ]),
            ("Totaux", [
                "Total : <b>%s (%d)</b>" % (utils_texte.Formate_montant(self.Get_total()), len(self.pieces)),
                "Prélevé : %s (%d)" % (utils_texte.Formate_montant(sum([p.montant for p in preleves], decimal.Decimal(0))), len(preleves)),
                "Non prélevé : %s (%d)" % (utils_texte.Formate_montant(sum([p.montant for p in self.pieces if not p.prelevement], decimal.Decimal(0))), len(self.pieces) - len(preleves)),
            ]),
        ])

    def Insert_tableau(self, entetes=[], lignes=[], largeurs=[], ligne_total=None, alignements=None):
        """ Tableau standard avec entête grisée et ligne de total optionnelle """
        alignements = alignements or ["G"] * len(entetes)
        styles = {"G": self.style_petit, "C": self.style_centre, "D": self.style_droite}
        dataTableau = [[Paragraph("<b>%s</b>" % entete, self.style_centre) for entete in entetes]]
        for ligne in lignes:
            dataTableau.append([Paragraph(str(valeur), styles[alignements[index]]) for index, valeur in enumerate(ligne)])
        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), (0.85, 0.85, 0.85)),
        ]
        if ligne_total:
            dataTableau.append([Paragraph("<b>%s</b>" % valeur, styles[alignements[index]]) if valeur != "" else "" for index, valeur in enumerate(ligne_total)])
            style += [("GRID", (0, 0), (-1, -2), 0.25, colors.black), ("BOX", (0, -1), (-1, -1), 0.25, colors.black), ("BACKGROUND", (0, -1), (-1, -1), (0.93, 0.93, 0.93))]
        else:
            style.append(("GRID", (0, 0), (-1, -1), 0.25, colors.black))
        tableau = Table(dataTableau, largeurs, repeatRows=1)
        tableau.setStyle(TableStyle(style))
        self.story.append(tableau)


class Impression_recap_imputations(Impression_base_pes):
    """ Récapitulatif des montants par imputation comptable """
    def Draw(self):
        self.Importation()
        self.Insert_header(detail=self.lot.nom)
        self.Insert_infos_lot()

        ventilation = self.Get_ventilation(self.Get_cle_imputation)
        lignes = []
        for cle in sorted(ventilation.keys()):
            id_poste, code_prodloc, libelle = cle
            lignes.append((E(id_poste) or "-", E(code_prodloc) or "-", E(libelle), len(ventilation[cle]["familles"]), utils_texte.Formate_montant(ventilation[cle]["montant"])))
        self.Insert_tableau(
            entetes=("Imputation", "Code produit", "Activité", "Nbre familles", "Montant"),
            lignes=lignes, largeurs=[80, 80, 220, 65, 75], alignements=["C", "C", "G", "C", "D"],
            ligne_total=("", "", "Total", len({piece.famille_id for piece in self.pieces}), utils_texte.Formate_montant(self.Get_total())),
        )

        # Sous-totaux par imputation seule
        sous_totaux = {}
        for (id_poste, code_prodloc, libelle), valeurs in ventilation.items():
            sous_totaux.setdefault((id_poste, code_prodloc), decimal.Decimal(0))
            sous_totaux[(id_poste, code_prodloc)] += valeurs["montant"]
        if 1 < len(sous_totaux) < len(ventilation):
            self.story.append(Spacer(0, 15))
            self.story.append(Paragraph("Totaux par imputation", self.style_titre_bloc))
            self.Insert_tableau(
                entetes=("Imputation", "Code produit", "Montant"),
                lignes=[(E(cle[0]) or "-", E(cle[1]) or "-", utils_texte.Formate_montant(montant)) for cle, montant in sorted(sous_totaux.items())],
                largeurs=[150, 150, 220], alignements=["C", "C", "D"],
            )
        self.story.append(Spacer(0, 8))
        self.story.append(Paragraph("Les codes sont recherchés comme lors de la génération du fichier : prestation, puis activité, puis modèle d'export. "
                                    "Le montant de chaque pièce est réparti au prorata des prestations de sa facture.", self.style_petit))


class Impression_bordereau_titres(Impression_base_pes):
    """ Bordereau des titres de recettes à signer par l'ordonnateur """
    def Draw(self):
        self.Importation()
        self.Insert_header()
        numero = " n°%s" % self.lot.id_bordereau if self.lot.id_bordereau else ""
        self.story.append(Paragraph("Bordereau des titres de recettes%s" % E(numero), self.style_titre))
        self.story.append(Spacer(0, 15))

        nom_collectivite = (self.modele.nom_collectivite or "{NOM_ORGANISATEUR}").replace("{NOM_ORGANISATEUR}", self.organisateur.nom or "")
        self.Insert_blocs([
            ("Collectivité", [
                "<b>%s</b>" % E(nom_collectivite),
                "SIRET : %s" % E(self.organisateur.num_siret) if self.organisateur.num_siret else None,
                "Code collectivité : %s" % E(self.modele.code_collectivite) if self.modele.code_collectivite else None,
                "Code budget : %s" % E(self.modele.code_budget) if self.modele.code_budget else None,
                "Poste comptable : %s" % E(self.modele.id_poste) if self.modele.id_poste else None,
            ]),
            ("Bordereau", [
                "Exercice : <b>%s</b>" % self.lot.exercice,
                "Export : %s" % E(self.lot.nom),
                "Période : %s %s" % (E(self.lot.get_mois_display()), self.lot.exercice),
                "Date d'émission : <b>%s</b>" % Formate_date(self.lot.date_emission),
            ]),
        ])

        # Liste des titres
        lignes = [(piece.pk, E(self.Get_debiteur(piece)), E(self.Get_objet(piece)), "P" if piece.prelevement else "", utils_texte.Formate_montant(piece.montant)) for piece in self.pieces]
        total = self.Get_total()
        self.Insert_tableau(
            entetes=("N° pièce", "Débiteur", "Objet", "Prél.", "Montant"),
            lignes=lignes, largeurs=[55, 190, 170, 35, 70], alignements=["C", "G", "G", "C", "D"],
            ligne_total=("", "Total (%d titre%s)" % (len(self.pieces), "s" if len(self.pieces) > 1 else ""), "", "", utils_texte.Formate_montant(total)),
        )
        self.story.append(Spacer(0, 12))

        # Cumul de l'exercice : exports précédents du même exercice et du même budget
        lots_precedents = PesLot.objects.filter(exercice=self.lot.exercice, modele__code_budget=self.modele.code_budget).filter(
            Q(date_emission__lt=self.lot.date_emission) | Q(date_emission=self.lot.date_emission, pk__lt=self.lot.pk))
        total_precedent = PesPiece.objects.filter(lot__in=lots_precedents).aggregate(total=Sum("montant"))["total"] or decimal.Decimal(0)
        dataTableau = [
            ("Total des bordereaux précédents de l'exercice", utils_texte.Formate_montant(total_precedent)),
            ("Total du présent bordereau", utils_texte.Formate_montant(total)),
            ("Total cumulé de l'exercice", utils_texte.Formate_montant(total_precedent + total)),
        ]
        tableau = Table([[Paragraph(E(a), self.style_defaut), Paragraph("<b>%s</b>" % b, ParagraphStyle(name="d", parent=self.style_defaut, alignment=2))] for a, b in dataTableau], [370, 150])
        tableau.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, -1), (-1, -1), (0.93, 0.93, 0.93))]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 15))

        self.story.append(Paragraph(
            "Certifié exécutoire le présent bordereau comprenant <b>%d</b> titre%s de recettes pour un montant total de <b>%s</b>." % (
                len(self.pieces), "s" if len(self.pieces) > 1 else "", utils_texte.Formate_montant(total)), self.style_defaut))
        self.Insert_signatures(["L'ordonnateur (nom, qualité, signature)", "Pris en charge par le comptable public"])


class Impression_etat_prelevements(Impression_base_pes):
    """ Etat des prélèvements de l'export """
    def Draw(self):
        self.Importation()
        self.Insert_header(detail=self.lot.nom)
        self.Insert_infos_lot()

        preleves = [piece for piece in self.pieces if piece.prelevement]
        non_preleves = [piece for piece in self.pieces if not piece.prelevement]
        preleves.sort(key=lambda piece: self.Get_debiteur(piece))
        non_preleves.sort(key=lambda piece: self.Get_debiteur(piece))

        # Synthèse
        lignes = []
        for sequence in ("OOFF", "FRST", "RCUR", "FNAL", None):
            pieces = [piece for piece in preleves if (piece.prelevement_sequence or None) == sequence]
            if pieces:
                lignes.append(("Prélevés - %s" % (LABELS_SEQUENCES[sequence] if sequence else "séquence non définie"), len(pieces), utils_texte.Formate_montant(sum([p.montant for p in pieces], decimal.Decimal(0)))))
        lignes.append(("Non prélevés", len(non_preleves), utils_texte.Formate_montant(sum([p.montant for p in non_preleves], decimal.Decimal(0)))))
        self.Insert_tableau(entetes=("", "Nombre", "Montant"), lignes=lignes, largeurs=[280, 100, 140], alignements=["G", "C", "D"],
                            ligne_total=("Total", len(self.pieces), utils_texte.Formate_montant(self.Get_total())))
        self.story.append(Spacer(0, 15))

        # Détail des prélèvements
        if preleves:
            self.story.append(Paragraph("Détail des prélèvements - prélevés le %s" % Formate_date(self.lot.date_prelevement), self.style_titre_bloc))
            lignes = []
            for piece in preleves:
                mandat = piece.prelevement_mandat
                lignes.append((
                    E(self.Get_debiteur(piece)), E(self.Get_objet(piece)), E(mandat.rum) if mandat else "<font color='red'>Aucun mandat</font>",
                    Masquer_iban(mandat.iban) if mandat else "", piece.prelevement_sequence or "", piece.get_prelevement_statut_display(), utils_texte.Formate_montant(piece.montant)))
            self.Insert_tableau(
                entetes=("Débiteur", "Objet", "RUM", "IBAN", "Séq.", "Statut", "Montant"),
                lignes=lignes, largeurs=[115, 80, 80, 90, 35, 50, 70], alignements=["G", "G", "C", "C", "C", "C", "D"],
                ligne_total=("", "", "", "", "", "Total", utils_texte.Formate_montant(sum([p.montant for p in preleves], decimal.Decimal(0)))),
            )
            self.story.append(Spacer(0, 15))

        # Titres à payer hors prélèvement
        if non_preleves:
            self.story.append(Paragraph("Titres à payer hors prélèvement", self.style_titre_bloc))
            self.Insert_tableau(
                entetes=("N° pièce", "Débiteur", "Objet", "Montant"),
                lignes=[(piece.pk, E(self.Get_debiteur(piece)), E(self.Get_objet(piece)), utils_texte.Formate_montant(piece.montant)) for piece in non_preleves],
                largeurs=[60, 220, 160, 80], alignements=["C", "G", "G", "D"],
                ligne_total=("", "", "Total", utils_texte.Formate_montant(sum([p.montant for p in non_preleves], decimal.Decimal(0)))),
            )


class Impression_controle(Impression_base_pes):
    """ Rapport de contrôle avant l'envoi du fichier """
    def Draw(self):
        self.Importation()
        self.Insert_header(detail=self.lot.nom)

        anomalies = []

        # Paramètres de l'export
        for champ, label in (("code_collectivite", "Code collectivité"), ("code_budget", "Code budget"), ("id_poste", "Poste comptable par défaut"), ("code_prodloc", "Code produit local par défaut")):
            if not getattr(self.modele, champ):
                anomalies.append(("bloquant" if self.modele.format == "pes" else "verifier", "Modèle d'export", "Le paramètre '%s' n'est pas renseigné" % label))
        if not self.organisateur.num_siret:
            anomalies.append(("bloquant", "Organisateur", "Le SIRET de l'organisateur n'est pas renseigné"))
        if not self.lot.id_bordereau:
            anomalies.append(("verifier", "Export", "L'identifiant du bordereau n'est pas renseigné"))
        if not self.pieces:
            anomalies.append(("bloquant", "Export", "L'export ne contient aucune pièce"))

        # Pièces
        for piece in self.pieces:
            debiteur = self.Get_debiteur(piece)
            titulaire = piece.titulaire_helios or piece.famille.titulaire_helios
            if not titulaire:
                anomalies.append(("bloquant", debiteur, "Aucun titulaire Hélios n'est défini pour la famille"))
            else:
                manquants = [label for valeur, label in ((titulaire.rue_resid, "rue"), (titulaire.cp_resid, "code postal"), (titulaire.ville_resid, "ville")) if not valeur]
                if manquants:
                    anomalies.append(("verifier", debiteur, "Adresse du titulaire Hélios incomplète (%s)" % ", ".join(manquants)))
            if not piece.famille.cattiers_helios:
                anomalies.append(("bloquant", debiteur, "La catégorie de tiers Hélios n'est pas renseignée"))
            if piece.type == "facture" and not piece.facture:
                anomalies.append(("bloquant", debiteur, "La pièce n'est rattachée à aucune facture"))
            if piece.montant <= 0:
                anomalies.append(("bloquant", debiteur, "Montant nul ou négatif (%s)" % utils_texte.Formate_montant(piece.montant)))
            elif piece.montant < SEUIL_RECOUVREMENT:
                anomalies.append(("verifier", debiteur, "Montant inférieur au seuil de mise en recouvrement de %s (%s)" % (utils_texte.Formate_montant(SEUIL_RECOUVREMENT), utils_texte.Formate_montant(piece.montant))))
            if piece.prelevement:
                mandat = piece.prelevement_mandat
                if not mandat:
                    anomalies.append(("bloquant", debiteur, "Prélèvement demandé sans mandat"))
                elif not mandat.actif:
                    anomalies.append(("bloquant", debiteur, "Prélèvement demandé avec un mandat inactif (RUM %s)" % mandat.rum))
                if not piece.prelevement_sequence:
                    anomalies.append(("bloquant", debiteur, "La séquence du prélèvement n'est pas définie"))
                if piece.prelevement_statut == "refus":
                    anomalies.append(("verifier", debiteur, "Le prélèvement est au statut 'Refus'"))

        # Synthèse
        nbre_bloquants = len([a for a in anomalies if a[0] == "bloquant"])
        nbre_verifier = len(anomalies) - nbre_bloquants
        if not anomalies:
            texte = "<font color='#3B6D11'><b>Aucune anomalie détectée</b></font> sur les %d pièce(s) de l'export." % len(self.pieces)
        else:
            texte = "<b>%d anomalie(s) bloquante(s)</b> et <b>%d point(s) à vérifier</b> sur les %d pièce(s) de l'export." % (nbre_bloquants, nbre_verifier, len(self.pieces))
        self.story.append(Paragraph(texte, ParagraphStyle(name="synthese", parent=self.style_defaut, fontSize=10, leading=14)))
        self.story.append(Spacer(0, 12))

        if anomalies:
            anomalies.sort(key=lambda a: (a[0] != "bloquant", a[1]))
            labels = {"bloquant": "<font color='#A32D2D'><b>Bloquant</b></font>", "verifier": "<font color='#854F0B'>A vérifier</font>"}
            self.Insert_tableau(
                entetes=("Gravité", "Concerne", "Anomalie"),
                lignes=[(labels[gravite], E(concerne), E(texte)) for gravite, concerne, texte in anomalies],
                largeurs=[70, 150, 300], alignements=["C", "G", "G"],
            )
            self.story.append(Spacer(0, 8))
            self.story.append(Paragraph("Les anomalies bloquantes empêchent la génération du fichier ou entraînent un rejet du flux par la DGFiP.", self.style_petit))


# Documents disponibles dans le menu Imprimer : code => (classe, titre)
DOCUMENTS = {
    "liste": (Impression, "Edition d'un export"),
    "recap_imputations": (Impression_recap_imputations, "Récapitulatif par imputation"),
    "bordereau_titres": (Impression_bordereau_titres, "Bordereau de titres"),
    "etat_prelevements": (Impression_etat_prelevements, "Etat des prélèvements"),
    "controle": (Impression_controle, "Rapport de contrôle"),
}
