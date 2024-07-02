# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import decimal, os, calendar, datetime, uuid, zipfile
from io import BytesIO
from urllib.request import urlretrieve
from xml.dom.minidom import Document
from django.conf import settings
from core.models import PrelevementsLot, Prelevements, Organisateur
from core.utils import utils_texte, utils_fichiers


class Exporter():
    def __init__(self, idlot=None, request=None):
        self.idlot = idlot
        self.request = request
        self.organisateur = Organisateur.objects.filter(pk=1).first()
        self.erreurs = []

    def Generer(self):
        # Importation des données
        self.lot = PrelevementsLot.objects.select_related("modele", "modele__compte", "modele__mode", "modele__perception").get(pk=self.idlot)
        self.pieces = Prelevements.objects.select_related("famille", "mandat", "facture").filter(lot=self.lot)

        # Création du répertoire de sortie
        self.rep_base = os.path.join("temp", str(uuid.uuid4()))
        self.rep_destination = os.path.join(settings.MEDIA_ROOT, self.rep_base, "prelevements")
        os.makedirs(self.rep_destination)

        # Préparation des lots de séquence
        self.liste_lots = []
        for sequence in ["OOFF", "FRST", "RCUR", "FNAL"]:
            montant_total = decimal.Decimal(0.0)
            liste_transactions = []
            for piece in self.pieces:
                if sequence == piece.sequence:
                    liste_transactions.append(piece)
                    montant_total += piece.montant

            if liste_transactions:
                self.liste_lots.append({"sequence": sequence, "transactions": liste_transactions, "montant_total": montant_total})

        # Vérifie qu'une séquence est bien définie pour chaque pièce
        self.erreurs.extend(["La séquence n'a pas été définie pour la famille %s" % piece.famille.nom for piece in self.pieces if not piece.sequence])

        # Création du nom du fichier
        if self.lot.modele.format == "public_dft":
            today = datetime.date.today()
            quantieme = (today - datetime.date(today.year, 1, 1)).days + 1
            self.nom_fichier = "%s-DFT-SDD-%s%03d-%03d" % (self.lot.modele.identifiant_service, str(today.year)[2:], quantieme, self.lot.numero_sequence)
        else:
            self.nom_fichier = self.lot.nom

        # Création des fichiers
        if not self.Creation_fichiers():
            return False

        return os.path.join(settings.MEDIA_URL, self.rep_base, "prelevements", self.nom_fichier)

    def Get_erreurs_html(self):
        html = """
            <div class='text-red'>Les erreurs suivantes ont été rencontrées :<div><ul class='mt-2'>%s</ul>
            <div class="buttonHolder">
                <div class="modal-footer" style="padding-bottom:0px;padding-right:0px;padding-left:0px;">
                    <button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-times margin-r-5'></i>Fermer</button>
                </div>
            </div>
        """ % "".join(["<li>%s</li>" % erreur for erreur in self.erreurs])
        return html

    def Formate_libelle(self, texte="", piece=None):
        texte = texte.replace("{NOM_ORGANISATEUR}", self.organisateur.nom)
        if piece:
            texte = texte.replace("{NUM_FACTURE}", str(piece.facture.numero))
        texte = texte.replace("{MOIS}", str(self.lot.mois))
        texte = texte.replace("{MOIS_LETTRES}", self.lot.get_mois_display())
        texte = texte.replace("{ANNEE}", str(self.lot.exercice))
        texte = texte.replace("{DATE_DEBUT_MOIS}", datetime.date(self.lot.exercice, self.lot.mois, 1).strftime('%d/%m/%Y'))
        texte = texte.replace("{DATE_FIN_MOIS}", datetime.date(self.lot.exercice, self.lot.mois, calendar.monthrange(self.lot.exercice, self.lot.mois)[1]).strftime('%d/%m/%Y'))
        return texte

    def Creation_fichiers(self):
        # Recherche les erreurs potentielles
        if not self.pieces: self.erreurs.append("Vous devez ajouter au moins une pièce.")
        if not self.organisateur.num_siret: self.erreurs.append("Vous devez renseigner le SIRET de l'organisateur dans le menu Paramétrage > Organisateur.")
        if not self.lot.modele.compte.raison: self.erreurs.append("Vous devez renseigner la raison sociale dans le paramétrage du compte bancaire.")
        if not self.lot.modele.compte.iban: self.erreurs.append("Vous devez renseigner l'IBAN dans le paramétrage du compte bancaire.")
        if not self.lot.modele.compte.bic: self.erreurs.append("Vous devez renseigner le BIC dans le paramétrage du compte bancaire.")
        if not self.lot.modele.compte.dft_titulaire and self.lot.modele.format == "public_dft": self.erreurs.append("Vous devez renseigner le titulaire DFT dans le paramétrage du compte bancaire.")
        if not self.lot.modele.compte.dft_iban and self.lot.modele.format == "public_dft": self.erreurs.append("Vous devez renseigner l'IBAN DFT dans le paramétrage du compte bancaire.")
        if self.lot.modele.perception:
            if not self.lot.modele.perception.rue_resid: self.erreurs.append("Vous devez renseigner la rue de la perception dans le paramétrage de la perception.")
            if not self.lot.modele.perception.cp_resid: self.erreurs.append("Vous devez renseigner le code postal de la perception dans le paramétrage de la perception.")
            if not self.lot.modele.perception.ville_resid: self.erreurs.append("Vous devez renseigner la ville de la perception dans le paramétrage de la perception.")

        if self.erreurs:
            return False

        # Génération du XML
        doc = Document()

        # Génération du document XML
        racine = doc.createElement("Document")
        racine.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        racine.setAttribute("xmlns", "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02")
        doc.appendChild(racine)

        # CstmrDrctDbtInitn
        CstmrDrctDbtInitn = doc.createElement("CstmrDrctDbtInitn")
        racine.appendChild(CstmrDrctDbtInitn)

        # ----------------------------------------------------------- NIVEAU MESSAGE ------------------------------------------------------------------------------

        # ------------- Caractéristiques générales du prélèvement -------------------

        # GrpHdr
        GrpHdr = doc.createElement("GrpHdr")
        CstmrDrctDbtInitn.appendChild(GrpHdr)

        # MsgId
        MsgId = doc.createElement("MsgId")
        GrpHdr.appendChild(MsgId)
        MsgId.appendChild(doc.createTextNode(self.nom_fichier))

        # CreDtTm
        CreDtTm = doc.createElement("CreDtTm")
        GrpHdr.appendChild(CreDtTm)
        CreDtTm.appendChild(doc.createTextNode(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))

        # NbOfTxs
        NbOfTxs = doc.createElement("NbOfTxs")
        GrpHdr.appendChild(NbOfTxs)
        NbOfTxs.appendChild(doc.createTextNode(str(len(self.pieces))))

        # CtrlSum
        CtrlSum = doc.createElement("CtrlSum")
        GrpHdr.appendChild(CtrlSum)
        CtrlSum.appendChild(doc.createTextNode(str(sum([piece.montant for piece in self.pieces]))))

        # ------------- Créantier (organisateur) -------------------

        # InitgPty
        InitgPty = doc.createElement("InitgPty")
        GrpHdr.appendChild(InitgPty)

        # Nm
        Nm = doc.createElement("Nm")
        InitgPty.appendChild(Nm)
        Nm.appendChild(doc.createTextNode(self.lot.modele.compte.raison[:70]))

        # Id
        Id = doc.createElement("Id")
        InitgPty.appendChild(Id)

        # OrgId
        OrgId = doc.createElement("OrgId")
        Id.appendChild(OrgId)

        # Othr
        Othr = doc.createElement("Othr")
        OrgId.appendChild(Othr)

        # Id
        Id = doc.createElement("Id")
        Othr.appendChild(Id)
        Id.appendChild(doc.createTextNode(self.organisateur.num_siret))

        # SchmeNm
        SchmeNm = doc.createElement("SchmeNm")
        Othr.appendChild(SchmeNm)

        # Prtry
        Prtry = doc.createElement("Prtry")
        SchmeNm.appendChild(Prtry)
        Prtry.appendChild(doc.createTextNode("SIRET"))

        # ----------------------------------------------------------- NIVEAU LOT ------------------------------------------------------------------------------

        for dict_lot in self.liste_lots:

            # PmtInf
            PmtInf = doc.createElement("PmtInf")
            CstmrDrctDbtInitn.appendChild(PmtInf)

            # PmtInfId
            PmtInfId = doc.createElement("PmtInfId")
            PmtInf.appendChild(PmtInfId)
            PmtInfId.appendChild(doc.createTextNode("%s %s" % (self.lot.nom, dict_lot["sequence"])))

            # PmtMtd
            PmtMtd = doc.createElement("PmtMtd")
            PmtInf.appendChild(PmtMtd)
            PmtMtd.appendChild(doc.createTextNode("DD"))

            # NbOfTxs
            NbOfTxs = doc.createElement("NbOfTxs")
            PmtInf.appendChild(NbOfTxs)
            NbOfTxs.appendChild(doc.createTextNode(str(len(dict_lot["transactions"]))))

            # CtrlSum
            CtrlSum = doc.createElement("CtrlSum")
            PmtInf.appendChild(CtrlSum)
            CtrlSum.appendChild(doc.createTextNode(str(dict_lot["montant_total"])))

            # PmtTpInf
            PmtTpInf = doc.createElement("PmtTpInf")
            PmtInf.appendChild(PmtTpInf)

            # SvcLvl
            SvcLvl = doc.createElement("SvcLvl")
            PmtTpInf.appendChild(SvcLvl)

            # Cd
            Cd = doc.createElement("Cd")
            SvcLvl.appendChild(Cd)
            Cd.appendChild(doc.createTextNode("SEPA"))

            # LclInstrm
            LclInstrm = doc.createElement("LclInstrm")
            PmtTpInf.appendChild(LclInstrm)

            # Cd
            Cd = doc.createElement("Cd")
            LclInstrm.appendChild(Cd)
            Cd.appendChild(doc.createTextNode("CORE"))

            # SeqTp
            SeqTp = doc.createElement("SeqTp")
            PmtTpInf.appendChild(SeqTp)
            SeqTp.appendChild(doc.createTextNode(dict_lot["sequence"]))

            # ReqdColltnDt
            ReqdColltnDt = doc.createElement("ReqdColltnDt")
            PmtInf.appendChild(ReqdColltnDt)
            ReqdColltnDt.appendChild(doc.createTextNode(str(self.lot.date)))

            # Cdtr
            Cdtr = doc.createElement("Cdtr")
            PmtInf.appendChild(Cdtr)

            if self.lot.modele.format == "prive":
                # Cdtr
                Nm = doc.createElement("Nm")
                Cdtr.appendChild(Nm)
                Nm.appendChild(doc.createTextNode(self.lot.modele.compte.raison))

            if self.lot.modele.format == "public_dft":

                # Cdtr
                Nm = doc.createElement("Nm")
                Cdtr.appendChild(Nm)
                Nm.appendChild(doc.createTextNode(self.lot.modele.perception.nom))

                # PstlAdr
                PstlAdr = doc.createElement("PstlAdr")
                Cdtr.appendChild(PstlAdr)

                # Ctry
                Ctry = doc.createElement("Ctry")
                PstlAdr.appendChild(Ctry)
                Ctry.appendChild(doc.createTextNode("FR"))

                # AdrLine
                AdrLine = doc.createElement("AdrLine")
                PstlAdr.appendChild(AdrLine)
                AdrLine.appendChild(doc.createTextNode(self.lot.modele.perception.rue_resid))

                # AdrLine
                AdrLine = doc.createElement("AdrLine")
                PstlAdr.appendChild(AdrLine)
                AdrLine.appendChild(doc.createTextNode(u"%s %s" % (self.lot.modele.perception.cp_resid, self.lot.modele.perception.ville_resid)))

            # CdtrAcct
            CdtrAcct = doc.createElement("CdtrAcct")
            PmtInf.appendChild(CdtrAcct)

            # Id
            Id = doc.createElement("Id")
            CdtrAcct.appendChild(Id)

            # IBAN
            IBAN = doc.createElement("IBAN")
            Id.appendChild(IBAN)
            IBAN.appendChild(doc.createTextNode(self.lot.modele.compte.iban))

            # CdtrAgt
            CdtrAgt = doc.createElement("CdtrAgt")
            PmtInf.appendChild(CdtrAgt)

            # FinInstnId
            FinInstnId = doc.createElement("FinInstnId")
            CdtrAgt.appendChild(FinInstnId)

            # BIC
            BIC = doc.createElement("BIC")
            FinInstnId.appendChild(BIC)
            BIC.appendChild(doc.createTextNode(self.lot.modele.compte.bic))

            if self.lot.modele.format == "public_dft":
                # UltmtCdtr
                UltmtCdtr = doc.createElement("UltmtCdtr")
                PmtInf.appendChild(UltmtCdtr)

                # Nm
                Nm = doc.createElement("Nm")
                UltmtCdtr.appendChild(Nm)
                Nm.appendChild(doc.createTextNode(self.lot.modele.compte.dft_titulaire))

                # Id
                Id = doc.createElement("Id")
                UltmtCdtr.appendChild(Id)

                # OrgId
                OrgId = doc.createElement("OrgId")
                Id.appendChild(OrgId)

                # Othr
                Othr = doc.createElement("Othr")
                OrgId.appendChild(Othr)

                # Id
                Id = doc.createElement("Id")
                Othr.appendChild(Id)
                Id.appendChild(doc.createTextNode(self.lot.modele.compte.dft_iban))

                # ChrgBr
                ChrgBr = doc.createElement("ChrgBr")
                PmtInf.appendChild(ChrgBr)
                ChrgBr.appendChild(doc.createTextNode("SLEV"))

            # CdtrSchmeId
            CdtrSchmeId = doc.createElement("CdtrSchmeId")
            PmtInf.appendChild(CdtrSchmeId)

            # Id
            Id = doc.createElement("Id")
            CdtrSchmeId.appendChild(Id)

            # PrvtId
            PrvtId = doc.createElement("PrvtId")
            Id.appendChild(PrvtId)

            # Othr
            Othr = doc.createElement("Othr")
            PrvtId.appendChild(Othr)

            # Id
            Id = doc.createElement("Id")
            Othr.appendChild(Id)
            Id.appendChild(doc.createTextNode(self.lot.modele.compte.code_ics))

            # SchmeNm
            SchmeNm = doc.createElement("SchmeNm")
            Othr.appendChild(SchmeNm)

            # Prtry
            Prtry = doc.createElement("Prtry")
            SchmeNm.appendChild(Prtry)
            Prtry.appendChild(doc.createTextNode("SEPA"))

            # ----------------------------------------------------------- NIVEAU TRANSACTION ------------------------------------------------------------------------------

            for transaction in dict_lot["transactions"]:
                if transaction.facture:
                    transaction_id = "FACT%s" % transaction.facture.numero
                else:
                    transaction_id = transaction.libelle

                # DrctDbtTxInf
                DrctDbtTxInf = doc.createElement("DrctDbtTxInf")
                PmtInf.appendChild(DrctDbtTxInf)

                # PmtId
                PmtId = doc.createElement("PmtId")
                DrctDbtTxInf.appendChild(PmtId)

                # EndToEndId
                EndToEndId = doc.createElement("EndToEndId")
                PmtId.appendChild(EndToEndId)
                if self.lot.modele.format == "public_dft":
                    endtoend = "1D%s0%s" % (self.lot.modele.poste_comptable, transaction_id)
                    EndToEndId.appendChild(doc.createTextNode(endtoend))
                else:
                    EndToEndId.appendChild(doc.createTextNode(transaction_id))

                # InstdAmt
                InstdAmt = doc.createElement("InstdAmt")
                DrctDbtTxInf.appendChild(InstdAmt)
                InstdAmt.appendChild(doc.createTextNode(str(transaction.montant)))
                InstdAmt.setAttribute("Ccy", "EUR")

                # DrctDbtTx
                DrctDbtTx = doc.createElement("DrctDbtTx")
                DrctDbtTxInf.appendChild(DrctDbtTx)

                # MndtRltdInf
                MndtRltdInf = doc.createElement("MndtRltdInf")
                DrctDbtTx.appendChild(MndtRltdInf)

                # MndtId
                MndtId = doc.createElement("MndtId")
                MndtRltdInf.appendChild(MndtId)
                MndtId.appendChild(doc.createTextNode(transaction.mandat.rum))

                # DtOfSgntr
                DtOfSgntr = doc.createElement("DtOfSgntr")
                MndtRltdInf.appendChild(DtOfSgntr)
                DtOfSgntr.appendChild(doc.createTextNode(str(transaction.mandat.date)))

                # AmdmntInd
                AmdmntInd = doc.createElement("AmdmntInd")
                MndtRltdInf.appendChild(AmdmntInd)
                AmdmntInd.appendChild(doc.createTextNode("false"))

                # DbtrAgt
                DbtrAgt = doc.createElement("DbtrAgt")
                DrctDbtTxInf.appendChild(DbtrAgt)

                # FinInstnId
                FinInstnId = doc.createElement("FinInstnId")
                DbtrAgt.appendChild(FinInstnId)

                # Dbtr
                BIC = doc.createElement("BIC")
                FinInstnId.appendChild(BIC)
                BIC.appendChild(doc.createTextNode(transaction.mandat.bic))

                # Dbtr
                Dbtr = doc.createElement("Dbtr")
                DrctDbtTxInf.appendChild(Dbtr)

                # Nm
                Nm = doc.createElement("Nm")
                Dbtr.appendChild(Nm)
                titulaire = transaction.mandat.individu.Get_nom() if transaction.mandat.individu else transaction.mandat.individu_nom
                Nm.appendChild(doc.createTextNode(utils_texte.Supprimer_accents(titulaire[:70])))

                # DbtrAcct
                DbtrAcct = doc.createElement("DbtrAcct")
                DrctDbtTxInf.appendChild(DbtrAcct)

                # Id
                Id = doc.createElement("Id")
                DbtrAcct.appendChild(Id)

                # IBAN
                IBAN = doc.createElement("IBAN")
                Id.appendChild(IBAN)
                IBAN.appendChild(doc.createTextNode(transaction.mandat.iban))

                if self.lot.modele.format == "public_dft":
                    # RmtInf
                    RmtInf = doc.createElement("RmtInf")
                    DrctDbtTxInf.appendChild(RmtInf)

                    # Ustrd
                    Ustrd = doc.createElement("Ustrd")
                    RmtInf.appendChild(Ustrd)
                    Ustrd.appendChild(doc.createTextNode(self.lot.motif))

        # Génération du XML
        xml = doc.toprettyxml(encoding=self.lot.modele.encodage.upper())

        # Validation XSD
        validation = self.ValidationXSD(xml)
        if not validation:
            return False

        # Enregistrement du fichier XML
        self.nom_fichier += ".xml"
        f = open(os.path.join(self.rep_destination, self.nom_fichier), "wb")
        f.write(xml)
        f.close()

        return True

    def ValidationXSD(self, xml=""):
        try:
            # Téléchargement du fichier XSD
            url = "http://www.noethys.com/fichiers/sepa/schema_sepa.zip"
            rep_temp = utils_fichiers.GetTempRep()
            nom_fichier = os.path.join(rep_temp, "schema_sepa.zip")
            urlretrieve(url, nom_fichier)

            # Décompression du zip XSD
            z = zipfile.ZipFile(nom_fichier, 'r')
            rep_dest = utils_fichiers.GetTempRep() + "/schema_sepa"
            z.extractall(rep_dest)
            z.close()

            # Lecture du XSD
            from lxml import etree
            fichier = rep_dest + "/pain.008.001.02.xsd"
            xmlschema_doc = etree.parse(fichier)
            xsd = etree.XMLSchema(xmlschema_doc)

            # Lecture du XML
            doc = etree.parse(BytesIO(xml))

            # Validation du XML avec le XSD
            if xsd.validate(doc):
                return True

            # Affichage des erreurs
            for error in xsd.error_log:
                self.erreurs.append("Ligne %d : %s" % (error.line, error.message))
            return False

        except Exception as err:
            print("Erreur dans validation XSD :")
            print(err)
            return True
