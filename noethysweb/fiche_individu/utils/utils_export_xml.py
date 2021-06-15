# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import Famille, Piece, Cotisation, Prestation, Consommation, Facture, Reglement, Ventilation
from xml.dom.minidom import Document
from django.db.models import Sum
from decimal import Decimal
from core.utils import utils_infos_individus, utils_dates, utils_preferences, utils_fichiers
from django.conf import settings
from uuid import uuid4


class Export():
    def __init__(self, famille=None):
        """ si famille == None : Toutes les familles sont sélectionnées"""
        self.famille = famille

    def GetDoc(self):
        # Importation des pièces fournies
        pieces = Piece.objects.select_related('type_piece').filter(famille=self.famille)
        dictPieces = {"familles": {}, "individus": {}}
        for piece in pieces:
            dictPiece = {"IDpiece": piece.pk,
                         "nom_piece": piece.type_piece.nom,
                         "date_debut": piece.date_debut,
                         "date_fin": piece.date_fin
                         }
            if piece.type_piece.public == "famille":
                if self.famille.pk not in dictPieces["familles"]:
                    dictPieces["familles"][self.famille.pk] = []
                dictPieces["familles"][self.famille.pk].append(dictPiece)
            if piece.type_piece.public == "individu" :
                if piece.individu.pk not in dictPieces["individus"]:
                    dictPieces["individus"][piece.individu.pk] = []
                dictPieces["individus"][piece.individu.pk].append(dictPiece)

        # Importation des cotisations
        cotisations = Cotisation.objects.select_related('type_cotisation').filter(famille=self.famille)
        dictCotisations = {"familles": {}, "individus": {}}
        for cotisation in cotisations:
            if cotisation.type_cotisation.type == "famille":
                if cotisation.famille_id not in dictCotisations["familles"]:
                    dictCotisations["familles"][cotisation.famille_id] = []
                dictCotisations["familles"][cotisation.famille_id].append(cotisation)
            if cotisation.type_cotisation.type == "individu" :
                if cotisation.individu_id not in dictCotisations["individus"]:
                    dictCotisations["individus"][cotisation.individu_id] = []
                dictCotisations["individus"][cotisation.individu_id].append(cotisation)

        # # Importation des prestations
        prestations = Prestation.objects.select_related('facture', 'activite', 'individu').filter(famille=self.famille)
        dictPrestations = {}
        for prestation in prestations:
            dictPrestations.setdefault(prestation.famille_id, [])
            dictPrestations[prestation.famille_id].append(prestation)

        # Importation des consommations
        consommations = Consommation.objects.select_related('activite', 'inscription', 'unite').filter(inscription__famille=self.famille)
        dictConsommations = {}
        for conso in consommations:
            dictConso = {"IDconso": conso.pk, "date": conso.date, "nomActivite": conso.activite.nom, "etat": conso.etat, "nomUnite": conso.unite.nom}
            dictConsommations.setdefault(conso.inscription.famille_id, {})
            dictConsommations[conso.inscription.famille_id].setdefault(conso.individu_id, [])
            dictConsommations[conso.inscription.famille_id][conso.individu_id].append(dictConso)

        # Importation des factures

        # Récupération des totaux des prestations pour chaque facture
        prestations = Prestation.objects.values('facture').filter(famille=self.famille).annotate(total=Sum("montant"))
        dictPrestationsFactures = {}
        for donnee in prestations:
            if donnee["facture"]:
                dictPrestationsFactures[donnee["facture"]] = donnee["total"]

        # Récupération de la ventilation
        ventilations = Ventilation.objects.values('prestation__facture').filter(famille=self.famille).annotate(total=Sum("montant"))
        dictVentilationFactures = {}
        for donnee in ventilations:
            if donnee["prestation__facture"]:
                dictVentilationFactures[donnee["prestation__facture"]] = donnee["total"]

        # Récupération des factures
        factures = Facture.objects.filter(famille=self.famille)
        dictFactures = {}
        for facture in factures:
            totalVentilation = dictVentilationFactures.get(facture.pk, Decimal(0))
            totalPrestations = dictPrestationsFactures.get(facture.pk, Decimal(0))
            solde_actuel = totalPrestations - totalVentilation
            dictFacture = {
                "IDfacture": facture.pk, "numero": facture.numero, "date_edition": facture.date_edition, "date_debut": facture.date_debut,
                "date_fin": facture.date_fin, "montant": float(totalPrestations), "montant_regle": float(totalVentilation),
                "montant_solde": float(solde_actuel),
                }
            dictFactures.setdefault(facture.famille_id, [])
            dictFactures[facture.famille_id].append(dictFacture)

        # Importation des règlements
        reglements = Reglement.objects.select_related('mode', 'emetteur', 'mode', 'payeur').filter(famille=self.famille)
        dictReglements = {}
        for reglement in reglements:
            dictReglements.setdefault(reglement.famille_id, [])
            dictReglements[reglement.famille_id].append(reglement)

        # Récupération des infos individus
        infos = utils_infos_individus.Informations()

        # Génération du XML
        doc = Document()

        # Racine Familles
        node_racine = doc.createElement("familles")
        doc.appendChild(node_racine)

        for IDfamille in [self.famille.pk,]:

            # Famille : Infos générales
            node_famille = doc.createElement("famille")
            node_famille.setAttribute("id", str(IDfamille))
            node_racine.appendChild(node_famille)

            # for key, valeur in infos.dictFamilles[IDfamille].items():
            #     if key.startswith("FAMILLE_"):
            #         node = doc.createElement(key.replace("FAMILLE_", "").lower())
            #         node.setAttribute("valeur", six.text_type(valeur))
            #         node_famille.appendChild(node)
            #
            # # Famille : Quotients
            # if "qf" in infos.dictFamilles[IDfamille]:
            #     node_qf = doc.createElement(u"quotients_familiaux")
            #     node_famille.appendChild(node_qf)
            #
            #     for dictQF in infos.dictFamilles[IDfamille]["qf"]:
            #         node = doc.createElement(u"quotient")
            #         node.setAttribute("date_debut", dictQF["date_debut"])
            #         node.setAttribute("date_fin", dictQF["date_fin"])
            #         node.setAttribute("quotient", str(dictQF["quotient"]))
            #         node.setAttribute("observations", dictQF["observations"])
            #         node_qf.appendChild(node)
            #
            # # Famille : Messages
            # if "messages" in infos.dictFamilles[IDfamille]:
            #     node_messages = doc.createElement(u"messages")
            #     node_famille.appendChild(node_messages)
            #
            #     for dictMessage in infos.dictFamilles[IDfamille]["messages"]["liste"]:
            #         node = doc.createElement(u"message")
            #         node.setAttribute("categorie_nom", dictMessage["categorie_nom"])
            #         node.setAttribute("date_saisie", dictMessage["date_saisie"])
            #         node.setAttribute("date_parution", dictMessage["date_parution"])
            #         node.setAttribute("nom", dictMessage["nom"])
            #         node.setAttribute("texte", dictMessage["texte"])
            #         node_messages.appendChild(node)
            #
            # # Famille : Questionnaires
            # if "questionnaires" in infos.dictFamilles[IDfamille]:
            #     node_questionnaires = doc.createElement(u"questionnaires")
            #     node_famille.appendChild(node_questionnaires)
            #
            #     for dictQuestionnaire in infos.dictFamilles[IDfamille]["questionnaires"]:
            #         node = doc.createElement(u"questionnaire")
            #         node.setAttribute("question", dictQuestionnaire["label"])
            #         node.setAttribute("reponse", six.text_type(dictQuestionnaire["reponse"]))
            #         node_questionnaires.appendChild(node)

            # Famille : Pièces
            if IDfamille in dictPieces["familles"]:
                node_pieces = doc.createElement("pieces")
                node_famille.appendChild(node_pieces)

                for dictPiece in dictPieces["familles"][IDfamille]:
                    node = doc.createElement("piece")
                    node.setAttribute("nom_piece", dictPiece["nom_piece"])
                    node.setAttribute("date_debut", utils_dates.ConvertDateToFR(dictPiece["date_debut"]))
                    node.setAttribute("date_fin", utils_dates.ConvertDateToFR(dictPiece["date_fin"]))
                    node_pieces.appendChild(node)

            # Famille : Cotisations
            if IDfamille in dictCotisations["familles"]:
                node_cotisations = doc.createElement(u"cotisations")
                node_famille.appendChild(node_cotisations)

                for cotisation in dictCotisations["familles"][IDfamille]:
                    node = doc.createElement(u"cotisation")
                    node.setAttribute("date_saisie", utils_dates.ConvertDateToFR(cotisation.date_saisie))
                    node.setAttribute("date_creation_carte", utils_dates.ConvertDateToFR(cotisation.date_creation_carte))
                    node.setAttribute("date_debut", utils_dates.ConvertDateToFR(cotisation.date_debut))
                    node.setAttribute("date_fin", utils_dates.ConvertDateToFR(cotisation.date_fin))
                    node.setAttribute("numero", cotisation.numero)
                    node.setAttribute("type_cotisation", cotisation.type_cotisation.nom)
                    node.setAttribute("nom_unite_cotisation", cotisation.unite_cotisation.nom)
                    node.setAttribute("observations", cotisation.observations)
                    node_cotisations.appendChild(node)

            # Famille : Prestations
            if IDfamille in dictPrestations:
                node_prestations = doc.createElement(u"prestations")
                node_famille.appendChild(node_prestations)

                for prestation in dictPrestations[IDfamille]:
                    node = doc.createElement(u"prestation")
                    node.setAttribute("date", utils_dates.ConvertDateToFR(prestation.date))
                    node.setAttribute("label", prestation.label)
                    node.setAttribute("devise", utils_preferences.Get_symbole_monnaie())
                    node.setAttribute("montant", "%.2f" % prestation.montant)
                    if prestation.activite:
                        node.setAttribute("activite", prestation.activite.nom)
                    if prestation.individu:
                        node.setAttribute("prenom", prestation.individu.prenom)
                    node_prestations.appendChild(node)

                # Famille : Factures
                if IDfamille in dictFactures:
                    node_factures = doc.createElement(u"factures")
                    node_famille.appendChild(node_factures)

                    for dictFacture in dictFactures[IDfamille]:
                        node = doc.createElement(u"facture")
                        node.setAttribute("date_edition", utils_dates.ConvertDateToFR(dictFacture["date_edition"]))
                        node.setAttribute("date_debut", utils_dates.ConvertDateToFR(dictFacture["date_debut"]))
                        node.setAttribute("date_fin", utils_dates.ConvertDateToFR(dictFacture["date_fin"]))
                        node.setAttribute("numero_facture", str(dictFacture["numero"]))
                        node.setAttribute("devise", utils_preferences.Get_symbole_monnaie())
                        node.setAttribute("montant", "%.2f" % dictFacture["montant"])
                        node.setAttribute("montant_regle", "%.2f" % dictFacture["montant_regle"])
                        node.setAttribute("montant_solde", "%.2f" % dictFacture["montant_solde"])
                        node_factures.appendChild(node)

                # Famille : Règlements
                if IDfamille in dictReglements:
                    node_reglements = doc.createElement(u"reglements")
                    node_famille.appendChild(node_reglements)

                    for reglement in dictReglements[IDfamille]:
                        node = doc.createElement(u"reglement")
                        node.setAttribute("date", utils_dates.ConvertDateToFR(reglement.date))
                        node.setAttribute("date_differe", utils_dates.ConvertDateToFR(reglement.date_differe))
                        node.setAttribute("date_saisie", utils_dates.ConvertDateToFR(reglement.date_saisie))
                        node.setAttribute("mode", reglement.mode.label)
                        if reglement.emetteur:
                            node.setAttribute("emetteur", reglement.emetteur.nom)
                        if reglement.numero_piece:
                            node.setAttribute("numero_piece", reglement.numero_piece)
                        node.setAttribute("devise", utils_preferences.Get_symbole_monnaie())
                        node.setAttribute("montant", u"%.2f" % reglement.montant)
                        node.setAttribute("payeur", reglement.payeur.nom)
                        node.setAttribute("observations", reglement.observations)
                        node.setAttribute("numero_quittancier", reglement.numero_quittancier)
                        node_reglements.appendChild(node)




            # Individus
            # node_individus = doc.createElement(u"individus")
            # node_famille.appendChild(node_individus)
            #
            # if IDfamille in infos.dictRattachements["familles"]:
            #     for dictRattachement in infos.dictRattachements["familles"][IDfamille]:
            #         IDindividu = dictRattachement["IDindividu"]
            #
            #         node_individu = doc.createElement(u"individu")
            #         node_individu.setAttribute("id", str(IDindividu))
            #         node_individus.appendChild(node_individu)
            #
            #         # Individu : données générales
            #         for key, champ in infos.GetListeChampsIndividus():
            #             valeur = infos.dictIndividus[IDindividu][key]
            #             if isinstance(valeur, (six.text_type, str)):
            #                 node = doc.createElement(key.replace("INDIVIDU_", "").lower())
            #                 node.setAttribute("valeur", six.text_type(valeur))
            #                 node_individu.appendChild(node)
            #
            #         # Individu : Messages
            #         if "messages" in infos.dictIndividus[IDindividu]:
            #             node_messages = doc.createElement(u"messages")
            #             node_individu.appendChild(node_messages)
            #
            #             for dictMessage in infos.dictIndividus[IDindividu]["messages"]["liste"]:
            #                 node = doc.createElement(u"message")
            #                 node.setAttribute("categorie_nom", dictMessage["categorie_nom"])
            #                 node.setAttribute("date_saisie", dictMessage["date_saisie"])
            #                 node.setAttribute("date_parution", dictMessage["date_parution"])
            #                 node.setAttribute("nom", dictMessage["nom"])
            #                 node.setAttribute("texte", dictMessage["texte"])
            #                 node_messages.appendChild(node)
            #
            #         # Individu : Infos médicales
            #         if "medical" in infos.dictIndividus[IDindividu]:
            #             node_medicales = doc.createElement(u"infos_medicales")
            #             node_individu.appendChild(node_medicales)
            #
            #             for dictMedicale in infos.dictIndividus[IDindividu]["medical"]["liste"]:
            #                 node = doc.createElement(u"info_medicale")
            #                 node.setAttribute("intitule", dictMedicale["intitule"])
            #                 node.setAttribute("description", dictMedicale["description"])
            #                 node.setAttribute("description_traitement", dictMedicale["description_traitement"])
            #                 node.setAttribute("date_debut_traitement", dictMedicale["date_debut_traitement"])
            #                 node.setAttribute("date_fin_traitement", dictMedicale["date_fin_traitement"])
            #                 node_medicales.appendChild(node)
            #
            #         # Individu : Inscriptions
            #         if "inscriptions" in infos.dictIndividus[IDindividu]:
            #             node_inscriptions = doc.createElement(u"inscriptions")
            #             node_individu.appendChild(node_inscriptions)
            #
            #             for dictInscription in infos.dictIndividus[IDindividu]["inscriptions"]["liste"]:
            #                 node = doc.createElement(u"inscription")
            #                 node.setAttribute("activite", dictInscription["activite"])
            #                 node.setAttribute("groupe", dictInscription["groupe"])
            #                 node.setAttribute("categorie_tarif", dictInscription["categorie_tarif"])
            #                 node.setAttribute("parti", dictInscription["parti"])
            #                 node.setAttribute("date_inscription", dictInscription["date_inscription"])
            #                 node_inscriptions.appendChild(node)
            #
            #         # Individu : Questionnaires
            #         if "questionnaires" in infos.dictIndividus[IDindividu]:
            #             node_questionnaires = doc.createElement(u"questionnaires")
            #             node_individu.appendChild(node_questionnaires)
            #
            #             for dictQuestionnaire in infos.dictIndividus[IDindividu]["questionnaires"]:
            #                 node = doc.createElement(u"questionnaire")
            #                 node.setAttribute("question", dictQuestionnaire["label"])
            #                 node.setAttribute("reponse", six.text_type(dictQuestionnaire["reponse"]))
            #                 node_questionnaires.appendChild(node)
            #
            #         # Individu : Scolarité
            #         if "scolarite" in infos.dictIndividus[IDindividu]:
            #             node_scolarite = doc.createElement(u"scolarite")
            #             node_individu.appendChild(node_scolarite)
            #
            #             for dictScolarite in infos.dictIndividus[IDindividu]["scolarite"]["liste"]:
            #                 node = doc.createElement(u"etape")
            #                 node.setAttribute("date_debut", dictScolarite["date_debut"])
            #                 node.setAttribute("date_fin", dictScolarite["date_fin"])
            #                 node.setAttribute("ecole_nom", dictScolarite["ecole_nom"])
            #                 node.setAttribute("classe_nom", dictScolarite["classe_nom"])
            #                 node.setAttribute("niveau_nom", dictScolarite["niveau_nom"])
            #                 node.setAttribute("niveau_abrege", dictScolarite["niveau_abrege"])
            #                 node_scolarite.appendChild(node)
            #
            #         # Individu : Pièces
            #         if IDindividu in dictPieces["individus"]:
            #             node_pieces = doc.createElement(u"pieces")
            #             node_individu.appendChild(node_pieces)
            #
            #             for dictPiece in dictPieces["individus"][IDindividu]:
            #                 node = doc.createElement(u"piece")
            #                 node.setAttribute("nom_piece", dictPiece["nom_piece"])
            #                 node.setAttribute("date_debut", utils_dates.ConvertDateToFR(dictPiece["date_debut"]))
            #                 node.setAttribute("date_fin", utils_dates.ConvertDateToFR(dictPiece["date_fin"]))
            #                 node_pieces.appendChild(node)
            #
            #         # Individu : Cotisations
            #         if IDindividu in dictCotisations["individus"]:
            #             node_cotisations = doc.createElement(u"cotisations")
            #             node_individu.appendChild(node_cotisations)
            #
            #             for dictCotisation in dictCotisations["individus"][IDindividu]:
            #                 node = doc.createElement(u"cotisation")
            #                 node.setAttribute("date_saisie", UTILS_Dates.DateDDEnFr(dictCotisation["date_saisie"]))
            #                 node.setAttribute("date_creation_carte", utils_dates.ConvertDateToFR(dictCotisation["date_creation_carte"]))
            #                 node.setAttribute("date_debut", utils_dates.ConvertDateToFR(dictCotisation["date_debut"]))
            #                 node.setAttribute("date_fin", utils_dates.ConvertDateToFR(dictCotisation["date_fin"]))
            #                 node.setAttribute("numero", dictCotisation["numero"])
            #                 node.setAttribute("type_cotisation", dictCotisation["type_cotisation"])
            #                 node.setAttribute("nom_unite_cotisation", dictCotisation["nom_unite_cotisation"])
            #                 node.setAttribute("observations", dictCotisation["observations"])
            #                 node.setAttribute("activites", dictCotisation["activites"])
            #                 node_cotisations.appendChild(node)
            #
            #         # Individu : Consommations
            #         if IDfamille in dictConsommations:
            #             if IDindividu in dictConsommations[IDfamille]:
            #                 node_consommations = doc.createElement(u"consommations")
            #                 node_individu.appendChild(node_consommations)
            #
            #                 for dictConso in dictConsommations[IDfamille][IDindividu]:
            #                     node = doc.createElement(u"consommation")
            #                     node.setAttribute("date", utils_dates.ConvertDateToFR(dictConso["date"]))
            #                     node.setAttribute("activite", dictConso["nomActivite"])
            #                     node.setAttribute("etat", dictConso["etat"])
            #                     node.setAttribute("unite", dictConso["nomUnite"])
            #                     node_consommations.appendChild(node)

        # Renvoie le doc
        return doc

    def GetPrettyXML(self):
        """ Renvoie le pretty XML """
        doc = self.GetDoc()
        pretty_xml = doc.toprettyxml(indent="  ", encoding="utf-8")
        return pretty_xml

    def Enregistrer(self):
        """ Enregistre le fichier XML """
        # Créé le répertoire temp s'il n'existe pas
        rep_temp = utils_fichiers.GetTempRep()

        # Création du nom de fichier
        self.nom_fichier = "/temp/%s.xml" % uuid4()
        self.chemin_fichier = settings.MEDIA_ROOT + self.nom_fichier

        # Enregistrement du fichier
        f = open(self.chemin_fichier, "wb")
        try:
            f.write(self.GetPrettyXML())
        finally:
            f.close()
        return self.chemin_fichier
