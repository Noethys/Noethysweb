# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, decimal
from xml.dom.minidom import Document
from core.utils import utils_texte
from facturation.utils.utils_export_tresor_public import ExporterBase


class Exporter(ExporterBase):
    """ Export vers Corail de Cosoluce (fichier XML ImportCosoluce + pièces jointes PDF dans un ZIP) """
    code_format = "corail"

    def Ajouter(self, parent, nom, valeur=None):
        """ Crée un élément avec un attribut V (si valeur fournie) et l'ajoute au parent """
        element = self.doc.createElement(nom)
        if valeur is not None:
            element.setAttribute("V", "%s" % valeur)
        parent.appendChild(element)
        return element

    def Get_civilite(self, individu):
        civilite = individu.Get_abrege_civilite()
        if civilite == "M.": return "Mr"
        if civilite in ("Mme", "Melle"): return "Mme"
        return None

    def Get_adresse_titulaire(self, piece):
        titulaire = piece.famille.titulaire_helios
        rue = piece.famille.facturation_rue_resid or titulaire.rue_resid or ""
        cp = piece.famille.facturation_cp_resid or titulaire.cp_resid or ""
        ville = piece.famille.facturation_ville_resid or titulaire.ville_resid or ""
        return rue, cp, ville

    def Ajouter_identite(self, parent, individu, suffixe=""):
        """ Ajoute le bloc d'identité d'un tiers (titulaire ou tiers solidaire) """
        nom = self.ConvertToTexte(individu.nom or "", majuscules=True)[:38]
        prenom = self.ConvertToTexte(individu.prenom or "", majuscules=True)[:38]
        self.Ajouter(parent, "CatTiers%s" % suffixe, "%02d" % (self.piece.famille.cattiers_helios or 1))
        self.Ajouter(parent, "NatJur%s" % suffixe, "%02d" % (self.piece.famille.natjur_helios or 1))
        self.Ajouter(parent, "TypeTiers%s" % suffixe, "D")
        civilite = self.Get_civilite(individu)
        if civilite:
            self.Ajouter(parent, "Civilite%s" % suffixe, civilite)
        self.Ajouter(parent, "RaisonSociale%s" % suffixe, ("%s %s" % (nom, prenom)).strip())
        self.Ajouter(parent, "Nom%s" % suffixe, nom)
        if prenom:
            self.Ajouter(parent, "Prenom%s" % suffixe, prenom)

    def Get_imputations(self, piece, codes_facture=None):
        """ Retourne les imputations comptables de la pièce. Leur total est toujours égal au montant de la pièce
            (solde de la facture), même si la facture a déjà été partiellement réglée. """
        modele = self.lot.modele
        imputations = {key: montant for key, montant in (codes_facture or {}).items() if montant}
        if not imputations:
            return {(modele.id_poste, modele.code_prodloc, modele.service1, modele.service2): piece.montant}

        # Si le total des prestations diffère du montant de la pièce, on répartit le montant de la pièce au prorata
        total = sum(imputations.values())
        if total == piece.montant:
            return imputations
        if total <= 0:
            key = max(imputations, key=lambda k: imputations[k])
            return {key: piece.montant}
        resultat, cumul = {}, decimal.Decimal(0)
        keys = sorted(imputations, key=lambda k: imputations[k])
        for key in keys[:-1]:
            montant = (piece.montant * imputations[key] / total).quantize(decimal.Decimal("0.01"))
            resultat[key] = montant
            cumul += montant
        resultat[keys[-1]] = piece.montant - cumul
        return resultat

    def Creation_fichiers(self):
        modele = self.lot.modele

        # Vérifications
        if not self.pieces:
            self.erreurs.append("Vous devez ajouter au moins une pièce.")
        for piece in self.pieces:
            if not piece.famille.titulaire_helios:
                self.erreurs.append("Aucun titulaire Hélios pour la famille %s." % piece.famille.nom)
                continue
            if piece.montant <= 0:
                self.erreurs.append("Le montant de la pièce de la famille %s doit être supérieur à zéro." % piece.famille.nom)
            rue, cp, ville = self.Get_adresse_titulaire(piece)
            if not rue or not cp or not ville:
                self.erreurs.append("Adresse incomplète pour %s (famille %s)." % (piece.famille.titulaire_helios.Get_nom(), piece.famille.nom))
            if piece.prelevement and not piece.prelevement_mandat:
                self.erreurs.append("Aucun mandat de prélèvement pour la famille %s." % piece.famille.nom)
        if self.erreurs:
            return False

        # Génération des pièces jointes
        dict_pieces_jointes = {}
        if modele.inclure_pieces_jointes:
            dict_pieces_jointes = self.Generation_pieces_jointes()
            if not dict_pieces_jointes:
                self.erreurs.append("Les factures au format PDF n'ont pas pu être générées.")
                return False

        # Récupération du détail des factures
        detail_factures, dict_prestations_factures = self.Get_detail_pieces()
        dict_codes = self.Get_dict_codes(dict_prestations_factures=dict_prestations_factures)

        date_emission = self.lot.date_emission.strftime("%Y%m%d")
        objet_dette = self.ConvertToTexte(self.Formate_libelle(texte=modele.objet_dette or ""), majuscules=True)

        # Génération du document XML
        self.doc = Document()
        racine = self.Ajouter(self.doc, "ImportCosoluce")

        # Information
        information = self.Ajouter(racine, "Information")
        self.Ajouter(information, "NomCollectivite", self.ConvertToTexte(self.Formate_libelle(texte=modele.nom_collectivite or "{NOM_ORGANISATEUR}")))
        self.Ajouter(information, "Exercice", self.lot.exercice)
        self.Ajouter(information, "Origine", "Noethys")
        self.Ajouter(information, "DateFichier", date_emission)
        self.Ajouter(information, "InfoComplementaire", objet_dette)

        # TypePieceImport
        type_piece_import = self.Ajouter(racine, "TypePieceImport")
        self.Ajouter(type_piece_import, "TypePiece", "Pièce EnCours")
        self.Ajouter(type_piece_import, "Sens", "R")

        for piece in self.pieces:
            self.piece = piece
            titulaire = piece.famille.titulaire_helios
            objet_piece = self.ConvertToTexte(self.Formate_libelle(texte=modele.objet_piece, piece=piece), majuscules=True)[:160]

            element_piece = self.Ajouter(type_piece_import, "Piece")

            # InfoPiece
            info_piece = self.Ajouter(element_piece, "InfoPiece")
            self.Ajouter(info_piece, "TypeSerieBordereau", "N")
            self.Ajouter(info_piece, "TypeEcriture", "R")
            self.Ajouter(info_piece, "TrainPiece", "Facturation")

            # Tiers
            tiers = self.Ajouter(info_piece, "Tiers")
            self.Ajouter_identite(self.Ajouter(tiers, "InfoTiers"), titulaire)
            rue, cp, ville = self.Get_adresse_titulaire(piece)
            adresse = self.Ajouter(tiers, "Adresse")
            self.Ajouter(adresse, "AdresseEtranger", "N")
            self.Ajouter(adresse, "Rue", self.ConvertToTexte(rue, majuscules=True)[:38])
            self.Ajouter(adresse, "CP", self.ConvertToTexte(cp)[:5])
            self.Ajouter(adresse, "Ville", self.ConvertToTexte(ville, majuscules=True)[:38])

            # Références bancaires
            ref_bancaire = self.Ajouter(info_piece, "RefBancaire")
            if piece.prelevement:
                mandat = piece.prelevement_mandat
                iban = (mandat.iban or "").replace(" ", "").upper()
                self.Ajouter(ref_bancaire, "Banque", "")
                self.Ajouter(ref_bancaire, "BanqueEtrangere", "N" if iban.startswith("FR") else "O")
                self.Ajouter(ref_bancaire, "Titulaire", self.ConvertToTexte(mandat.individu_nom or (mandat.individu.Get_nom() if mandat.individu else ""), majuscules=True)[:32])
                if iban.startswith("FR") and len(iban) == 27:
                    self.Ajouter(ref_bancaire, "CodeBanque", iban[4:9])
                    self.Ajouter(ref_bancaire, "CodeGuichet", iban[9:14])
                    self.Ajouter(ref_bancaire, "NumeroCompte", iban[14:25])
                    self.Ajouter(ref_bancaire, "CleRib", iban[25:27])
                self.Ajouter(ref_bancaire, "IBAN", iban)
                self.Ajouter(ref_bancaire, "BIC", (mandat.bic or "").upper())

            # Tiers solidaire
            tiers_solidaire = piece.famille.tiers_solidaire
            if modele.inclure_tiers_solidaires and tiers_solidaire:
                element_ts = self.Ajouter(info_piece, "TiersSolidaire")
                self.Ajouter_identite(self.Ajouter(element_ts, "InfoTiersSolidaire"), tiers_solidaire, suffixe="TiersSolidaire")
                adresse_ts = self.Ajouter(element_ts, "AdresseTiersSolidaire")
                self.Ajouter(adresse_ts, "AdresseEtrangerTiersSolidaire", "N")
                self.Ajouter(adresse_ts, "RueTiersSolidaire", self.ConvertToTexte(tiers_solidaire.rue_resid or "", majuscules=True)[:38])
                self.Ajouter(adresse_ts, "CPTiersSolidaire", self.ConvertToTexte(tiers_solidaire.cp_resid or "")[:5])
                self.Ajouter(adresse_ts, "VilleTiersSolidaire", self.ConvertToTexte(tiers_solidaire.ville_resid or "", majuscules=True)[:38])

            # Informations de la pièce
            self.Ajouter(info_piece, "DatePiece", date_emission)
            self.Ajouter(info_piece, "Objet", objet_piece)
            self.Ajouter(info_piece, "LibPieceJustificative", objet_piece)
            self.Ajouter(info_piece, "TypePiecePES", "01")
            self.Ajouter(info_piece, "NaturePiecePES", "01")
            self.Ajouter(info_piece, "PesASAP", "01")

            # En-tête ASAP
            entete_asap = self.Ajouter(info_piece, "ASAPEnteteFacturation")
            self.Ajouter(entete_asap, "ASAPObjet", objet_dette)
            self.Ajouter(entete_asap, "ASAPDateDebut", self.date_min_lot.strftime("%Y%m%d"))
            self.Ajouter(entete_asap, "ASAPDateFin", self.date_max_lot.strftime("%Y%m%d"))

            # Pièce jointe
            pj = dict_pieces_jointes.get(piece.facture_id)
            if pj:
                element_pj = self.Ajouter(element_piece, "PJ")
                self.Ajouter(element_pj, "NomPJ", pj["NomPJ"])
                self.Ajouter(element_pj, "IDPJInterne", pj["IdUnique"])
                self.Ajouter(element_pj, "CheminRelatif", "PJ\\")
                self.Ajouter(element_pj, "TransmettreAHelios", "O")

            # Prélèvement
            if piece.prelevement:
                if piece.prelevement_sequence == "FRST": sequence = "02"
                elif piece.prelevement_sequence == "RCUR": sequence = "03"
                elif piece.prelevement_sequence == "FNAL": sequence = "04"
                else: sequence = "01"
                prelevement = self.Ajouter(element_piece, "Prelevement")
                self.Ajouter(prelevement, "NaturePrelevement", "01")
                self.Ajouter(prelevement, "PeriodicitePrelevement", "07")
                self.Ajouter(prelevement, "DatePrelevement", self.lot.date_prelevement.strftime("%Y%m%d"))
                self.Ajouter(prelevement, "SequencePrelevement", sequence)
                self.Ajouter(prelevement, "RUM", piece.prelevement_mandat.rum)
                self.Ajouter(prelevement, "DateRUM", piece.prelevement_mandat.date.strftime("%Y%m%d"))
                self.Ajouter(prelevement, "LibPrelevement", self.ConvertToTexte(self.Formate_libelle(texte=modele.prelevement_libelle, piece=piece), majuscules=True)[:140])
                for nom in ("AncienRUM", "AncienICS", "AncienCreancier"):
                    self.Ajouter(prelevement, nom, "")
                self.Ajouter(prelevement, "ChangementBanque", "N")
                self.Ajouter(prelevement, "AncienIBAN", "")
                self.Ajouter(prelevement, "TitulaireDifferent", "N")

            # Lignes de la pièce (une ligne par imputation comptable)
            imputations = self.Get_imputations(piece, dict_codes.get(piece.facture))
            for (id_poste, code_prodloc, service1, service2), montant in imputations.items():
                ligne_piece = self.Ajouter(element_piece, "LignePiece")
                self.Ajouter(ligne_piece, "Article", (id_poste or "")[:10])
                self.Ajouter(ligne_piece, "Fonction", modele.fonction or "")
                if service1:
                    self.Ajouter(ligne_piece, "CodeAnalytique1", service1)
                if service2:
                    self.Ajouter(ligne_piece, "CodeAnalytique2", service2)
                self.Ajouter(ligne_piece, "MontantHT", decimal.Decimal(montant).quantize(decimal.Decimal("0.01")))
                self.Ajouter(ligne_piece, "CodeProduit", (code_prodloc or "")[:4])

            # Détail ASAP
            if modele.inclure_detail:
                lignes_asap = []
                for dict_detail in detail_factures.get(piece.facture, []):
                    montant_unitaire = decimal.Decimal(dict_detail["montant"])
                    lignes_asap.append((self.ConvertToTexte(dict_detail["libelle"])[:200], dict_detail["quantite"], montant_unitaire.quantize(decimal.Decimal("0.01")),
                                        (montant_unitaire * dict_detail["quantite"]).quantize(decimal.Decimal("0.01"))))

                # Facture partiellement réglée : ajout d'une ligne négative pour que le détail corresponde au montant dû
                ecart = piece.montant - sum([ligne[3] for ligne in lignes_asap], decimal.Decimal(0))
                if lignes_asap and ecart:
                    lignes_asap.append(("Déjà réglé" if ecart < 0 else "Ajustement", 1, ecart, ecart))

                for libelle, quantite, prix_unitaire, montant_total in lignes_asap:
                    ligne_asap = self.Ajouter(element_piece, "ASAPLigneFacturation")
                    self.Ajouter(ligne_asap, "ASAPLibelleLigne", libelle)
                    self.Ajouter(ligne_asap, "ASAPUnite", "")
                    self.Ajouter(ligne_asap, "ASAPQuantite", quantite)
                    self.Ajouter(ligne_asap, "ASAPPrixUnitaire", prix_unitaire)
                    self.Ajouter(ligne_asap, "ASAPMontantHT", montant_total)
                    self.Ajouter(ligne_asap, "ASAPTauxTVA", "0.00")
                    self.Ajouter(ligne_asap, "ASAPMontantTVA", "0.00")

        # Enregistrement du fichier XML
        self.nom_fichier_simple = "%s.xml" % utils_texte.Supprimer_accents(self.lot.nom).replace("/", "-").replace("\\", "-")
        with open(os.path.join(self.rep_destination, self.nom_fichier_simple), "wb") as fichier:
            fichier.write(self.doc.toprettyxml(indent="  ", encoding="UTF-8"))

        return True
