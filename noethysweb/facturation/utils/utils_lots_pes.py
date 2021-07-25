# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.conf import settings
from core.models import PesLot, PesPiece, Prestation, Organisateur, LISTE_MOIS
from core.utils import utils_dates, utils_parametres
from dateutil.relativedelta import relativedelta
import os, calendar, datetime, shutil, uuid


def ConvertToTexte(valeur):
    return '"%s"' % valeur


class Exporter():
    def __init__(self, idlot=None):
        self.idlot = idlot
        self.organisateur = Organisateur.objects.filter(pk=1).first()
        self.erreurs = []

    def Generer(self):
        # Importation des données
        self.lot = PesLot.objects.select_related("modele", "modele__compte", "modele__mode").get(pk=self.idlot)
        self.pieces = PesPiece.objects.select_related("famille", "prelevement_mandat", "titulaire_helios", "facture").filter(lot=self.lot)

        # Création du répertoire de sortie
        self.rep_base = os.path.join("temp", str(uuid.uuid4()))
        self.rep_destination = os.path.join(settings.MEDIA_ROOT, self.rep_base, "magnus")
        os.makedirs(self.rep_destination)

        # Création des fichiers
        if not self.Creation_fichiers():
            return False

        # Création du fichier ZIP
        nom_fichier_zip = self.lot.nom + ".zip"
        shutil.make_archive(os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_fichier_zip.replace(".zip", "")), "zip", self.rep_destination)

        return os.path.join(settings.MEDIA_URL, self.rep_base, nom_fichier_zip)

    def Get_detail_pieces(self):
        prestations = Prestation.objects.select_related("activite", "individu").filter(facture_id__in=[piece.facture_id for piece in self.pieces])

        dict_resultats = {}
        dict_prestations_factures = {}
        for prestation in prestations:

            # Recherche le code compta et le code prod local
            id_poste = self.lot.modele.id_poste
            code_prodloc = self.lot.modele.code_prodloc
            if prestation.activite.code_comptable: id_poste = prestation.activite.code_comptable
            if prestation.activite.code_produit_local: code_prodloc = prestation.activite.code_produit_local
            if prestation.code_compta: id_poste = prestation.code_compta
            if prestation.code_produit_local: code_prodloc = prestation.code_produit_local

            dict_prestations_factures.setdefault(prestation.facture, [])
            dict_prestations_factures[prestation.facture].append({"prestation": prestation, "label": prestation.label, "montant": prestation.montant, "id_poste": id_poste, "code_prodloc": code_prodloc})

            # Définit le montant
            montant_unitaire = prestation.montant / prestation.quantite

            # Spécial
            if "portage" in prestation.activite.nom.lower():
                prestation.date = prestation.date - relativedelta(months=1)

            # Définit le label
            libelle = self.lot.modele.prestation_libelle
            libelle = libelle.replace("{ACTIVITE_NOM}", prestation.activite.nom)
            libelle = libelle.replace("{ACTIVITE_ABREGE}", prestation.activite.abrege if prestation.activite.abrege else "")
            libelle = libelle.replace("{PRESTATION_LABEL}", prestation.label)
            libelle = libelle.replace("{PRESTATION_QUANTITE}", str(prestation.quantite))
            libelle = libelle.replace("{PRESTATION_MOIS}", {num: label for (num, label) in LISTE_MOIS}[prestation.date.month])
            libelle = libelle.replace("{PRESTATION_ANNEE}", str(prestation.date.year))
            libelle = libelle.replace("{INDIVIDU_PRENOM}", prestation.individu.prenom if prestation.individu.prenom else "")
            libelle = libelle.replace("{INDIVIDU_NOM}", prestation.individu.nom if prestation.individu.nom else "")
            libelle = libelle.replace("{MOIS}", str(self.lot.mois))
            libelle = libelle.replace("{MOIS_LETTRES}", self.lot.get_mois_display())
            libelle = libelle.replace("{ANNEE}", str(self.lot.exercice))

            # Mémorisation du label et de la quantité
            libelle = (libelle, montant_unitaire)
            dict_resultats.setdefault(prestation.facture, {})
            dict_resultats[prestation.facture].setdefault(prestation.individu, {})
            dict_resultats[prestation.facture][prestation.individu].setdefault(libelle, 0)
            dict_resultats[prestation.facture][prestation.individu][libelle] += prestation.quantite

        dict_resultats2 = {}
        for facture, dict_facture in dict_resultats.items():
            dict_resultats2.setdefault(facture, [])
            for individu, dict_individu in dict_facture.items():
                for (libelle, montant), quantite in dict_individu.items():
                    dict_resultats2[facture].append({"libelle": libelle, "quantite": quantite, "montant": montant})
                dict_resultats2[facture].sort(key=lambda x: x["libelle"])

        return dict_resultats2, dict_prestations_factures

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
        texte = texte.replace("{NUM_FACTURE}", str(piece.facture.numero))
        texte = texte.replace("{MOIS}", str(self.lot.mois))
        texte = texte.replace("{MOIS_LETTRES}", self.lot.get_mois_display())
        texte = texte.replace("{ANNEE}", str(self.lot.exercice))
        return texte

    def Generation_pieces_jointes(self, repertoire=""):
        """ Génération des pièces jointes """
        dict_factures = {piece.facture_id: piece.facture for piece in self.pieces}

        # Création du répertoire
        repertoire_pj = os.path.join(self.rep_destination, "PJ")
        if not os.path.isdir(repertoire_pj):
            os.mkdir(repertoire_pj)

        # Récupération des options d'impression
        from facturation.forms.factures_options_impression import VALEURS_DEFAUT
        dict_options = utils_parametres.Get_categorie(categorie="impression_facture", parametres=VALEURS_DEFAUT)
        dict_options["modele"] = self.lot.modele.modele_document

        # Génération des factures du format PDF
        from facturation.utils import utils_facturation
        facturation = utils_facturation.Facturation()
        resultat = facturation.Impression(liste_factures=list(dict_factures.keys()), dict_options=dict_options, mode_email=True)
        if resultat == False:
            return False

        # Déplacement des PDF vers le répertoire PJ
        dict_pieces_jointes = {}
        for IDfacture, donnees in resultat["noms_fichiers"].items():
            NomPJ = "Facture_%s.pdf" % dict_factures[IDfacture].numero
            numero_facture = dict_factures[IDfacture].numero
            IdUnique = str(numero_facture)
            shutil.move(settings.MEDIA_ROOT + donnees["nom_fichier"], os.path.join(repertoire_pj, NomPJ))
            dict_pieces_jointes[IDfacture] = {"NomPJ": NomPJ, "IdUnique": IdUnique, "numero_facture": numero_facture}

        return dict_pieces_jointes

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

        # Calcul des dates extrêmes du mois
        date_min = datetime.date(self.lot.exercice, self.lot.mois, 1)
        date_max = datetime.date(self.lot.exercice, self.lot.mois, calendar.monthrange(self.lot.exercice, self.lot.mois)[1])

        # Récupération du détail des factures
        detail_factures, dict_prestations_factures = self.Get_detail_pieces()

        # Recherche poste et code local
        dict_codes = {}
        for facture, liste_prestations in dict_prestations_factures.items():
            dict_codes.setdefault(facture, {})
            for dict_prestation in liste_prestations:
                key = (dict_prestation["id_poste"], dict_prestation["code_prodloc"])
                dict_codes[facture].setdefault(key, 0)
                dict_codes[facture][key] += dict_prestation["montant"]

        # Génération des lignes des fichiers
        lignes = []
        lignes_pj = []
        lignes_detail = []
        for IdEcriture, piece in enumerate(self.pieces, start=1):
            num_sous_ligne = 1
            if piece.facture in dict_codes:
                for (IDposte, code_produit_local), montant in dict_codes[piece.facture].items():
                    ligne = {}

                    # IDEcriture - Texte (50)
                    ligne[1] = ConvertToTexte(IdEcriture)

                    # Type - Texte (1)
                    ligne[2] = ConvertToTexte("T")

                    # Reelle - Texte (1)
                    ligne[3] = ConvertToTexte("O")

                    # Collectivité - Texte (10)
                    ligne[4] = ConvertToTexte(self.lot.modele.code_collectivite[:10])

                    # Budget - Texte (10)
                    ligne[5] = ConvertToTexte(self.lot.modele.code_budget[:10])

                    # Exercice - Entier
                    ligne[6] = str(self.lot.exercice)

                    # Multiple - Texte (1)
                    ligne[7] = ConvertToTexte("M" if num_sous_ligne == 1 else "S")

                    # CodeTiers - Texte (15)
                    ligne[8] = ConvertToTexte("FAM%06d" % piece.famille_id)
                    if self.lot.modele.code_compta_as_alias and piece.famille.code_compta:
                        ligne[8] = ConvertToTexte(piece.famille.code_compta[:15])

                    # Designation1 - Texte (50)
                    ligne[10] = ConvertToTexte(piece.famille.titulaire_helios.nom[:50])

                    # Designation2 - Texte (50)
                    ligne[11] = ConvertToTexte(piece.famille.titulaire_helios.prenom[:50])

                    # AdrLig1 - Texte (50)
                    ligne[12] = ConvertToTexte(piece.famille.titulaire_helios.rue_resid[:50])

                    # Codepostal - Texte (10)
                    ligne[15] = ConvertToTexte(piece.famille.titulaire_helios.cp_resid[:10])

                    # Ville - Texte (50)
                    ligne[16] = ConvertToTexte(piece.famille.titulaire_helios.ville_resid[:50])

                    # Libelle1 - Texte (50)
                    ligne[18] = ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece, piece=piece)[:50])

                    # PièceJustificative1 - Texte (50)
                    pj = dict_pieces_jointes.get(piece.facture_id, None)
                    ligne[20] = ConvertToTexte(pj["NomPJ"][:50].replace(".pdf", "")) if pj else ""

                    # Sens - Texte (1)
                    ligne[24] = ConvertToTexte("R")

                    # Date - Texte (10)
                    ligne[25] = ConvertToTexte(utils_dates.ConvertDateToFR(self.lot.date_emission))

                    # Article - Texte (10)
                    ligne[26] = IDposte[:10]

                    # Opération - Texte (10)
                    ligne[27] = self.lot.modele.operation or ""

                    # Service - Texte (15)
                    ligne[28] = self.lot.modele.service1 or ""

                    # Fonction - Texte (10)
                    ligne[29] = self.lot.modele.fonction or ""

                    # Montant HT - Monétaire (,4)
                    ligne[30] = str(montant) + "00"

                    # Montant TVA - Monétaire (,4)
                    ligne[31] = "0.0000"

                    # Solder - O/N
                    ligne[32] = "0"

                    # Priorité - Entier
                    ligne[33] = "0"

                    # Accepté - O/N
                    ligne[35] = "0"

                    # Erroné - O/N
                    ligne[36] = "0"

                    # NJ - Texte (2)
                    ligne[38] = ConvertToTexte("%02d" % piece.famille.natjur_helios)

                    # TvaTaux - Reel Simple (5)
                    ligne[40] = "0.000000"

                    # Service 2 - Texte (10)
                    ligne[41] = self.lot.modele.service2 or ""

                    # Mixte - Texte (1)
                    ligne[44] = ConvertToTexte("N")

                    # Imprévisible - Texte (1)
                    ligne[45] = ConvertToTexte("N")

                    # CodeAlim - Texte (1)
                    ligne[46] = ConvertToTexte("N")

                    # MarcheSim - Texte (1)
                    ligne[47] = ConvertToTexte("N")

                    # SuiviDelai - Texte (1)
                    ligne[50] = ConvertToTexte("N")

                    # DelaiPaiement - Entier
                    ligne[51] = "0"

                    # CPL - Texte (4)
                    ligne[54] = code_produit_local[:4]

                    # Prélèvement :
                    if piece.prelevement:

                        # TitCpte - Texte (32)
                        individu_mandat = piece.prelevement_mandat.individu_nom or piece.prelevement_mandat.individu.Get_nom()
                        ligne[64] = ConvertToTexte(individu_mandat[:32])

                        # IBAN - Texte (34)
                        ligne[65] = ConvertToTexte(piece.prelevement_mandat.iban)

                        # BIC - Texte (11)
                        ligne[66] = ConvertToTexte(piece.prelevement_mandat.bic)

                    # Tribunal - Texte (100)
                    ligne[68] = ConvertToTexte(self.lot.modele.nom_tribunal[:100])

                    # TIPI - O/N
                    ligne[70] = ConvertToTexte("O" if self.lot.modele.payable_internet else "N")

                    # PrelevementSEPA - O/N
                    ligne[71] = ConvertToTexte("O" if piece.prelevement else "N")

                    # DatePrel - Texte (10)
                    if piece.prelevement:
                        ligne[72] = ConvertToTexte(utils_dates.ConvertDateToFR(self.lot.date_prelevement))

                        # PeriodicitePrel - Texte (2)
                        ligne[73] = ConvertToTexte("02") # Mensuel

                        # ICS - Texte (13)
                        ligne[74] = ConvertToTexte(self.lot.modele.compte.code_ics)

                        # RUM - Texte (35)
                        ligne[75] = ConvertToTexte(piece.prelevement_mandat.rum)

                    # RUMMigre - O/N
                    ligne[76] = ConvertToTexte("N")

                    # RUM - Texte (35)
                    if piece.prelevement:
                        ligne[77] = ConvertToTexte(utils_dates.ConvertDateToFR(piece.prelevement_mandat.date))

                        # LibellePrel - Texte (140)
                        ligne[78] = ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.prelevement_libelle, piece=piece)[:140])

                        # SequencePrel - Texte (02)
                        if piece.prelevement_sequence == "FRST": sequence = "02"
                        elif piece.prelevement_sequence == "RCUR": sequence = "03"
                        elif piece.prelevement_sequence == "FNAL": sequence = "04"
                        else: sequence = "01"
                        ligne[79] = ConvertToTexte(sequence)

                    # TitCpteDiff - O/N
                    ligne[80] = ConvertToTexte("N")

                    # AncienBanque - O/N
                    ligne[84] = ConvertToTexte("N")

                    # Version - Numérique (3)
                    ligne[90] = ConvertToTexte("19")

                    # CategorieTiersPES - Numérique (2)
                    ligne[91] = ConvertToTexte(piece.famille.cattiers_helios)

                    # NatJuridiqueTiersPES - Numérique (2)
                    ligne[92] = ConvertToTexte(piece.famille.natjur_helios)

                    # Civilité - Texte (32)
                    civilite_titulaire = piece.famille.titulaire_helios.Get_abrege_civilite()
                    if civilite_titulaire == "M.": ligne[93] = ConvertToTexte("M")
                    if civilite_titulaire == "Mme": ligne[93] = ConvertToTexte("MME")
                    if civilite_titulaire == "Melle": ligne[93] = ConvertToTexte("MLLE")

                    # NatIdentifiantTiers - Numérique (2)
                    ligne[94] = ConvertToTexte(piece.famille.natidtiers_helios)

                    # IdentifiantTiers - Texte (18)
                    ligne[95] = ConvertToTexte(piece.famille.idtiers_helios or "")

                    # CodeResident - Numérique (3)
                    ligne[97] = ConvertToTexte("0")

                    # TypeTiersPES - Numérique (2)
                    ligne[98] = ConvertToTexte("01")

                    # DatNaisTiers - Texte (10)
                    ligne[107] = ConvertToTexte(utils_dates.ConvertDateToFR(piece.famille.titulaire_helios.date_naiss)) if piece.famille.titulaire_helios.date_naiss else ""

                    # TitreASAP - O/N
                    ligne[108] = ConvertToTexte("O")

                    # TIP ASAP - O/N
                    ligne[109] = ConvertToTexte("N")

                    # NumeroFacture - Texte (50)
                    ligne[111] = ConvertToTexte(piece.facture.numero)

                    # EditionASAP - Numérique (2)
                    ligne[112] = ConvertToTexte(self.lot.modele.edition_asap)

                    # DateEnvoiASAP - Texte (10)
                    ligne[113] = ConvertToTexte(self.lot.date_envoi.strftime("%Y%m%d"))

                    # Formatage de la ligne
                    texte_ligne = ['""' for x in range(0, 123)]
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
                            ligne_detail[1] = ConvertToTexte("19")

                            # RefIdEcriture - Texte (50)
                            ligne_detail[2] = ligne[1]

                            # DateDebut - Date
                            ligne_detail[3] = ConvertToTexte(utils_dates.ConvertDateToFR(date_min))

                            # DateFin - Date
                            ligne_detail[4] = ConvertToTexte(utils_dates.ConvertDateToFR(date_max))

                            # Libelle - Texte (200)
                            ligne_detail[5] = ConvertToTexte(dict_detail["libelle"][:200])

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
                ligne_pj[2] = ConvertToTexte(pj["NomPJ"][:100])

                # DescriptionPJ - Texte (255)
                ligne_pj[3] = ConvertToTexte(self.Formate_libelle(texte=self.lot.modele.objet_piece, piece=piece)[:255])

                # TypPJPES - Texte (3)
                ligne_pj[4] = ConvertToTexte("006")

                # TypDoc - Texte (2)
                ligne_pj[6] = ConvertToTexte("02")

                # TypFichier - Texte (2)
                ligne_pj[7] = ConvertToTexte("06")

                # Version - Numérique (3)
                ligne_pj[8] = ConvertToTexte("19")

                # Formatage de la ligne PJ
                texte_ligne_pj = ['""' for x in range(0, 8)]
                for index, valeur in ligne_pj.items():
                    texte_ligne_pj[index-1] = valeur
                lignes_pj.append(";".join(texte_ligne_pj))

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

        return True
