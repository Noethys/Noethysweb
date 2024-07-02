# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, calendar, datetime, uuid, zipfile
from urllib.request import urlretrieve
from xml.dom.minidom import Document
from lxml import etree
from io import BytesIO
from django.conf import settings
from core.models import PesLot, PesPiece, Organisateur
from core.utils import utils_texte, utils_fichiers
from noethysweb.version import GetVersion


def ConvertToTexte(valeur, majuscules=False):
    if majuscules and valeur:
        valeur = utils_texte.Supprimer_accents(valeur.upper())
    valeur = valeur.replace("\n", " ")
    valeur = valeur.replace("\r", " ")
    valeur = valeur.strip()
    return valeur


class Exporter():
    def __init__(self, idlot=None, request=None):
        self.idlot = idlot
        self.request = request
        self.organisateur = Organisateur.objects.filter(pk=1).first()
        self.erreurs = []

    def Generer(self):
        # Importation des données
        self.lot = PesLot.objects.select_related("modele", "modele__compte", "modele__mode").get(pk=self.idlot)
        self.pieces = PesPiece.objects.select_related("famille", "prelevement_mandat", "titulaire_helios", "facture").filter(lot=self.lot)

        # Création du répertoire de sortie
        self.rep_base = os.path.join("temp", str(uuid.uuid4()))
        self.rep_destination = os.path.join(settings.MEDIA_ROOT, self.rep_base, "pes")
        os.makedirs(self.rep_destination)

        # Création du nom du fichier
        self.nom_fichier = "export.xml"

        # Création des fichiers
        if not self.Creation_fichiers():
            return False

        return os.path.join(settings.MEDIA_URL, self.rep_base, "pes", self.nom_fichier)

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
        # Vérifie que des pièces existent
        if not self.pieces:
            self.erreurs.append("Vous devez ajouter au moins une pièce.")
            return False

        # Génération du XML
        doc = Document()

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
        TypFic.setAttribute("V", "PESORMC")
        Parametres.appendChild(TypFic)

        NomFic = doc.createElement("NomFic")
        NomFic.setAttribute("V", self.nom_fichier[:100])
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

        IdPost = doc.createElement("IdPost")
        IdPost.setAttribute("V", self.lot.modele.id_poste[:7])
        EnTetePES.appendChild(IdPost)

        IdColl = doc.createElement("IdColl")
        IdColl.setAttribute("V", self.lot.modele.id_collectivite[:14])
        EnTetePES.appendChild(IdColl)

        CodCol = doc.createElement("CodCol")
        CodCol.setAttribute("V", self.lot.modele.code_collectivite[:3])
        EnTetePES.appendChild(CodCol)

        CodBud = doc.createElement("CodBud")
        CodBud.setAttribute("V", self.lot.modele.code_budget[:10])
        EnTetePES.appendChild(CodBud)

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
        InfoDematerialisee.setAttribute("V", "0")
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

        IdBord = doc.createElement("IdBord")
        IdBord.setAttribute("V", self.lot.id_bordereau[:7])
        BlocBordereau.appendChild(IdBord)

        DteBordEm = doc.createElement("DteBordEm")
        DteBordEm.setAttribute("V", self.lot.date_emission.strftime("%Y-%m-%d"))
        BlocBordereau.appendChild(DteBordEm)

        TypBord = doc.createElement("TypBord")
        TypBord.setAttribute("V", "06")
        BlocBordereau.appendChild(TypBord)

        NbrPce = doc.createElement("NbrPce")
        NbrPce.setAttribute("V", str(len(self.pieces)))
        BlocBordereau.appendChild(NbrPce)

        MtBordHt = doc.createElement("MtBordHt")
        MtBordHt.setAttribute("V", str(sum([piece.montant for piece in self.pieces])))
        BlocBordereau.appendChild(MtBordHt)

        DteAsp = doc.createElement("DteAsp")
        DteAsp.setAttribute("V", self.lot.date_envoi.strftime("%Y-%m-%d"))
        BlocBordereau.appendChild(DteAsp)

        Objet = doc.createElement("Objet")
        Objet.setAttribute("V", ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece)[:160], majuscules=True))
        BlocBordereau.appendChild(Objet)

        for piece in self.pieces:

            # Pièce
            Piece = doc.createElement("Piece")
            Bordereau.appendChild(Piece)

            BlocPiece = doc.createElement("BlocPiece")
            Piece.appendChild(BlocPiece)

            IdPce = doc.createElement("IdPce")
            IdPce.setAttribute("V", str(piece.pk))
            BlocPiece.appendChild(IdPce)

            TypPce = doc.createElement("TypPce")
            TypPce.setAttribute("V", "15")
            BlocPiece.appendChild(TypPce)

            NatPce = doc.createElement("NatPce")
            NatPce.setAttribute("V", "01")
            BlocPiece.appendChild(NatPce)

            ObjPce = doc.createElement("ObjPce")
            ObjPce.setAttribute("V", ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece, piece=piece)[:160], majuscules=True))
            BlocPiece.appendChild(ObjPce)

            NumDette = doc.createElement("NumDette")
            NumDette.setAttribute("V", str(piece.facture.numero)[:15])
            BlocPiece.appendChild(NumDette)

            Per = doc.createElement("Per")
            Per.setAttribute("V", str(self.lot.mois)[:1])
            BlocPiece.appendChild(Per)

            Cle1 = doc.createElement("Cle1")
            cle1 = self.Get_cle_modulo_11([
                self.lot.modele.code_collectivite, self.lot.id_bordereau, str(self.lot.exercice)[-2:],
                str(self.lot.mois), "{:0>13}".format(str(piece.facture.numero))
            ])
            Cle1.setAttribute("V", str(cle1))
            BlocPiece.appendChild(Cle1)

            Cle2 = doc.createElement("Cle2")
            cle2 = Get_cle_modulo_23([
                str(self.lot.exercice)[-2:], str(self.lot.mois), "00",
                "{:0>13}".format(str(piece.facture.numero))
            ])
            Cle2.setAttribute("V", cle2)
            BlocPiece.appendChild(Cle2)

            NumeroFacture = doc.createElement("NumeroFacture")
            NumeroFacture.setAttribute("V", str(piece.facture.numero)[:20])
            BlocPiece.appendChild(NumeroFacture)

            # Ligne de pièce
            LigneDePiece = doc.createElement("LigneDePiece")
            Piece.appendChild(LigneDePiece)

            BlocLignePiece = doc.createElement("BlocLignePiece")
            LigneDePiece.appendChild(BlocLignePiece)

            InfoLignePiece = doc.createElement("InfoLignePiece")
            BlocLignePiece.appendChild(InfoLignePiece)

            IdLigne = doc.createElement("IdLigne")
            IdLigne.setAttribute("V", "1")
            InfoLignePiece.appendChild(IdLigne)

            ObjLignePce = doc.createElement("ObjLignePce")
            ObjLignePce.setAttribute("V", ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece, piece=piece)[:160], majuscules=True))
            InfoLignePiece.appendChild(ObjLignePce)

            CodProdLoc = doc.createElement("CodProdLoc")
            CodProdLoc.setAttribute("V", self.lot.modele.code_prodloc[:4])
            InfoLignePiece.appendChild(CodProdLoc)

            Nature = doc.createElement("Nature")
            Nature.setAttribute("V", "588")
            InfoLignePiece.appendChild(Nature)

            Majo = doc.createElement("Majo")
            Majo.setAttribute("V", "0")
            InfoLignePiece.appendChild(Majo)

            TvaIntraCom = doc.createElement("TvaIntraCom")
            TvaIntraCom.setAttribute("V", "0")
            InfoLignePiece.appendChild(TvaIntraCom)

            MtHT = doc.createElement("MtHT")
            MtHT.setAttribute("V", str(piece.montant))
            InfoLignePiece.appendChild(MtHT)

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
                MtPrel.setAttribute("V", str(piece.montant))
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
                LibPrel.setAttribute("V", ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.prelevement_libelle, piece=piece)[:140], majuscules=True))
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

            if piece.famille.natidtiers_helios and piece.famille.natidtiers_helios != 9999:
                NatIdTiers = doc.createElement("NatIdTiers")
                NatIdTiers.setAttribute("V", "" if piece.famille.natidtiers_helios == 9999 else piece.famille.natidtiers_helios)
                InfoTiers.appendChild(NatIdTiers)

            if piece.famille.reftiers_helios:
                RefTiers = doc.createElement("RefTiers")
                RefTiers.setAttribute("V", "%02d" % piece.famille.reftiers_helios)
                InfoTiers.appendChild(RefTiers)

            CatTiers = doc.createElement("CatTiers")
            if not piece.famille.cattiers_helios:
                self.erreurs.append("Vous devez renseigner la catégorie de tiers pour %s" % piece.famille)
                return False
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
            Nom.setAttribute("V", ConvertToTexte(piece.famille.titulaire_helios.nom[:38], majuscules=True))
            InfoTiers.appendChild(Nom)

            prenom = piece.famille.titulaire_helios.prenom
            if prenom:
                Prenom = doc.createElement("Prenom")
                Prenom.setAttribute("V", ConvertToTexte(prenom[:38], majuscules=True))
                InfoTiers.appendChild(Prenom)

            # Adresse
            Adresse = doc.createElement("Adresse")
            Tiers.appendChild(Adresse)

            TypAdr = doc.createElement("TypAdr")
            TypAdr.setAttribute("V", "1")
            Adresse.appendChild(TypAdr)

            Adr2 = doc.createElement("Adr2")
            Adr2.setAttribute("V", ConvertToTexte((piece.famille.titulaire_helios.rue_resid or "")[:38], majuscules=True))
            Adresse.appendChild(Adr2)

            CP = doc.createElement("CP")
            CP.setAttribute("V", (piece.famille.titulaire_helios.cp_resid or "")[:5])
            Adresse.appendChild(CP)

            Ville = doc.createElement("Ville")
            Ville.setAttribute("V", ConvertToTexte((piece.famille.titulaire_helios.ville_resid or "")[:38], majuscules=True))
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
                TitCpte.setAttribute("V", ConvertToTexte(individu_mandat[:32], majuscules=True))
                CpteBancaire.appendChild(TitCpte)

        # Génération du XML
        xml = doc.toprettyxml(indent="  ", encoding="ISO-8859-1")

        # Validation XSD
        validation = self.ValidationXSD(xml)
        if not validation:
            return False

        # Enregistrement du fichier XML
        f = open(os.path.join(self.rep_destination, self.nom_fichier), "wb")
        f.write(xml)
        f.close()

        return True

    def Get_cle_modulo_11(self, elements=[]):
        """ Calcul de la clé Modulo 11 """
        nombre = "".join(elements)[::-1]
        coefficients = [2, 3, 4, 5, 6, 7] * (len(nombre) // 6 + 1)
        total = 0
        index = 0
        for chiffre in nombre:
            if chiffre not in "0123456789": chiffre = "0"
            total += int(chiffre) * coefficients[index]
            index += 1
        if total % 11 == 0:
            pass
        cle = 11 - (total % 11)
        if cle > 9: cle = 1
        return cle

    def ValidationXSD(self, xml=""):
        try :
            # Téléchargement du fichier XSD
            fichier_dest = os.path.join(utils_fichiers.GetTempRep(), "schemas_pes.zip")
            urlretrieve("https://www.noethys.com/fichiers/pes/schemas_pes.zip", fichier_dest)

            # Décompression du zip XSD
            z = zipfile.ZipFile(fichier_dest, "r")
            rep_dest = os.path.join(utils_fichiers.GetTempRep(), "schemas_pes")
            z.extractall(rep_dest)
            z.close()

            # Lecture du XSD
            fichier_pes = rep_dest + "/Schemas_PES/PES_V2/Rev0/PES_Aller.xsd"
            xmlschema_doc = etree.parse(fichier_pes)
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


def Get_cle_modulo_23(elements=[]):
    """ Calcul de la clé Modulo 23 """
    nombre = "".join(elements)
    k = (int(nombre) % 23) + 1
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXY"
    cle = alphabet[k-1]
    return cle
