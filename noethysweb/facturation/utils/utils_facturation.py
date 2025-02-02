# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from decimal import Decimal
from django.db.models import Q, Sum
from core.models import Prestation, Ventilation, Deduction, Consommation, Reglement, Agrement, Facture, Quotient, PesPiece, Prelevements, Note
from core.data import data_codes_etab
from core.utils import utils_preferences, utils_dates, utils_conversion, utils_impression, utils_infos_individus, utils_questionnaires, utils_texte
from facturation.utils import utils_impression_facture
from facturation.utils.utils_export_pes import Get_cle_modulo_23



class Facturation():
    def __init__(self):
        """ Récupération de toutes les données de base """

        # Recherche des numéros d'agréments
        logger.debug("Recherche tous les agréments...")
        self.listeAgrements = Agrement.objects.all()

        # Récupération des questionnaires
        logger.debug("Recherche tous les questionnaires...")
        self.questionnaires = utils_questionnaires.ChampsEtReponses(categorie="famille")

    def RechercheAgrement(self, IDactivite, date):
        for agrement in self.listeAgrements:
            if agrement.activite_id == IDactivite and date >= agrement.date_debut and date <= agrement.date_fin:
                return agrement
        return None

    def Supprime_accent(self, texte):
        liste = [ (u"é", u"e"), (u"è", u"e"), (u"ê", u"e"), (u"ë", u"e"), (u"ä", u"a"), (u"à", u"a"), (u"û", u"u"), (u"ô", u"o"), (u"ç", u"c"), (u"î", u"i"), (u"ï", u"i"), (u"/", u""), (u"\\", u""), ]
        for a, b in liste :
            texte = texte.replace(a, b)
            texte = texte.replace(a.upper(), b.upper())
        return texte

    def RemplaceMotsCles(self, texte="", dictValeurs={}):
        if texte == None :
            texte = ""
        for key, valeur, in dictValeurs.items():
            if key in texte and key.startswith("{"):
                texte = texte.replace(key, str(valeur))
        return texte

    def GetListeTriee(self, dict_factures={}):
        """ Renvoie une liste de factures triées par nom de titulaires """
        liste_keys = [(dict_facture["nomSansCivilite"], idfacture) for idfacture, dict_facture in dict_factures.items()]
        liste_keys.sort()
        liste_factures = [dict_factures[idfacture] for nom, idfacture in liste_keys]
        return liste_factures

    def GetDonnees(self, liste_factures=[], liste_activites=[], date_debut=None, date_fin=None, date_edition=None,
                   date_echeance=None, categories_prestations=["consommation", "cotisation", "location", "autre"],
                   type_label="0", date_anterieure=None, mode="facture", IDfamille=None, liste_IDindividus=[], filtre_prestations=None, exclusions_prestations=None,
                   impayes_factures=False, inclure_cotisations_si_conso=False, liste_conditions=None):
        """ Recherche des factures à créer """
        logger.debug("Recherche les données de facturation...")

        dictFactures = {}
        if liste_factures:
            for facture in Facture.objects.filter(idfacture__in=liste_factures):
                dictFactures[facture.pk] = facture

        # En cas d'intégration des prestations antérieures
        date_debut_temp = date_debut
        if date_anterieure:
            date_debut_temp = date_anterieure

        # Recherche des prestations de la période
        if liste_factures:
            conditions = Q(facture_id__in=liste_factures)
        else:
            conditions = (Q(activite__in=liste_activites) | Q(activite=None)) & Q(date__gte=date_debut_temp) & Q(date__lte=date_fin) & Q(categorie__in=categories_prestations)
            # Filtre facture
            if mode == "facture": conditions &= Q(facture_id=None)
            # Filtre famille
            if IDfamille: conditions &= Q(famille_id=IDfamille)
            # Filtre individus
            if liste_IDindividus:
                if 0 in liste_IDindividus:
                    conditions &= (Q(individu_id__in=liste_IDindividus) | Q(individu__isnull=True))
                else:
                    conditions &= Q(individu_id__in=liste_IDindividus)
            # Filtre noms de prestation
            if filtre_prestations:
                conditions_prestation = Q()
                for nom_prestation in filtre_prestations.split(";"):
                    conditions_prestation |= Q(label__icontains=nom_prestation.strip())
                conditions &= (conditions_prestation)
            # Exclusions noms de prestations
            if exclusions_prestations:
                for nom_prestation in exclusions_prestations.split(";"):
                    conditions &= ~Q(label__icontains=nom_prestation.strip())
            # Liste de conditions
            if liste_conditions:
                conditions &= liste_conditions

        logger.debug("Recherche des prestations des factures...")
        prestations = Prestation.objects.select_related('famille', 'activite', 'individu', 'tarif', 'categorie_tarif', "tarif__nom_tarif").filter(conditions).order_by("date")

        # Créé la liste des familles concernées
        liste_familles = []
        liste_familles_has_prestations_activite = []
        for prestation in prestations:
            if prestation.famille_id not in liste_familles:
                liste_familles.append(prestation.famille_id)
            if prestation.categorie == "consommation" and prestation.famille_id not in liste_familles_has_prestations_activite:
                liste_familles_has_prestations_activite.append(prestation.famille_id)

        # Importation des notes à afficher sur la facture
        dict_notes = {}
        for note in Note.objects.filter(afficher_facture=True, famille_id__in=liste_familles):
            dict_notes.setdefault(note.famille_id, [])
            dict_notes[note.famille_id].append(note)

        # Recherche de la ventilation des prestations
        if liste_factures:
            conditions = Q(prestation__facture__in=liste_factures)
        else:
            conditions = (Q(prestation__activite__in=liste_activites) | Q(prestation__activite=None)) & Q(prestation__date__gte=date_debut_temp) & Q(prestation__date__lte=date_fin)
            if mode == "facture":
                conditions &= Q(prestation__facture_id=None)
        logger.debug("Recherche des ventilations des factures...")
        ventilations = Ventilation.objects.select_related('prestation', 'reglement__payeur', 'reglement__mode', 'reglement__emetteur').filter(conditions)

        dictVentilationPrestations = {}
        dictReglements = {}
        for ventilation in ventilations:
            dictReglements.setdefault(ventilation.famille_id, {})
            if ventilation.reglement_id not in dictReglements[ventilation.famille_id]:
                dictReglements[ventilation.famille_id][ventilation.reglement_id] = {"date": ventilation.reglement.date, "montant": ventilation.reglement.montant, "mode": ventilation.reglement.mode,
                                                                                    "emetteur": ventilation.reglement.emetteur, "numero": ventilation.reglement.numero_piece, "payeur": ventilation.reglement.payeur,
                                                                                    "ventilation": Decimal(0)}
            dictReglements[ventilation.famille_id][ventilation.reglement_id]["ventilation"] += ventilation.montant

            dictVentilationPrestations.setdefault(ventilation.prestation_id, Decimal(0))
            dictVentilationPrestations[ventilation.prestation_id] += ventilation.montant

        # Recherche des QF aux dates concernées
        date_min, date_max = None, None
        if not liste_factures:
            date_min = date_debut
            date_max = date_fin
        else :
            liste_dates = []
            for prestation in prestations:
                liste_dates.append(prestation.date)
            if liste_dates:
                date_min = min(liste_dates)
                date_max = max(liste_dates)
        if date_min and date_max:
            listeQfdates = Quotient.objects.filter(Q(date_fin__gte=date_min) & Q(date_debut__lte=date_max))
        else:
            listeQfdates = []

        # Recherche des anciennes prestations impayées (=le report antérieur)
        logger.debug("Recherche des prestations reportées...")
        conditions = Q()
        if not liste_factures:
            conditions &= (Q(activite__in=liste_activites) | Q(activite=None)) & Q(date__lte=date_debut)
        if impayes_factures:
            conditions &= Q(facture__isnull=False)
        prestations_reports = Prestation.objects.filter(conditions, famille_id__in=liste_familles)

        # Recherche de la ventilation des reports
        if not liste_factures:
            conditions = (Q(prestation__activite__in=liste_activites) | Q(prestation__activite=None)) & Q(prestation__date__lte=date_debut)
        else:
            conditions = Q()
        logger.debug("Recherche de la ventilation des reports...")
        ventilations_reports = Ventilation.objects.values('prestation').filter(conditions, famille_id__in=liste_familles).annotate(total=Sum("montant"))

        dictVentilationReports = {}
        for ventilation in ventilations_reports:
            dictVentilationReports[ventilation["prestation"]] = ventilation["total"]
        
        # Recherche des déductions
        if liste_factures:
            conditions = Q(prestation__facture__in=liste_factures)
        else:
            conditions = Q()
        deductions = Deduction.objects.filter(conditions)

        dictDeductions = {}
        for deduction in deductions:
            dictDeductions.setdefault(deduction.prestation_id, [])
            dictDeductions[deduction.prestation_id].append({"IDdeduction": deduction.pk, "date": deduction.date, "montant": deduction.montant, "label": deduction.label, "IDaide": deduction.aide_id})

        # Recherche des consommations (sert pour les forfaits)
        if not liste_factures:
            conditions = Q(prestation__activite__in=liste_activites) & Q(date__gte=date_debut_temp) & Q(date__lte=date_fin)
        else:
            conditions = Q()
        logger.debug("Recherche des consommations...")
        consommations = Consommation.objects.filter(conditions, inscription__famille_id__in=liste_familles)

        dictConsommations = {}
        for consommation in consommations:
            dictConsommations.setdefault(consommation.prestation_id, [])
            dictConsommations[consommation.prestation_id].append({"date": consommation.date, "etat": consommation.etat})


        # Recherche du solde du compte
        logger.debug("Recherche du total des prestations pour chaque facture...")
        total_prestations = Prestation.objects.values('famille').filter(famille_id__in=liste_familles).annotate(total=Sum("montant"))

        dict_prestations = {}
        for dict_temp in total_prestations:
            dict_prestations[dict_temp["famille"]] = dict_temp["total"]
        logger.debug("Recherche du total des règlements pour chaque facture...")
        total_reglements = Reglement.objects.values('famille').filter(famille_id__in=liste_familles).annotate(total=Sum("montant"))

        dict_reglements = {}
        for dict_temp in total_reglements:
            dict_reglements[dict_temp["famille"]] = dict_temp["total"]

        dict_soldes_comptes = {}
        for IDfamille_temp in liste_familles:
            if IDfamille_temp in dict_prestations:
                total_prestations = Decimal(dict_prestations[IDfamille_temp])
            else:
                total_prestations = Decimal(0)
            if IDfamille_temp in dict_reglements:
                total_reglements = Decimal(dict_reglements[IDfamille_temp])
            else :
                total_reglements = Decimal(0)
            solde_compte = total_reglements - total_prestations

            if solde_compte > Decimal(0):
                solde_compte = "+%.2f %s" % (solde_compte, utils_preferences.Get_symbole_monnaie())
            else:
                solde_compte = "%.2f %s" % (solde_compte, utils_preferences.Get_symbole_monnaie())

            dict_soldes_comptes[IDfamille_temp] = solde_compte

        # Analyse et regroupement des données
        logger.debug("Analyse et groupement des données par facture...")
        num_facture = 0
        dictComptes = {}
        dictComptesPayeursFactures = {}
        for prestation in prestations:

            # On passe sur cette prestation si c'est une cotisation et que la famille n'a pas de consommation sur cette facture
            if inclure_cotisations_si_conso and prestation.categorie == "cotisation" and prestation.famille_id not in liste_familles_has_prestations_activite:
                continue

            dictComptesPayeursFactures.setdefault(prestation.famille_id, [])
            if prestation.facture_id not in dictComptesPayeursFactures[prestation.famille_id]:
                dictComptesPayeursFactures[prestation.famille_id].append(prestation.facture_id)

            if len(liste_factures) == 0:
                ID = prestation.famille_id
            else:
                ID = prestation.facture_id
                date_debut = dictFactures[prestation.facture_id].date_debut
                date_fin = dictFactures[prestation.facture_id].date_fin
                date_edition = dictFactures[prestation.facture_id].date_edition
                date_echeance = dictFactures[prestation.facture_id].date_echeance

            # Regroupement par compte payeur
            if ID not in dictComptes:
                
                # Recherche des titulaires
                nomsTitulairesAvecCivilite = prestation.famille.nom
                nomsTitulairesSansCivilite = prestation.famille.nom
                rue_resid = prestation.famille.rue_resid if prestation.famille.rue_resid else ""
                cp_resid = prestation.famille.cp_resid if prestation.famille.cp_resid else ""
                ville_resid = prestation.famille.ville_resid if prestation.famille.ville_resid else ""

                # Adresse de facturation
                destinataire_nom = prestation.famille.facturation_nom or nomsTitulairesAvecCivilite
                destinataire_rue = prestation.famille.facturation_rue_resid or rue_resid
                destinataire_cp = prestation.famille.facturation_cp_resid or cp_resid
                destinataire_ville = prestation.famille.facturation_ville_resid or ville_resid

                # Recherche des règlements
                if prestation.famille_id in dictReglements:
                    dictReglementsCompte = dictReglements[prestation.famille_id]
                else :
                    dictReglementsCompte = {}

                # Recherche du solde du compte
                if prestation.famille_id in dict_soldes_comptes:
                    solde_compte = dict_soldes_comptes[prestation.famille_id]
                else:
                    solde_compte = u"0.00 %s" % utils_preferences.Get_symbole_monnaie()

                # Mémorisation des infos
                dictComptes[ID] = {
                    "idfamille": ID,
                    "date_debut": date_debut,
                    "date_fin": date_fin,
                    "liste_activites": liste_activites,
                    "{FAMILLE_NOM}": destinataire_nom,
                    "nomSansCivilite": nomsTitulairesSansCivilite,
                    "IDfamille": prestation.famille_id,
                    "{IDFAMILLE}": str(prestation.famille_id),
                    "{FAMILLE_RUE}": destinataire_rue,
                    "{FAMILLE_CP}": destinataire_cp,
                    "{FAMILLE_VILLE}": destinataire_ville,
                    "{FAMILLE}": nomsTitulairesAvecCivilite,
                    "{DESTINATAIRE_NOM}": destinataire_nom,
                    "{DESTINATAIRE_RUE}": destinataire_rue,
                    "{DESTINATAIRE_CP}": destinataire_cp,
                    "{DESTINATAIRE_VILLE}": destinataire_ville,
                    "individus": {},
                    "listePrestations": [],
                    "listeIDprestations": [],
                    "listeDeductions": [],
                    "prestations_familiales": [],
                    "total": Decimal(0),
                    "total_tva": Decimal(0),
                    "ventilation": Decimal(0),
                    "solde": Decimal(0),
                    "qfdates": {},
                    "reports": {},
                    "total_reports": Decimal(0),
                    "{TOTAL_REPORTS}": u"0.00 %s" % utils_preferences.Get_symbole_monnaie(),
                    "solde_avec_reports": Decimal(0),
                    "{SOLDE_AVEC_REPORTS}": u"0.00 %s" % utils_preferences.Get_symbole_monnaie(),
                    "{SOLDE_COMPTE}": solde_compte,
                    "select": True,
                    "messages_familiaux": dict_notes.get(prestation.famille_id, []),
                    "{NOM_LOT}": "",
                    "reglements": dictReglementsCompte,
                    "texte_introduction": "",
                    "texte_conclusion": "",
                    "date_edition": date_edition,
                    "{DATE_EDITION_LONG}": utils_dates.DateComplete(date_edition),
                    "{DATE_EDITION_COURT}": utils_dates.ConvertDateToFR(date_edition),
                    "{DATE_DEBUT}": utils_dates.ConvertDateToFR(date_debut),
                    "{DATE_FIN}": utils_dates.ConvertDateToFR(date_fin),
                    "numero": "Facture n°%06d" % num_facture,
                    "num_facture": num_facture,
                    "{NUM_FACTURE}": "%06d" % num_facture,
                    "{CODEBARRES_NUM_FACTURE}": "F%06d" % num_facture,
                    "{INDIVIDUS_CONCERNES}": [],
                    "liste_idactivite": [],
                    }

                # Date échéance
                if date_echeance != None :
                    if date_echeance != None :
                        dictComptes[ID]["date_echeance"] = date_echeance
                        dictComptes[ID]["{DATE_ECHEANCE_LONG}"] = utils_dates.DateComplete(date_echeance)
                        dictComptes[ID]["{DATE_ECHEANCE_COURT}"] = utils_dates.ConvertDateToFR(date_echeance)
                        dictComptes[ID]["{TEXTE_ECHEANCE}"] = "Echéance du règlement : %s" % utils_dates.ConvertDateToFR(date_echeance)
                else:
                    dictComptes[ID]["date_echeance"] = None
                    dictComptes[ID]["{DATE_ECHEANCE_LONG}"] = ""
                    dictComptes[ID]["{DATE_ECHEANCE_COURT}"] = ""
                    dictComptes[ID]["{TEXTE_ECHEANCE}"] = ""

                # Ajoute les réponses des questionnaires
                for dictReponse in self.questionnaires.GetDonnees(IDfamille) :
                    dictComptes[ID][dictReponse["champ"]] = dictReponse["reponse"]
                    if dictReponse["controle"] == "codebarres":
                        dictComptes[ID]["{CODEBARRES_QUESTION_%d}" % dictReponse["IDquestion"]] = dictReponse["reponse"]

            # Insert les montants pour le compte payeur
            if prestation.pk in dictVentilationPrestations :
                montant_ventilation = Decimal(dictVentilationPrestations[prestation.pk])
            else :
                montant_ventilation = Decimal(0)

            dictComptes[ID]["total"] += prestation.montant
            dictComptes[ID]["ventilation"] += montant_ventilation
            dictComptes[ID]["solde"] = dictComptes[ID]["total"] - dictComptes[ID]["ventilation"]

            if prestation.tva:
                dictComptes[ID]["total_tva"] += Decimal(float(prestation.montant) - ((100.0 * float(prestation.montant)) / (100 + float(prestation.tva))))
            
            dictComptes[ID]["{TOTAL_PERIODE}"] = u"%.02f %s" % (dictComptes[ID]["total"], utils_preferences.Get_symbole_monnaie())
            dictComptes[ID]["{TOTAL_REGLE}"] = u"%.02f %s" % (dictComptes[ID]["ventilation"], utils_preferences.Get_symbole_monnaie())
            dictComptes[ID]["{SOLDE_DU}"] = u"%.02f %s" % (dictComptes[ID]["solde"], utils_preferences.Get_symbole_monnaie())

            # Ajout d'une prestation familiale
            IDindividu = prestation.individu_id
            if not prestation.individu_id:
                IDindividu = 0
            IDactivite = prestation.activite_id
            if not prestation.activite_id:
                IDactivite = 0
            
            # Ajout d'un individu
            if (IDindividu in dictComptes[ID]["individus"]) == False:
                if IDindividu:

                    # Si c'est bien un individu
                    texteDateNaiss = ""
                    if prestation.individu.date_naiss:
                        if prestation.individu.Get_sexe() == "M":
                            texteDateNaiss = ", né le %s" % utils_dates.ConvertDateToFR(prestation.individu.date_naiss)
                        else:
                            texteDateNaiss = ", née le %s" % utils_dates.ConvertDateToFR(prestation.individu.date_naiss)
                    texteIndividu = "<b>%s %s</b><font size=6>%s</font>" % (prestation.individu.nom, prestation.individu.prenom or "", texteDateNaiss)

                    nom = prestation.individu.Get_nom()

                    dictComptes[ID]["{INDIVIDUS_CONCERNES}"].append(nom)
                    
                else:
                    # Si c'est pour une prestation familiale on créé un individu ID 0 :
                    nom = "Prestations diverses"
                    texteIndividu = u"<b>%s</b>" % nom

                dictComptes[ID]["individus"][IDindividu] = {"texte": texteIndividu, "activites": {}, "total": Decimal(0), "ventilation": Decimal(0), "total_reports": Decimal(0), "nom": nom, "select": True}

            # Ajout de l'activité
            if IDactivite not in dictComptes[ID]["individus"][IDindividu]["activites"]:
                texteActivite = prestation.activite.nom if prestation.activite else None
                agrement = self.RechercheAgrement(IDactivite, prestation.date)
                if agrement:
                    texteActivite += " - n° agrément : %s" % agrement
                dictComptes[ID]["individus"][IDindividu]["activites"][IDactivite] = {"texte": texteActivite, "presences": {}}
            
            # Ajout de la présence
            if prestation.date not in dictComptes[ID]["individus"][IDindividu]["activites"][IDactivite]["presences"]:
                dictComptes[ID]["individus"][IDindividu]["activites"][IDactivite]["presences"][prestation.date] = {"texte": utils_dates.ConvertDateToFR(prestation.date), "unites": [], "total": Decimal(0)}

            # Recherche du nbre de dates pour cette prestation
            if prestation.pk in dictConsommations:
                listeDates = dictConsommations[prestation.pk]
            else:
                listeDates = []

            # Recherche des déductions
            if prestation.pk in dictDeductions:
                deductions = dictDeductions[prestation.pk]
            else :
                deductions = []

            # Mémorisation des déductions pour total
            for dictDeduction in deductions :
                dictComptes[ID]["listeDeductions"].append(dictDeduction)

            # Adaptation du label
            label = prestation.label
            if type_label == "2" and prestation.tarif:
                label = prestation.tarif.nom_tarif.nom
            if type_label == "3" and prestation.tarif:
                label = prestation.activite.nom
            if type_label == "1" and prestation.tarif:
                if prestation.pk in dictConsommations:
                    nbreAbsences = 0
                    for dictTemp in dictConsommations[prestation.pk]:
                        if dictTemp["etat"] == "absenti":
                            nbreAbsences += 1
                    # Si toutes les consommations attachées à la prestation sont sur l'état "Absence injustifiée" :
                    if nbreAbsences == len(dictConsommations[prestation.pk]):
                        label = prestation.label + " (Absence injustifiée)"

            # Mémorisation de la prestation
            dictPrestation = {
                "IDprestation": prestation.pk, "date": prestation.date, "categorie": prestation.categorie_tarif, "label": label,
                "montant_initial": prestation.montant_initial, "montant": prestation.montant, "tva": prestation.tva,
                "IDtarif": prestation.tarif_id, "nomTarif": prestation.tarif.nom_tarif.nom if prestation.tarif else None,
                "nomCategorieTarif": prestation.categorie_tarif.nom if prestation.categorie_tarif else None,
                "montant_ventilation": montant_ventilation, "listeDatesConso": listeDates, "quantite": prestation.quantite,
                "deductions": deductions,
                }

            dictComptes[ID]["individus"][IDindividu]["activites"][IDactivite]["presences"][prestation.date]["unites"].append(dictPrestation)
            
            # Ajout des totaux
            if prestation.montant:
                dictComptes[ID]["individus"][IDindividu]["total"] += prestation.montant
                dictComptes[ID]["individus"][IDindividu]["activites"][IDactivite]["presences"][prestation.date]["total"] += prestation.montant
            if montant_ventilation != None : 
                dictComptes[ID]["individus"][IDindividu]["ventilation"] += montant_ventilation
                        
            # Stockage des IDprestation pour saisir le IDfacture après création de la facture
            dictComptes[ID]["listePrestations"].append(prestation)
            dictComptes[ID]["listeIDprestations"].append(prestation.pk)

            # Mémorisation des IDactivite
            if IDactivite not in dictComptes[ID]["liste_idactivite"]:
                dictComptes[ID]["liste_idactivite"].append(IDactivite)

            # Intégration des qf aux dates concernées
            for quotient in listeQfdates:
                if quotient.famille_id == prestation.famille_id and quotient.date_debut <= date_fin and quotient.date_fin >= date_debut:
                    if quotient.date_debut < date_debut:
                        plage = "du %s " % utils_dates.ConvertDateToFR(date_debut)
                    else:
                        plage = "du %s " % utils_dates.ConvertDateToFR(quotient.date_debut)
                    if quotient.date_fin > date_fin :
                        plage = plage + "au %s" % utils_dates.ConvertDateToFR(date_fin)
                    else :
                        plage = plage + "au %s" % utils_dates.ConvertDateToFR(quotient.date_fin)
                    dictComptes[ID]["qfdates"][plage] = quotient.quotient
                
        
        # Intégration des total des déductions
        logger.debug("Intégration des total des déductions...")
        for ID, valeurs in dictComptes.items():
            totalDeductions = Decimal(0)
            for dictDeduction in dictComptes[ID]["listeDeductions"]:
                totalDeductions += dictDeduction["montant"]
            dictComptes[ID]["{TOTAL_DEDUCTIONS}"] = "%.02f %s" % (totalDeductions, utils_preferences.Get_symbole_monnaie())

        # Intégration du REPORT des anciennes prestations NON PAYEES
        logger.debug("Intégration du REPORT des anciennes prestations NON PAYEES...")
        for prestation in prestations_reports:
            montant_ventilation = Decimal(dictVentilationReports.get(prestation.pk, 0))
            montant_impaye = prestation.montant - montant_ventilation
            periode = (prestation.date.year, prestation.date.month)
            if montant_ventilation != prestation.montant:

                if len(liste_factures) == 0:

                    if prestation.famille_id in dictComptes and prestation.pk not in dictComptes[prestation.famille_id]["listeIDprestations"]:
                        if periode not in dictComptes[prestation.famille_id]["reports"]:
                            dictComptes[prestation.famille_id]["reports"][periode] = Decimal(0)
                        dictComptes[prestation.famille_id]["reports"][periode] += montant_impaye
                        dictComptes[prestation.famille_id]["total_reports"] += montant_impaye
                        dictComptes[prestation.famille_id]["{TOTAL_REPORTS}"] = "%.02f %s" % (dictComptes[prestation.famille_id]["total_reports"], utils_preferences.Get_symbole_monnaie())

                else:

                    if prestation.famille_id in dictComptesPayeursFactures:
                        for IDfacture in dictComptesPayeursFactures[prestation.famille_id]:
                            if prestation.date < dictComptes[IDfacture]["date_debut"] and prestation.pk not in dictComptes[IDfacture]["listeIDprestations"]:
                                if periode not in dictComptes[IDfacture]["reports"]:
                                    dictComptes[IDfacture]["reports"][periode] = Decimal(0)
                                dictComptes[IDfacture]["reports"][periode] += montant_impaye
                                dictComptes[IDfacture]["total_reports"] += montant_impaye
                                dictComptes[IDfacture]["{TOTAL_REPORTS}"] = "%.02f %s" % (dictComptes[IDfacture]["total_reports"], utils_preferences.Get_symbole_monnaie())

        # Ajout des impayés au solde
        for ID, dictValeurs in dictComptes.items():
            dictComptes[ID]["solde_avec_reports"] = dictComptes[ID]["solde"] + dictComptes[ID]["total_reports"]
            dictComptes[ID]["{SOLDE_AVEC_REPORTS}"] = "%.02f %s" % (dictComptes[ID]["solde_avec_reports"], utils_preferences.Get_symbole_monnaie())
            dictComptes[ID]["{INDIVIDUS_CONCERNES}"] = utils_texte.Convert_liste_to_texte_virgules(dictComptes[ID]["{INDIVIDUS_CONCERNES}"])
            dictComptes[ID]["{NOMS_INDIVIDUS}"] = dictComptes[ID]["{INDIVIDUS_CONCERNES}"]

        logger.debug("Fin de la récupération des données de facturation.")
        return dictComptes



    def GetDonneesImpression(self, liste_factures=[], dict_options=None):
        """ Impression des factures """
        logger.debug("Recherche toutes les factures...")
        factures = Facture.objects.select_related("lot").filter(idfacture__in=liste_factures)
        if not factures:
            return False

        # Prélèvements
        dict_prelevements = {prelevement.facture_id: prelevement for prelevement in Prelevements.objects.select_related("lot", "lot__modele__compte", "mandat").filter(facture_id__in=liste_factures)}

        # Infos PES ORMC
        dict_pes = {piece.facture_id: piece for piece in PesPiece.objects.select_related("lot", "lot__modele", "lot__modele__compte", "prelevement_mandat").filter(facture_id__in=liste_factures)}

        # Recherche la liste des familles concernées
        liste_idfamille = [facture.famille_id for facture in factures]

        # Récupération des infos de base familles
        logger.debug("Recherche toutes les infos utils_infos_individus...")
        infosIndividus = utils_infos_individus.Informations(liste_familles=liste_idfamille)

        # Récupération des mots-clés par défaut
        dict_motscles_defaut = utils_impression.Get_motscles_defaut()

        # Récupération des données de facturation
        dictComptes = self.GetDonnees(liste_factures=liste_factures, type_label=dict_options["intitules"], impayes_factures=dict_options.get("impayes_factures", False))

        dictFactures = {}
        dictChampsFusion = {}
        logger.debug("Analyse de chaque facture...")
        for facture in factures:
            if facture.pk in dictComptes:
                
                dictCompte = dictComptes[facture.pk]
                dictCompte["select"] = True
                
                # Affichage du solde initial
                if dict_options["affichage_solde"] == "1":
                    dictCompte["ventilation"] = facture.regle
                    dictCompte["solde"] = facture.solde
                
                # Attribue un numéro de facture
                if facture.prefixe:
                    numeroStr = "%s-%06d" % (facture.prefixe.prefixe, facture.numero)
                else:
                    numeroStr = "%06d" % facture.numero

                monnaie = utils_preferences.Get_monnaie()

                dictCompte["facture"] = facture
                dictCompte["{IDFACTURE}"] = str(facture.pk)
                dictCompte["num_facture"] = numeroStr
                dictCompte["num_codeBarre"] = numeroStr
                dictCompte["numero"] = "Facture n°%s" % numeroStr
                dictCompte["{NUM_FACTURE}"] = numeroStr
                dictCompte["{CODEBARRES_NUM_FACTURE}"] = "F%s" % numeroStr
                dictCompte["{NUMERO_FACTURE}"] = dictCompte["{NUM_FACTURE}"]
                dictCompte["{DATE_DEBUT}"] = utils_dates.ConvertDateToFR(facture.date_debut)
                dictCompte["{DATE_FIN}"] = utils_dates.ConvertDateToFR(facture.date_fin)
                dictCompte["{DATE_EDITION_FACTURE}"] = utils_dates.ConvertDateToFR(facture.date_edition)
                dictCompte["{DATE_ECHEANCE}"] = utils_dates.ConvertDateToFR(facture.date_echeance) if facture.date_echeance else ""
                dictCompte["{SOLDE}"] = u"%.2f %s" % (dictCompte["solde"], utils_preferences.Get_symbole_monnaie())
                dictCompte["{SOLDE_LETTRES}"] = utils_conversion.trad(facture.solde).strip().capitalize()
                dictCompte["{SOLDE_AVEC_REPORTS}"] = u"%.2f %s" % (dictCompte["solde_avec_reports"], utils_preferences.Get_symbole_monnaie())
                dictCompte["{SOLDE_AVEC_REPORTS_LETTRES}"] = utils_conversion.trad(facture.solde+dictCompte["total_reports"]).strip().capitalize()
                dictCompte["{NOM_LOT}"] = facture.lot.nom if facture.lot else ""
                dictCompte["{DATE_PRELEVEMENT}"] = ""
                dictCompte["prelevement"] = None

                # Ajoute les informations de base famille
                for key, valeur in infosIndividus.GetDictValeurs(mode="famille", ID=facture.famille_id, formatChamp=True).items():
                    if key not in ("{FAMILLE_NOM}", "{FAMILLE_RUE}", "{FAMILLE_CP}", "{FAMILLE_VILLE}"):
                        dictCompte[key] = valeur

                for IDindividu, dictIndividu in dictCompte["individus"].items():
                    dictIndividu["select"] = True

                # Recherche de prélèvements
                prelevement = dict_prelevements.get(facture.pk, None)
                if prelevement:
                    verbe = "a été" if prelevement.lot.date < facture.date_edition else "sera"
                    if prelevement.mandat.iban:
                        dictCompte["prelevement"] = "La somme de %.2f %s %s prélevée le %s sur le compte ***%s" % (prelevement.montant, utils_preferences.Get_symbole_monnaie(), verbe, utils_dates.ConvertDateToFR(prelevement.lot.date), prelevement.mandat.iban[-7:])
                    else :
                        dictCompte["prelevement"] = "La somme de %.2f %s %s prélevée le %s" % (prelevement.montant, utils_preferences.Get_symbole_monnaie(), verbe, utils_dates.ConvertDateToFR(prelevement.lot.date))
                    if prelevement.mandat.rum:
                        dictCompte["prelevement"] += "<br/>Réf. mandat unique : %s / Code ICS : %s" % (prelevement.mandat.rum, prelevement.lot.modele.compte.code_ics)
                    dictCompte["{DATE_PRELEVEMENT}"] = utils_dates.ConvertDateToFR(prelevement.lot.date)

                # Infos PES ORMC
                piece_pes = dict_pes.get(facture.pk, None)
                if piece_pes and piece_pes.prelevement:
                    verbe = "a été" if piece_pes.lot.date_prelevement < facture.date_edition else "sera"
                    if piece_pes.prelevement_mandat.iban:
                        dictCompte["prelevement"] = "La somme de %.2f %s %s prélevée le %s sur le compte ***%s" % (piece_pes.montant, utils_preferences.Get_symbole_monnaie(), verbe, utils_dates.ConvertDateToFR(piece_pes.lot.date_prelevement), piece_pes.prelevement_mandat.iban[-7:])
                    else :
                        dictCompte["prelevement"] = "La somme de %.2f %s %s prélevée le %s" % (piece_pes.montant, utils_preferences.Get_symbole_monnaie(), verbe, utils_dates.ConvertDateToFR(piece_pes.lot.date_prelevement))
                    if piece_pes.prelevement_mandat.rum:
                        dictCompte["prelevement"] += "<br/>Réf. mandat unique : %s / Code ICS : %s" % (piece_pes.prelevement_mandat.rum, piece_pes.lot.modele.compte.code_ics)
                    dictCompte["{DATE_PRELEVEMENT}"] = utils_dates.ConvertDateToFR(piece_pes.lot.date_prelevement)

                dictCompte["piece_pes"] = piece_pes
                dictCompte["{PES_IDPIECE}"] = str(facture.pk)
                dictCompte["{PES_IDLOT}"] = piece_pes.lot_id if piece_pes else ""
                dictCompte["{PES_NOM_LOT}"] = piece_pes.lot.nom if piece_pes else ""
                dictCompte["{PES_LOT_EXERCICE}"] = piece_pes.lot.exercice if piece_pes else ""
                dictCompte["{PES_LOT_MOIS}"] = piece_pes.lot.mois if piece_pes else ""
                # dictCompte["{PES_LOT_OBJET}"] = dictPes[IDfacture]["pes_lot_objet"]
                dictCompte["{PES_LOT_ID_BORDEREAU}"] = piece_pes.lot.id_bordereau if piece_pes else ""
                # dictCompte["{PES_LOT_CODE_PRODUIT}"] = dictPes[IDfacture]["pes_lot_code_produit"]

                # Datamatrix
                dictCompte["{PES_DATAMATRIX}"] = ""
                if piece_pes:
                    try:
                        dictCompte["{PES_DATAMATRIX}"] = Calculer_datamatrix(dictCompte)
                    except Exception as err:
                        pass
                        #logger.error("Erreur génération datamatrix : %s" % err)

                # Champs de fusion pour Email
                dictChampsFusion[facture.pk] = {}
                dictChampsFusion[facture.pk]["{NUMERO_FACTURE}"] = dictCompte["{NUM_FACTURE}"]
                dictChampsFusion[facture.pk]["{DATE_DEBUT}"] = utils_dates.ConvertDateToFR(facture.date_debut)
                dictChampsFusion[facture.pk]["{DATE_FIN}"] = utils_dates.ConvertDateToFR(facture.date_fin)
                dictChampsFusion[facture.pk]["{DATE_EDITION_FACTURE}"] = utils_dates.ConvertDateToFR(facture.date_edition)
                dictChampsFusion[facture.pk]["{DATE_ECHEANCE}"] = utils_dates.ConvertDateToFR(facture.date_echeance)  if facture.date_echeance else ""
                dictChampsFusion[facture.pk]["{SOLDE}"] = u"%.2f %s" % (dictCompte["solde"], utils_preferences.Get_symbole_monnaie())
                dictChampsFusion[facture.pk]["{SOLDE_AVEC_REPORTS}"] = dictCompte["{SOLDE_AVEC_REPORTS}"]
                dictChampsFusion[facture.pk]["{SOLDE_COMPTE}"] = dictCompte["{SOLDE_COMPTE}"]
                dictChampsFusion[facture.pk]["{DATE_PRELEVEMENT}"] = dictCompte["{DATE_PRELEVEMENT}"]

                # Fusion pour textes personnalisés
                dictCompte["texte_titre"] = self.RemplaceMotsCles(dict_options["texte_titre"], dictCompte)
                dictCompte["texte_introduction"] = self.RemplaceMotsCles(dict_options["texte_introduction"], dictCompte)
                dictCompte["texte_conclusion"] = self.RemplaceMotsCles(dict_options["texte_conclusion"], dictCompte)

                # Ajout les mots-clés par défaut
                dictCompte.update(dict_motscles_defaut)

                # Mémorisation de la facture
                dictFactures[facture.pk] = dictCompte
            

        if not dictFactures:
            return False
           
        return dictFactures, dictChampsFusion




    def Impression(self, liste_factures=[], dict_options=None, mode_email=False):
        """ Impression des factures """
        # Récupération des données à partir des IDfacture
        logger.debug("Recherche des données d'impression...")
        resultat = self.GetDonneesImpression(liste_factures, dict_options)
        if resultat == False :
            return False
        dictFactures, dictChampsFusion = resultat

        # Envoi par email
        noms_fichiers = {}
        if mode_email:
            logger.debug("Création des PDF des factures à l'unité...")
            impression = utils_impression_facture.Impression(dict_options=dict_options, IDmodele=dict_options["modele"].pk, generation_auto=False)
            for IDfacture, dictFacture in dictFactures.items():
                logger.debug("Création du PDF de la facture ID%d..." % IDfacture)
                impression.Generation_document(dict_donnees={IDfacture: dictFacture})
                noms_fichiers[IDfacture] = {"nom_fichier": impression.Get_nom_fichier(), "valeurs": impression.Get_champs_fusion_pour_email("facture", IDfacture)}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_facture.Impression(dict_donnees=dictFactures, dict_options=dict_options, IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()

        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}



def Calculer_datamatrix(dictCompte):
    piece_pes = dictCompte["piece_pes"]
    elements = []

    # 1-40 : Données métiers (40 caractères)
    elements.append(" " * 40)

    # 41-64 : Zone d'espaces (24 caractères)
    elements.append(" " * 24)

    # 65-67 : Code établissement (3 caractères)
    code_etab = data_codes_etab.Rechercher(str(piece_pes.lot.modele.code_etab))
    elements.append("%03d" % int(code_etab))

    # 68 : Code période (1 caractère)
    elements.append(str(piece_pes.lot.mois)[:1])

    # 69-71 : Deux premiers chiffres du CodProdLoc (3 caractères)
    elements.append("%03d" % int(data_codes_etab.Rechercher(str(piece_pes.lot.modele.code_prodloc[:2]))))

    # 72-73 : deux zéros
    elements.append("00")

    # 74-75 : Deux derniers chiffres de la balise Exerc (2 caractères)
    elements.append(str(piece_pes.lot.exercice)[-2:])

    # 76 : Clé 5 (modulo 11)
    base = int("".join(elements[-5:]))
    cle = str(11 - (base % 11))[-1:]
    elements.append(cle)

    # 77-82 : Code émetteur (6 caractères)
    elements.append("940033")

    # 83-86 : Code établissement (=0001)
    elements.append("0001")

    # 87-88 : Clé 3 (Modulo 100)
    base = "".join(elements[-2:])
    cle = sum([rang * int(valeur) for rang, valeur in enumerate(base[::-1], 1)]) % 100
    elements.append("%02d" % cle)

    # 89 : Espace
    elements.append(" ")

    # 92-115 : Référence de l'opération (24 caractères)
    id_poste = "%06d" % int(piece_pes.lot.modele.id_poste)

    num_dette = str(dictCompte["facture"].numero).zfill(15)

    cle2 = Get_cle_modulo_23((str(piece_pes.lot.exercice)[-2:], str(piece_pes.lot.mois), "00", str(dictCompte["facture"].numero).zfill(13)))
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXY"
    cle2 = "%02d" % (alphabet.index(cle2) + 1)

    elements.append("".join([cle2, num_dette, id_poste, "4"]))

    # 116 : Code document (=9)
    elements.append("9")

    # 90-91 : Clé 2 (Modulo 100)
    base = "".join(elements[-2:])
    cle = sum([rang * int(valeur) for rang, valeur in enumerate(base[::-1], 1)]) % 100
    elements.insert(len(elements)-2, "%02d" % cle)

    # 119 : Code nature (=8)
    elements.append("8")

    # 120-121 : Code de traitement BDF (=06)
    elements.append("06")

    # 122 : Espace
    elements.append(" ")

    # 123-130 : Montant (8 caractères)
    montant = "{: >8}".format(("%.2f" % dictCompte["solde"]).replace(".", ""))
    elements.append(montant)

    # 117-118 : Clé 1 (Modulo 100)
    base1 = "".join(elements[-4:-2]).replace(" ", "0")
    somme1 = sum([rang * int(valeur) for rang, valeur in enumerate(base1[::-1], 9)])

    base2 = "".join(elements[-1]).replace(" ", "0")
    somme2 = sum([rang * int(valeur) for rang, valeur in enumerate(base2[::-1], 1)])

    cle = (somme1 + somme2) % 100
    elements.insert(len(elements)-4, "%02d" % cle)

    # Finalisation du datamatrix
    datamatrix = "".join(elements)
    return datamatrix
