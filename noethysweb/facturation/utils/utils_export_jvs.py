# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os
from xml.dom.minidom import Document
from noethysweb.version import GetVersion
from facturation.utils.utils_export_tresor_public import ExporterBase


class Exporter(ExporterBase):
    code_format = "jvs"

    def Creation_fichiers(self):
        # Vérifications
        if not self.pieces:
            self.erreurs.append("Vous devez ajouter au moins une pièce.")
        for piece in self.pieces:
            if not piece.famille.titulaire_helios.rue_resid or not piece.famille.titulaire_helios.cp_resid or not piece.famille.titulaire_helios.ville_resid:
                self.erreurs.append("Adresse incomplète pour %s (famille %s)." % (piece.famille.titulaire_helios.Get_nom(), piece.famille.nom))
        if self.erreurs:
            return False

        # Récupération du détail des pièces
        detail_factures, dict_prestations_factures = self.Get_detail_pieces()
        dict_codes = self.Get_dict_codes(dict_prestations_factures=dict_prestations_factures)

        # Génération du XML
        doc = Document()

        # Génération du document XML
        racine = doc.createElement("n:PES_Aller")
        racine.setAttribute("xsi:schemaLocation", "http://www.minefi.gouv.fr/cp/helios/pes_v2/recette/r0/aller")
        racine.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        racine.setAttribute("xmlns:xenc", "http://www.w3.org/2001/04/xmlenc#")
        racine.setAttribute("xmlns:xad", "http://uri.etsi.org/01903/v1.1.1#")
        racine.setAttribute("xmlns:reca", "http://www.minefi.gouv.fr/cp/helios/pes_v2/recette/r0/aller")
        racine.setAttribute("xmlns:n", "http://www.minefi.gouv.fr/cp/helios/pes_v2/Rev0/aller")
        racine.setAttribute("xmlns:cm", "http://www.minefi.gouv.fr/cp/helios/pes_v2/commun")
        racine.setAttribute("xmlns:acta", "http://www.minefi.gouv.fr/cp/helios/pes_v2/etatactif/r0/aller")
        doc.appendChild(racine)

        # Enveloppe
        Enveloppe = doc.createElement("Enveloppe")
        racine.appendChild(Enveloppe)

        Parametres = doc.createElement("Parametres")
        Enveloppe.appendChild(Parametres)

        Version = doc.createElement("Version")
        Version.setAttribute("V", "2")
        Parametres.appendChild(Version)

        TypFic = doc.createElement("TypFic")
        TypFic.setAttribute("V", "PESALR2")
        Parametres.appendChild(TypFic)

        NomFic = doc.createElement("NomFic")
        NomFic.setAttribute("V", self.nom_fichier_simple[:100])
        Parametres.appendChild(NomFic)

        Emetteur = doc.createElement("Emetteur")
        Enveloppe.appendChild(Emetteur)

        Sigle = doc.createElement("Sigle")
        Sigle.setAttribute("V", "Ivan LUCAS")
        Emetteur.appendChild(Sigle)

        Adresse = doc.createElement("Adresse")
        Adresse.setAttribute("V", "Noethysweb %s" % GetVersion())
        Emetteur.appendChild(Adresse)

        # EnTetePES
        EnTetePES = doc.createElement("EnTetePES")
        racine.appendChild(EnTetePES)

        DteStr = doc.createElement("DteStr")
        DteStr.setAttribute("V", self.lot.date_emission.strftime("%Y-%m-%d"))
        EnTetePES.appendChild(DteStr)

        # IdPost = doc.createElement("IdPost")
        # IdPost.setAttribute("V", dictDonnees["id_poste"][:7])
        # EnTetePES.appendChild(IdPost)

        # SIRET de la collectivité facultatif
        IdColl = doc.createElement("IdColl")
        IdColl.setAttribute("V", self.lot.modele.id_collectivite[:14])
        EnTetePES.appendChild(IdColl)

        # Code collectivité
        CodCol = doc.createElement("CodCol")
        CodCol.setAttribute("V", self.lot.modele.code_collectivite[:3])
        EnTetePES.appendChild(CodCol)

        # Code budget de la collectivité
        CodBud = doc.createElement("CodBud")
        CodBud.setAttribute("V", self.lot.modele.code_budget[:10])
        EnTetePES.appendChild(CodBud)

        # Nom de la collectivité
        LibelleColBud = doc.createElement("LibelleColBud")
        LibelleColBud.setAttribute("V", self.ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.nom_collectivite), majuscules=True))
        EnTetePES.appendChild(LibelleColBud)

        # PES_RecetteAller
        PES_RecetteAller = doc.createElement("PES_RecetteAller")
        racine.appendChild(PES_RecetteAller)

        # EnTeteRecette
        EnTeteRecette = doc.createElement("EnTeteRecette")
        PES_RecetteAller.appendChild(EnTeteRecette)

        IdVer = doc.createElement("IdVer")
        IdVer.setAttribute("V", "2")
        EnTeteRecette.appendChild(IdVer)

        InfoDematerialisee = doc.createElement("InfoDematerialisee")
        InfoDematerialisee.setAttribute("V", "1")
        EnTeteRecette.appendChild(InfoDematerialisee)

        # Bordereau
        Bordereau = doc.createElement("Bordereau")
        PES_RecetteAller.appendChild(Bordereau)

        # Bloc Bordereau
        BlocBordereau = doc.createElement("BlocBordereau")
        Bordereau.appendChild(BlocBordereau)

        Exer = doc.createElement("Exer")
        Exer.setAttribute("V", str(self.lot.exercice)[:4])
        BlocBordereau.appendChild(Exer)

        # Facultatif. Si non renseigné, le bordereau est créé dans le Brouillard
        if self.lot.id_bordereau:
            IdBord = doc.createElement("IdBord")
            IdBord.setAttribute("V", self.lot.id_bordereau[:7])
            BlocBordereau.appendChild(IdBord)

        # Facultatif
        DteBordEm = doc.createElement("DteBordEm")
        DteBordEm.setAttribute("V", self.lot.date_emission.strftime("%Y-%m-%d"))
        BlocBordereau.appendChild(DteBordEm)

        # 01=valeur par défaut. 02 pour annulation-réduction
        TypBord = doc.createElement("TypBord")
        TypBord.setAttribute("V", "01")
        BlocBordereau.appendChild(TypBord)

        NbrPce = doc.createElement("NbrPce")
        NbrPce.setAttribute("V", str(len(self.pieces)))
        BlocBordereau.appendChild(NbrPce)

        MtBordHt = doc.createElement("MtBordHt")
        MtBordHt.setAttribute("V", str(sum([piece.montant for piece in self.pieces])))
        BlocBordereau.appendChild(MtBordHt)

        # for piece in self.pieces:
        for IdEcriture, piece in enumerate(self.pieces, start=1):

            # Pièce
            Piece = doc.createElement("Piece")
            Bordereau.appendChild(Piece)

            BlocPiece = doc.createElement("BlocPiece")
            Piece.appendChild(BlocPiece)

            IdPce = doc.createElement("IdPce")
            IdPce.setAttribute("V", str(piece.pk))
            BlocPiece.appendChild(IdPce)

            # 01=valeur par défaut. 02 pour annulation-réduction.
            TypPce = doc.createElement("TypPce")
            TypPce.setAttribute("V", "01")
            BlocPiece.appendChild(TypPce)

            # 01=valeur par défaut. 06 pour annulation-réduction
            NatPce = doc.createElement("NatPce")
            NatPce.setAttribute("V", "01")
            BlocPiece.appendChild(NatPce)

            # Date du mouvement pour recette uniquement
            DteAsp = doc.createElement("DteAsp")
            DteAsp.setAttribute("V", self.lot.date_envoi.strftime("%Y-%m-%d"))
            BlocPiece.appendChild(DteAsp)

            # Edition
            Edition = doc.createElement("Edition")
            Edition.setAttribute("V", self.lot.modele.edition_asap)
            BlocPiece.appendChild(Edition)

            ObjPce = doc.createElement("ObjPce")
            ObjPce.setAttribute("V", self.ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece, piece=piece)[:160], majuscules=True))
            BlocPiece.appendChild(ObjPce)

            num_sous_ligne = 1
            if piece.facture in dict_codes:
                for (IDposte, code_produit_local, service1, service2), montant in dict_codes[piece.facture].items():
                    detail = detail_factures.get(piece.facture, None)
                    if detail:
                        for index, dict_detail in enumerate(detail, start=1):

                            # Ligne de pièce
                            LigneDePiece = doc.createElement("LigneDePiece")
                            Piece.appendChild(LigneDePiece)

                            BlocLignePiece = doc.createElement("BlocLignePiece")
                            LigneDePiece.appendChild(BlocLignePiece)

                            InfoLignePiece = doc.createElement("InfoLignePiece")
                            BlocLignePiece.appendChild(InfoLignePiece)

                            IdLigne = doc.createElement("IdLigne")
                            IdLigne.setAttribute("V", str(num_sous_ligne))
                            InfoLignePiece.appendChild(IdLigne)

                            ObjLignePce = doc.createElement("ObjLignePce")
                            ObjLignePce.setAttribute("V", self.ConvertToTexte(dict_detail["libelle"][:160], majuscules=True))
                            InfoLignePiece.appendChild(ObjLignePce)

                            CodProdLoc = doc.createElement("CodProdLoc")
                            CodProdLoc.setAttribute("V", code_produit_local)
                            InfoLignePiece.appendChild(CodProdLoc)

                            Nature = doc.createElement("Nature")
                            Nature.setAttribute("V", IDposte)
                            InfoLignePiece.appendChild(Nature)

                            Majo = doc.createElement("Majo")
                            Majo.setAttribute("V", "0")
                            InfoLignePiece.appendChild(Majo)

                            TvaIntraCom = doc.createElement("TvaIntraCom")
                            TvaIntraCom.setAttribute("V", "0")
                            InfoLignePiece.appendChild(TvaIntraCom)

                            MtHT = doc.createElement("MtHT")
                            MtHT.setAttribute("V", str(dict_detail["montant"] * dict_detail["quantite"]))
                            InfoLignePiece.appendChild(MtHT)

                            JVS_FAC_NumeroFacture = doc.createElement("JVS_FAC_NumeroFacture")
                            JVS_FAC_NumeroFacture.setAttribute("V", str(piece.facture.numero)[:20])
                            InfoLignePiece.appendChild(JVS_FAC_NumeroFacture)

                            JVS_LFAC_Date = doc.createElement("JVS_LFAC_Date")
                            JVS_LFAC_Date.setAttribute("V", self.ConvertToTexte(self.date_min_lot.strftime("%Y-%m-%d")))
                            InfoLignePiece.appendChild(JVS_LFAC_Date)

                            JVS_LFAC_DateFin = doc.createElement("JVS_LFAC_DateFin")
                            JVS_LFAC_DateFin.setAttribute("V", self.ConvertToTexte(self.date_max_lot.strftime("%Y-%m-%d")))
                            InfoLignePiece.appendChild(JVS_LFAC_DateFin)

                            JVS_LFAC_Libelle = doc.createElement("JVS_LFAC_Libelle")
                            JVS_LFAC_Libelle.setAttribute("V", self.ConvertToTexte(dict_detail["libelle"][:160], majuscules=True))
                            InfoLignePiece.appendChild(JVS_LFAC_Libelle)

                            JVS_LFAC_Quantite = doc.createElement("JVS_LFAC_Quantite")
                            JVS_LFAC_Quantite.setAttribute("V", str(dict_detail["quantite"]))
                            InfoLignePiece.appendChild(JVS_LFAC_Quantite)

                            JVS_LFAC_Unite = doc.createElement("JVS_LFAC_Unite")
                            JVS_LFAC_Unite.setAttribute("V", "Unite")
                            InfoLignePiece.appendChild(JVS_LFAC_Unite)

                            JVS_LFAC_MtUnitaire = doc.createElement("JVS_LFAC_MtUnitaire")
                            JVS_LFAC_MtUnitaire.setAttribute("V", str(dict_detail["montant"]))
                            InfoLignePiece.appendChild(JVS_LFAC_MtUnitaire)

                            JVS_LFAC_Ordre = doc.createElement("JVS_LFAC_Ordre")
                            JVS_LFAC_Ordre.setAttribute("V", str(num_sous_ligne))
                            InfoLignePiece.appendChild(JVS_LFAC_Ordre)

                            num_sous_ligne += 1

                            # Info prélèvement SEPA
                            if piece.prelevement:

                                InfoPrelevementSEPA = doc.createElement("InfoPrelevementSEPA")
                                BlocLignePiece.appendChild(InfoPrelevementSEPA)

                                NatPrel = doc.createElement("NatPrel")
                                NatPrel.setAttribute("V", "01")
                                InfoPrelevementSEPA.appendChild(NatPrel)

                                PerPrel = doc.createElement("PerPrel")
                                PerPrel.setAttribute("V", "07")
                                InfoPrelevementSEPA.appendChild(PerPrel)

                                DtePrel = doc.createElement("DtePrel")
                                DtePrel.setAttribute("V", self.lot.date_prelevement.strftime("%Y-%m-%d"))
                                InfoPrelevementSEPA.appendChild(DtePrel)

                                MtPrel = doc.createElement("MtPrel")
                                MtPrel.setAttribute("V", str(dict_detail["montant"] * dict_detail["quantite"]))
                                InfoPrelevementSEPA.appendChild(MtPrel)

                                if piece.prelevement_sequence == "FRST": sequence = "02"
                                elif piece.prelevement_sequence == "RCUR": sequence = "03"
                                elif piece.prelevement_sequence == "FNAL": sequence = "04"
                                else: sequence = "01"
                                SequencePres = doc.createElement("SequencePres")
                                SequencePres.setAttribute("V", sequence)
                                InfoPrelevementSEPA.appendChild(SequencePres)

                                DateSignMandat = doc.createElement("DateSignMandat")
                                DateSignMandat.setAttribute("V", piece.prelevement_mandat.date.strftime("%Y-%m-%d"))
                                InfoPrelevementSEPA.appendChild(DateSignMandat)

                                RefUniMdt = doc.createElement("RefUniMdt")
                                RefUniMdt.setAttribute("V", piece.prelevement_mandat.rum)
                                InfoPrelevementSEPA.appendChild(RefUniMdt)

                                LibPrel = doc.createElement("LibPrel")
                                LibPrel.setAttribute("V", self.ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.prelevement_libelle, piece=piece)[:140], majuscules=True))
                                InfoPrelevementSEPA.appendChild(LibPrel)

                            # Tiers
                            Tiers = doc.createElement("Tiers")
                            LigneDePiece.appendChild(Tiers)

                            InfoTiers = doc.createElement("InfoTiers")
                            Tiers.appendChild(InfoTiers)

                            if piece.famille.idtiers_helios:
                                IdTiers = doc.createElement("IdTiers")
                                IdTiers.setAttribute("V", piece.famille.idtiers_helios)
                                InfoTiers.appendChild(IdTiers)

                            if piece.famille.natidtiers_helios:
                                NatIdTiers = doc.createElement("NatIdTiers")
                                NatIdTiers.setAttribute("V", "" if piece.famille.natidtiers_helios == 9999 else piece.famille.natidtiers_helios)
                                InfoTiers.appendChild(NatIdTiers)

                            ref_tiers = piece.famille.reftiers_helios if piece.famille.reftiers_helios else piece.famille.code_compta
                            Numo = doc.createElement("Numo")
                            Numo.setAttribute("V", ref_tiers)
                            InfoTiers.appendChild(Numo)

                            CatTiers = doc.createElement("CatTiers")
                            CatTiers.setAttribute("V", "%02d" % piece.famille.cattiers_helios)
                            InfoTiers.appendChild(CatTiers)

                            NatJur = doc.createElement("NatJur")
                            NatJur.setAttribute("V", "%02d" % piece.famille.natjur_helios)
                            InfoTiers.appendChild(NatJur)

                            TypTiers = doc.createElement("TypTiers")
                            TypTiers.setAttribute("V", "01")
                            InfoTiers.appendChild(TypTiers)

                            civilite_titulaire = piece.famille.titulaire_helios.Get_abrege_civilite()
                            if civilite_titulaire == "M.": civilite_titulaire = "M"
                            if civilite_titulaire == "Melle": civilite_titulaire = "MME"
                            if civilite_titulaire == "Mme": civilite_titulaire = "MME"
                            if civilite_titulaire:
                                Civilite = doc.createElement("Civilite")
                                Civilite.setAttribute("V", civilite_titulaire[:10])
                                InfoTiers.appendChild(Civilite)

                            Nom = doc.createElement("Nom")
                            Nom.setAttribute("V", self.ConvertToTexte(piece.famille.titulaire_helios.nom[:38], majuscules=True))
                            InfoTiers.appendChild(Nom)

                            prenom = piece.famille.titulaire_helios.prenom
                            if prenom:
                                Prenom = doc.createElement("Prenom")
                                Prenom.setAttribute("V", self.ConvertToTexte(prenom[:38], majuscules=True))
                                InfoTiers.appendChild(Prenom)

                            # Adresse
                            Adresse = doc.createElement("Adresse")
                            Tiers.appendChild(Adresse)

                            TypAdr = doc.createElement("TypAdr")
                            TypAdr.setAttribute("V", "1")
                            Adresse.appendChild(TypAdr)

                            Adr2 = doc.createElement("Adr2")
                            Adr2.setAttribute("V", self.ConvertToTexte(piece.famille.titulaire_helios.rue_resid[:38], majuscules=True))
                            Adresse.appendChild(Adr2)

                            CP = doc.createElement("CP")
                            CP.setAttribute("V", piece.famille.titulaire_helios.cp_resid[:5])
                            Adresse.appendChild(CP)

                            Ville = doc.createElement("Ville")
                            Ville.setAttribute("V", self.ConvertToTexte(piece.famille.titulaire_helios.ville_resid[:38], majuscules=True))
                            Adresse.appendChild(Ville)

                            CodRes = doc.createElement("CodRes")
                            CodRes.setAttribute("V", "0")
                            Adresse.appendChild(CodRes)

                            # Compte bancaire
                            if piece.prelevement:
                                CpteBancaire = doc.createElement("CpteBancaire")
                                Tiers.appendChild(CpteBancaire)

                                BIC = doc.createElement("BIC")
                                BIC.setAttribute("V", piece.prelevement_mandat.bic)
                                CpteBancaire.appendChild(BIC)

                                IBAN = doc.createElement("IBAN")
                                IBAN.setAttribute("V", piece.prelevement_mandat.iban)
                                CpteBancaire.appendChild(IBAN)

                                TitCpte = doc.createElement("TitCpte")
                                individu_mandat = piece.prelevement_mandat.individu_nom or piece.prelevement_mandat.individu.Get_nom()
                                TitCpte.setAttribute("V", self.ConvertToTexte(individu_mandat[:32], majuscules=True))
                                CpteBancaire.appendChild(TitCpte)

        # Enregistrement du fichier XML
        f = open(os.path.join(self.rep_destination, self.nom_fichier_simple), "w")
        f.write(doc.toxml())
        f.close()

        return True
