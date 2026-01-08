# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os
from core.utils import utils_dates
from facturation.utils.utils_export_tresor_public import ExporterBase


class Exporter(ExporterBase):
    code_format = "magnus"

    def ConvertToTexte(self, valeur, majuscules=False):
        """ Ajoute des quotes aux textes """
        valeur = super().ConvertToTexte(valeur=valeur, majuscules=majuscules)
        return '"%s"' % valeur

    def Creation_fichiers(self):
        # Vérifie que des pièces existent
        if not self.pieces:
            self.erreurs.append("Vous devez ajouter au moins une pièce.")
            return False

        # Génération des pièces jointes
        dict_pieces_jointes = {}
        if self.lot.modele.inclure_pieces_jointes:
            dict_pieces_jointes = self.Generation_pieces_jointes()
            if not dict_pieces_jointes:
                return False

        # Récupération du détail des factures
        detail_factures, dict_prestations_factures = self.Get_detail_pieces()
        dict_codes = self.Get_dict_codes(dict_prestations_factures=dict_prestations_factures)

        # Génération des lignes des fichiers
        lignes = []
        lignes_pj = []
        lignes_detail = []
        lignes_tsol = []
        for IdEcriture, piece in enumerate(self.pieces, start=1):
            num_sous_ligne = 1
            if piece.facture in dict_codes:
                for (IDposte, code_produit_local, service1, service2), montant in dict_codes[piece.facture].items():
                    ligne = {}

                    # IDEcriture - Texte (50)
                    ligne[1] = self.ConvertToTexte(IdEcriture)

                    # Type - Texte (1)
                    ligne[2] = self.ConvertToTexte("T")

                    # Reelle - Texte (1)
                    ligne[3] = self.ConvertToTexte("O")

                    # Collectivité - Texte (10)
                    ligne[4] = self.ConvertToTexte(self.lot.modele.code_collectivite[:10])

                    # Budget - Texte (10)
                    ligne[5] = self.ConvertToTexte(self.lot.modele.code_budget[:10])

                    # Exercice - Entier
                    ligne[6] = self.ConvertToTexte(self.lot.exercice)

                    # Multiple - Texte (1)
                    ligne[7] = self.ConvertToTexte("M" if num_sous_ligne == 1 else "S")

                    # CodeTiers - Texte (15)
                    ligne[8] = self.ConvertToTexte("FAM%06d" % piece.famille_id)
                    if self.lot.modele.code_compta_as_alias and piece.famille.code_compta:
                        ligne[8] = self.ConvertToTexte(piece.famille.code_compta[:15])

                    # Designation1 - Texte (50)
                    ligne[10] = self.ConvertToTexte(piece.famille.titulaire_helios.nom[:50], majuscules=True)

                    # Designation2 - Texte (50)
                    if piece.famille.titulaire_helios.prenom:
                        ligne[11] = self.ConvertToTexte(piece.famille.titulaire_helios.prenom[:50], majuscules=True)

                    # AdrLig1, AdrLig2, et AdrLig3 - Texte (50)
                    rue_resid = piece.famille.facturation_rue_resid or piece.famille.titulaire_helios.rue_resid
                    if rue_resid:
                        lignes_rue = rue_resid.split("\n")
                        for idx, valeur in enumerate(lignes_rue[:3], 12):
                            ligne[idx] = self.ConvertToTexte(valeur[:50], majuscules=True)

                    # Codepostal - Texte (10)
                    cp_resid = piece.famille.facturation_cp_resid or piece.famille.titulaire_helios.cp_resid or ""
                    ligne[15] = self.ConvertToTexte(cp_resid[:10])

                    # Ville - Texte (50)
                    ville_resid = piece.famille.facturation_ville_resid or piece.famille.titulaire_helios.ville_resid or ""
                    ligne[16] = self.ConvertToTexte(ville_resid[:50])

                    # Libelle1 - Texte (50)
                    ligne[18] = self.ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece, piece=piece)[:50], majuscules=True)

                    # PièceJustificative1 - Texte (50)
                    pj = dict_pieces_jointes.get(piece.facture_id, None)
                    ligne[20] = self.ConvertToTexte(pj["NomPJ"][:50].replace(".pdf", "")) if pj else ""

                    # Sens - Texte (1)
                    ligne[24] = self.ConvertToTexte("R")

                    # Date - Texte (10)
                    ligne[25] = self.ConvertToTexte(utils_dates.ConvertDateToFR(self.lot.date_emission))

                    # Article - Texte (10)
                    ligne[26] = self.ConvertToTexte(IDposte[:10])

                    # Opération - Texte (10)
                    ligne[27] = self.ConvertToTexte(self.lot.modele.operation or "")

                    # Service - Texte (15)
                    ligne[28] = self.ConvertToTexte(service1 or "")

                    # Fonction - Texte (10)
                    ligne[29] = self.ConvertToTexte(self.lot.modele.fonction or "")

                    # Montant HT - Monétaire (,4)
                    ligne[30] = self.ConvertToTexte(str(montant))

                    # Montant TVA - Monétaire (,4)
                    ligne[31] = self.ConvertToTexte("0.00")

                    # Solder - O/N
                    ligne[32] = self.ConvertToTexte("0")

                    # Priorité - Entier
                    ligne[33] = self.ConvertToTexte("")

                    # Accepté - O/N
                    ligne[35] = self.ConvertToTexte("")

                    # Erroné - O/N
                    ligne[36] = self.ConvertToTexte("")

                    # NJ - Texte (2)
                    ligne[38] = self.ConvertToTexte("%02d" % piece.famille.natjur_helios)

                    # TvaTaux - Reel Simple (5)
                    ligne[40] = self.ConvertToTexte("")

                    # Service 2 - Texte (10)
                    ligne[41] = self.ConvertToTexte(service2 or "")

                    # Mixte - Texte (1)
                    ligne[44] = self.ConvertToTexte("")

                    # Imprévisible - Texte (1)
                    ligne[45] = self.ConvertToTexte("")

                    # CodeAlim - Texte (1)
                    ligne[46] = self.ConvertToTexte("")

                    # MarcheSim - Texte (1)
                    ligne[47] = self.ConvertToTexte("")

                    # SuiviDelai - Texte (1)
                    ligne[50] = self.ConvertToTexte("")

                    # DelaiPaiement - Entier
                    ligne[51] = self.ConvertToTexte("")

                    # CPL - Texte (4)
                    ligne[54] = self.ConvertToTexte(code_produit_local[:4])

                    # Prélèvement :
                    if piece.prelevement:

                        # TitCpte - Texte (32)
                        individu_mandat = piece.prelevement_mandat.individu_nom or piece.prelevement_mandat.individu.Get_nom()
                        ligne[64] = self.ConvertToTexte(individu_mandat[:32], majuscules=True)

                        # IBAN - Texte (34)
                        ligne[65] = self.ConvertToTexte(piece.prelevement_mandat.iban)

                        # BIC - Texte (11)
                        ligne[66] = self.ConvertToTexte(piece.prelevement_mandat.bic)

                    # Tribunal - Texte (100)
                    ligne[68] = self.ConvertToTexte(self.lot.modele.nom_tribunal or "")

                    # TIPI - O/N
                    ligne[70] = self.ConvertToTexte("O" if self.lot.modele.payable_internet else "N")

                    # PrelevementSEPA - O/N
                    ligne[71] = self.ConvertToTexte("O" if piece.prelevement else "N")

                    # DatePrel - Texte (10)
                    if piece.prelevement:
                        ligne[72] = self.ConvertToTexte(utils_dates.ConvertDateToFR(self.lot.date_prelevement))

                        # PeriodicitePrel - Texte (2)
                        ligne[73] = self.ConvertToTexte("02") # Mensuel

                        # ICS - Texte (13)
                        ligne[74] = self.ConvertToTexte(self.lot.modele.compte.code_ics)

                        # RUM - Texte (35)
                        ligne[75] = self.ConvertToTexte(piece.prelevement_mandat.rum)

                    # RUMMigre - O/N
                    ligne[76] = self.ConvertToTexte("")

                    # RUM - Texte (35)
                    if piece.prelevement:
                        ligne[77] = self.ConvertToTexte(utils_dates.ConvertDateToFR(piece.prelevement_mandat.date))

                        # LibellePrel - Texte (140)
                        ligne[78] = self.ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.prelevement_libelle, piece=piece)[:140], majuscules=True)

                        # SequencePrel - Texte (02)
                        if piece.prelevement_sequence == "FRST": sequence = "02"
                        elif piece.prelevement_sequence == "RCUR": sequence = "03"
                        elif piece.prelevement_sequence == "FNAL": sequence = "04"
                        else: sequence = "01"
                        ligne[79] = self.ConvertToTexte(sequence)

                    # TitCpteDiff - O/N
                    ligne[80] = self.ConvertToTexte("N")

                    # AncienBanque - O/N
                    ligne[84] = self.ConvertToTexte("N")

                    # Version - Numérique (3)
                    ligne[90] = self.ConvertToTexte("19")

                    # CategorieTiersPES - Numérique (2)
                    ligne[91] = self.ConvertToTexte("%02d" % piece.famille.cattiers_helios)

                    # NatJuridiqueTiersPES - Numérique (2)
                    ligne[92] = self.ConvertToTexte("%02d" % piece.famille.natjur_helios)

                    # Civilité - Texte (32)
                    civilite_titulaire = piece.famille.titulaire_helios.Get_abrege_civilite()
                    if civilite_titulaire == "M.": ligne[93] = self.ConvertToTexte("M")
                    if civilite_titulaire == "Mme": ligne[93] = self.ConvertToTexte("MME")
                    if civilite_titulaire == "Melle": ligne[93] = self.ConvertToTexte("MLLE")

                    # NatIdentifiantTiers - Numérique (2)
                    ligne[94] = self.ConvertToTexte("" if piece.famille.natidtiers_helios == 9999 else piece.famille.natidtiers_helios)

                    # IdentifiantTiers - Texte (18)
                    ligne[95] = self.ConvertToTexte(piece.famille.idtiers_helios or "")

                    # CodeResident - Numérique (3)
                    ligne[97] = self.ConvertToTexte("0")

                    # TypeTiersPES - Numérique (2)
                    ligne[98] = self.ConvertToTexte("01")

                    # DatNaisTiers - Texte (10)
                    ligne[107] = self.ConvertToTexte(utils_dates.ConvertDateToFR(piece.famille.titulaire_helios.date_naiss) if piece.famille.titulaire_helios.date_naiss else "")

                    # TitreASAP - O/N
                    ligne[108] = self.ConvertToTexte("O")

                    # TIP ASAP - O/N
                    ligne[109] = self.ConvertToTexte("N")

                    # NumeroFacture - Texte (50)
                    # ligne[111] = self.ConvertToTexte(piece.facture.numero)

                    # EditionASAP - Numérique (2)
                    ligne[112] = self.ConvertToTexte(self.lot.modele.edition_asap)

                    # DateEnvoiASAP - Texte (10)
                    # ligne[113] = self.ConvertToTexte(self.lot.date_envoi.strftime("%Y%m%d"))

                    # Formatage de la ligne
                    texte_ligne = ['""' for x in range(0, 125)]
                    for index, valeur in ligne.items():
                        texte_ligne[index-1] = valeur
                    lignes.append(";".join(texte_ligne))

                    # Incrémente sous-ligne
                    num_sous_ligne += 1

                # Création de la ligne de détail
                if self.lot.modele.inclure_detail:
                    detail = detail_factures.get(piece.facture, None)
                    if detail:
                        for index, dict_detail in enumerate(detail, start=1):
                            ligne_detail = {}

                            # Version - Numérique (3)
                            ligne_detail[1] = self.ConvertToTexte("19")

                            # RefIdEcriture - Texte (50)
                            ligne_detail[2] = ligne[1]

                            # DateDebut - Date
                            ligne_detail[3] = self.ConvertToTexte(utils_dates.ConvertDateToFR(self.date_min_lot))

                            # DateFin - Date
                            ligne_detail[4] = self.ConvertToTexte(utils_dates.ConvertDateToFR(self.date_max_lot))

                            # Libelle - Texte (200)
                            ligne_detail[5] = self.ConvertToTexte(dict_detail["libelle"][:200], majuscules=True)

                            # Quantite - Numérique (5)
                            ligne_detail[6] = str(dict_detail["quantite"])

                            # MtUnitaire - Monétaire
                            ligne_detail[10] = str(dict_detail["montant"])

                            # MtHTaxe - Monétaire
                            ligne_detail[13] = str(dict_detail["montant"] * dict_detail["quantite"])

                            # MtTTC - Monétaire
                            ligne_detail[16] = str(dict_detail["montant"] * dict_detail["quantite"])

                            # Ordre - Numérique (3)
                            ligne_detail[17] = str(index)

                            # Formatage de la ligne de détail
                            texte_ligne_detail = ['""' for x in range(0, 17)]
                            for index, valeur in ligne_detail.items():
                                texte_ligne_detail[index-1] = valeur
                            lignes_detail.append(";".join(texte_ligne_detail))

            # Création de la pièce jointe
            ligne_pj = {}
            pj = dict_pieces_jointes.get(piece.facture_id, None)
            if pj:

                # RefIdEcriture - Texte (50)
                ligne_pj[1] = ligne[1]

                # NomPJ - Texte (100)
                ligne_pj[2] = self.ConvertToTexte(pj["NomPJ"][:100])

                # DescriptionPJ - Texte (255)
                ligne_pj[3] = self.ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece, piece=piece)[:255], majuscules=True)

                # TypPJPES - Texte (3)
                ligne_pj[4] = self.ConvertToTexte(self.lot.modele.type_pj)

                # TypDoc - Texte (2)
                ligne_pj[6] = self.ConvertToTexte("02")

                # TypFichier - Texte (2)
                ligne_pj[7] = self.ConvertToTexte("06")

                # Version - Numérique (3)
                ligne_pj[8] = self.ConvertToTexte("19")

                # Formatage de la ligne PJ
                texte_ligne_pj = ['""' for x in range(0, 8)]
                for index, valeur in ligne_pj.items():
                    texte_ligne_pj[index-1] = valeur
                lignes_pj.append(";".join(texte_ligne_pj))

            # Création du tiers solidaire
            ligne_tsol = {}
            if self.lot.modele.inclure_tiers_solidaires and piece.famille.tiers_solidaire:

                # Version - Numérique (3)
                ligne_tsol[1] = self.ConvertToTexte("19")

                # RefIdEcriture - Texte (50)
                ligne_tsol[2] = ligne[1]

                # CodeTiers - Texte (15)
                ligne_tsol[3] = ligne[8]

                # Designation1 - Texte (50)
                ligne_tsol[4] = self.ConvertToTexte(piece.famille.tiers_solidaire.nom[:50], majuscules=True)

                # Designation2 - Texte (50)
                if piece.famille.tiers_solidaire.prenom:
                    ligne_tsol[5] = self.ConvertToTexte(piece.famille.tiers_solidaire.prenom[:50], majuscules=True)

                # AdrLig1, AdrLig2, et AdrLig3 - Texte (50)
                if piece.famille.tiers_solidaire.rue_resid:
                    lignes_rue = piece.famille.tiers_solidaire.rue_resid.split("\n")
                    for idx, valeur in enumerate(lignes_rue[:3], 6):
                        ligne_tsol[idx] = self.ConvertToTexte(valeur[:50], majuscules=True)

                # Codepostal - Texte (10)
                if piece.famille.tiers_solidaire.cp_resid:
                    ligne_tsol[9] = self.ConvertToTexte(piece.famille.tiers_solidaire.cp_resid[:10])

                # Ville - Texte (50)
                if piece.famille.tiers_solidaire.ville_resid:
                    ligne_tsol[10] = self.ConvertToTexte(piece.famille.tiers_solidaire.ville_resid[:50])

                # Catégorie Tiers PES
                ligne_tsol[19] = self.ConvertToTexte("01")

                # Nat Juridique Tiers PES
                ligne_tsol[20] = self.ConvertToTexte("01")

                # Civilité PES - Texte (32)
                civilite_titulaire = piece.famille.tiers_solidaire.Get_abrege_civilite()
                if civilite_titulaire == "M.": ligne_tsol[21] = self.ConvertToTexte("M")
                if civilite_titulaire == "Mme": ligne_tsol[21] = self.ConvertToTexte("MME")
                if civilite_titulaire == "Melle": ligne_tsol[21] = self.ConvertToTexte("MLLE")

                # DatNaisTiers - Texte (10)
                ligne_tsol[27] = self.ConvertToTexte(utils_dates.ConvertDateToFR(piece.famille.tiers_solidaire.date_naiss) if piece.famille.tiers_solidaire.date_naiss else "")

                # Formatage de la ligne TSOL
                texte_ligne_tsol = ['""' for x in range(0, 27)]
                for index, valeur in ligne_tsol.items():
                    texte_ligne_tsol[index-1] = valeur
                lignes_tsol.append(";".join(texte_ligne_tsol))

        # Enregistrement du fichier ECRITURES
        if lignes:
            contenu_lignes = "\n".join(lignes)
            with open(os.path.join(self.rep_destination, "WTAMC001.txt"), "w") as fichier:
                fichier.write(contenu_lignes)

        # Enregistrement du fichier ECRITURES_ASAP (Détail)
        if lignes_detail:
            contenu_lignes_detail = "\n".join(lignes_detail)
            with open(os.path.join(self.rep_destination, "WTAMC001AS.txt"), "w") as fichier:
                fichier.write(contenu_lignes_detail)

        # Enregistrement du fichier ECRITURES_PJ
        if lignes_pj:
            contenu_lignes_pj = "\n".join(lignes_pj)
            with open(os.path.join(self.rep_destination, "WTAMC001PJ.txt"), "w") as fichier:
                fichier.write(contenu_lignes_pj)

        # Enregistrement du fichier ECRITURES_TSOL
        if lignes_tsol:
            contenu_lignes_tsol = "\n".join(lignes_tsol)
            with open(os.path.join(self.rep_destination, "WTAMC001_TSOL.txt"), "w") as fichier:
                fichier.write(contenu_lignes_tsol)

        return True
