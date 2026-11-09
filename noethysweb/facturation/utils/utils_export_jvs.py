# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, decimal
from xml.dom.minidom import Document
from noethysweb.version import GetVersion
from core.models import Deduction
from facturation.utils.utils_export_tresor_public import ExporterBase


class Exporter(ExporterBase):
    code_format = "jvs"

    def Get_lignes_factures(self, dict_prestations_factures=None):
        """ Regroupe les prestations de chaque facture en lignes de pièce.
            Si l'option 'detail_deductions' est cochée, chaque ligne de prestation est exportée à son montant initial
            et suivie de lignes négatives pour les aides et déductions qui lui ont été appliquées. """
        detailler_deductions = self.lot.modele.detail_deductions

        # Récupération des déductions
        dict_deductions = {}
        if detailler_deductions:
            for deduction in Deduction.objects.filter(prestation__facture_id__in=[piece.facture_id for piece in self.pieces]).order_by("date", "pk"):
                dict_deductions.setdefault(deduction.prestation_id, []).append(deduction)

        dict_lignes = {}
        for facture, liste_prestations in dict_prestations_factures.items():
            dict_groupes = {}
            for dict_prestation in liste_prestations:
                prestation = dict_prestation["prestation"]
                deductions = dict_deductions.get(prestation.pk, [])
                total_deductions = sum([deduction.montant for deduction in deductions], decimal.Decimal(0))

                # Le montant brut est recalculé à partir du montant net pour que le total de la pièce reste toujours juste
                montant_brut = prestation.montant + total_deductions
                montant_unitaire = (montant_brut / prestation.quantite).quantize(decimal.Decimal("0.01"))

                # Regroupement par code comptable, individu, libellé et montant unitaire
                libelle = self.Get_libelle_prestation(prestation)
                key = (dict_prestation["id_poste"], dict_prestation["code_prodloc"], dict_prestation["service1"], dict_prestation["service2"], prestation.individu_id, libelle, montant_unitaire)
                if key not in dict_groupes:
                    dict_groupes[key] = {
                        "libelle": libelle, "montant_unitaire": montant_unitaire, "quantite": 0, "montant_total": decimal.Decimal(0),
                        "id_poste": dict_prestation["id_poste"], "code_prodloc": dict_prestation["code_prodloc"],
                        "prenom": (prestation.individu.prenom or prestation.individu.nom) if prestation.individu else "",
                        "deductions": {},
                    }
                groupe = dict_groupes[key]
                groupe["quantite"] += prestation.quantite
                groupe["montant_total"] += montant_brut
                for deduction in deductions:
                    if deduction.montant:
                        groupe["deductions"].setdefault(deduction.label, []).append(deduction.montant)

            # Création des lignes
            dict_lignes[facture] = []
            for groupe in sorted(dict_groupes.values(), key=lambda x: x["libelle"]):
                dict_lignes[facture].append({
                    "libelle": groupe["libelle"], "quantite": groupe["quantite"], "montant_unitaire": groupe["montant_unitaire"],
                    "montant_total": groupe["montant_total"], "montant_prelevement": groupe["montant_total"], "remise": None,
                    "id_poste": groupe["id_poste"], "code_prodloc": groupe["code_prodloc"],
                })

                # Lignes de remise pour les aides et déductions : selon la doc JVS, MtHT et MtPrel sont négatifs,
                # JVS_LFAC_MtRemise est positif et les imputations sont identiques à celles de la ligne positive
                # pour permettre le regroupement lors de la transmission PES.
                for label, montants in groupe["deductions"].items():
                    total = sum(montants, decimal.Decimal(0))
                    libelle = "Remise %s" % label
                    dict_lignes[facture].append({
                        "libelle": "%s - %s" % (groupe["prenom"], libelle) if groupe["prenom"] else libelle,
                        "quantite": None, "montant_unitaire": None, "montant_total": -total, "montant_prelevement": -total, "remise": total,
                        "id_poste": groupe["id_poste"], "code_prodloc": groupe["code_prodloc"],
                    })

        return dict_lignes

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
        lignes_factures = self.Get_lignes_factures(dict_prestations_factures=dict_prestations_factures)

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

            for num_sous_ligne, ligne in enumerate(lignes_factures.get(piece.facture, []), start=1):

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
                ObjLignePce.setAttribute("V", self.ConvertToTexte(ligne["libelle"][:160], majuscules=True))
                InfoLignePiece.appendChild(ObjLignePce)

                CodProdLoc = doc.createElement("CodProdLoc")
                CodProdLoc.setAttribute("V", ligne["code_prodloc"])
                InfoLignePiece.appendChild(CodProdLoc)

                Nature = doc.createElement("Nature")
                Nature.setAttribute("V", ligne["id_poste"])
                InfoLignePiece.appendChild(Nature)

                if self.lot.modele.fonction:
                    fonction = doc.createElement("Fonction")
                    fonction.setAttribute("V", self.lot.modele.fonction)
                    InfoLignePiece.appendChild(fonction)

                if self.lot.modele.service1:
                    CptAna = doc.createElement("CptAna")
                    CptAna.setAttribute("V", self.lot.modele.service1)
                    InfoLignePiece.appendChild(CptAna)

                if self.lot.modele.service2:
                    Ventilation = doc.createElement("Ventilation")
                    Ventilation.setAttribute("V", self.lot.modele.service2)
                    InfoLignePiece.appendChild(Ventilation)

                Majo = doc.createElement("Majo")
                Majo.setAttribute("V", "0")
                InfoLignePiece.appendChild(Majo)

                TvaIntraCom = doc.createElement("TvaIntraCom")
                TvaIntraCom.setAttribute("V", "0")
                InfoLignePiece.appendChild(TvaIntraCom)

                MtHT = doc.createElement("MtHT")
                MtHT.setAttribute("V", str(ligne["montant_total"]))
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
                JVS_LFAC_Libelle.setAttribute("V", self.ConvertToTexte(ligne["libelle"][:160], majuscules=True))
                InfoLignePiece.appendChild(JVS_LFAC_Libelle)

                if ligne["remise"] is None:
                    # Ligne détaillée : quantité, unité et prix unitaire (strictement positif)
                    JVS_LFAC_Quantite = doc.createElement("JVS_LFAC_Quantite")
                    JVS_LFAC_Quantite.setAttribute("V", str(ligne["quantite"]))
                    InfoLignePiece.appendChild(JVS_LFAC_Quantite)

                    JVS_LFAC_Unite1 = doc.createElement("JVS_LFAC_Unite1")
                    JVS_LFAC_Unite1.setAttribute("V", "Unite")
                    InfoLignePiece.appendChild(JVS_LFAC_Unite1)

                    JVS_LFAC_MtUnitaire = doc.createElement("JVS_LFAC_MtUnitaire")
                    JVS_LFAC_MtUnitaire.setAttribute("V", str(ligne["montant_unitaire"]))
                    InfoLignePiece.appendChild(JVS_LFAC_MtUnitaire)
                else:
                    # Ligne de remise : MtHT négatif et montant de la remise en positif (doc JVS Millésime On-Line)
                    JVS_LFAC_MtRemise = doc.createElement("JVS_LFAC_MtRemise")
                    JVS_LFAC_MtRemise.setAttribute("V", str(ligne["remise"]))
                    InfoLignePiece.appendChild(JVS_LFAC_MtRemise)

                JVS_LFAC_Ordre = doc.createElement("JVS_LFAC_Ordre")
                JVS_LFAC_Ordre.setAttribute("V", str(num_sous_ligne))
                InfoLignePiece.appendChild(JVS_LFAC_Ordre)


                # Info prélèvement SEPA (MtPrel négatif pour les lignes de remise)
                if piece.prelevement and ligne["montant_prelevement"]:

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
                    MtPrel.setAttribute("V", str(ligne["montant_prelevement"]))
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
