# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from core.utils import utils_dates, utils_questionnaires
from core.data import data_civilites
from core.models import Individu, Famille, Rattachement, Quotient, Inscription, Note, Information, Scolarite, Cotisation, Lien, CHOIX_AUTORISATIONS
from individus.utils import utils_pieces_manquantes
from core.data.data_liens import DICT_TYPES_LIENS
from django.db.models import Q


# import GestionDB
# import sqlite3
# import datetime
# import base64
# from six.moves import cPickle
# import six
# from Utils import UTILS_Dates
# from Utils import UTILS_Cotisations_manquantes
# from Utils import UTILS_Pieces_manquantes
# from Utils import UTILS_Questionnaires
# from Utils import UTILS_Fichiers
#
# from Data.DATA_Liens import DICT_TYPES_LIENS, DICT_AUTORISATIONS
# from Data import DATA_Civilites as Civilites
#
# DICT_CIVILITES = Civilites.GetDictCivilites()


def GetTypeChamp(codeChamp=""):
    """ Renvoie le type de donnée d'un champ """
    codeChamp = codeChamp.replace("{", "").replace("}", "")
    dictTypes = {"INDIVIDU_AGE_INT": "entier", }
    if codeChamp in dictTypes:
        return dictTypes[codeChamp]
    else:
        return "texte"


def GetNomsChampsPossibles(mode="individu+famille"):
    listeChamps = []

    # Individu
    listeChampsIndividu = [
        ("ID de l'individu", u"253", "{IDINDIVIDU}"),
        ("Civilité courte de l'individu", "M.", "{INDIVIDU_CIVILITE_COURT}"),
        ("Civilité longue de l'individu", "Monsieur", "{INDIVIDU_CIVILITE_LONG}"),
        ("Sexe de l'individu", u"H", "{INDIVIDU_SEXE}"),
        ("Nom complet de l'individu", "DUPOND Philippe", "{INDIVIDU_NOM_COMPLET}"),
        ("Nom de famille de l'individu", "DUPOND", "{INDIVIDU_NOM}"),
        ("Prénom de l'individu", "Philippe", "{INDIVIDU_PRENOM}"),
        ("Numéro de sécu de l'individu", u"2 39 336...", "{INDIVIDU_NUM_SECU}"),
        ("Date de naissance de l'individu", u"23/01/2010", "{INDIVIDU_DATE_NAISS}"),
        ("Age de l'individu", "9 ans", "{INDIVIDU_AGE}"),
        ("Code postal de la ville de naissance de l'individu", u"29200", "{INDIVIDU_CP_NAISS}"),
        ("Ville de naissance de l'individu", "BREST", "{INDIVIDU_VILLE_NAISS}"),
        ("Année de décès de l'individu", u"2012", "{INDIVIDU_ANNEE_DECES}"),
        ("Rue de l'adresse de l'individu", "10 rue des oiseaux", "{INDIVIDU_RUE}"),
        ("Code postal de l'adresse de l'individu", u"29870", "{INDIVIDU_CP}"),
        ("Ville de l'adresse de l'individu", "LANNILIS", "{INDIVIDU_VILLE}"),
        ("Secteur de l'adresse de l'individu", "Quartier sud", "{INDIVIDU_SECTEUR}"),
        ("Catégorie socio-professionnelle de l'individu", "Ouvrier", "{INDIVIDU_CATEGORIE_TRAVAIL}"),
        ("Profession de l'individu", "Peintre", "{INDIVIDU_PROFESSION}"),
        ("Employeur de l'individu", "Pinceaux et Cie", "{INDIVIDU_EMPLOYEUR}"),
        ("Numéro de téléphone pro de l'individu", u"01.02.03.04.05", "{INDIVIDU_TEL_PRO}"),
        ("Numéro de fax pro de l'individu", u"01.02.03.04.05", "{INDIVIDU_FAX_PRO}"),
        ("Mail pro de l'individu", u"monadresse@pro.fr", "{INDIVIDU_MAIL_PRO}"),
        ("Numéro de téléphone domicile de l'individu", u"01.02.03.04.05", "{INDIVIDU_TEL_DOMICILE}"),
        ("Numéro de téléphone portable de l'individu", u"06.02.03.04.05", "{INDIVIDU_TEL_MOBILE}"),
        ("Numéro de fax domicile de l'individu", u"01.02.03.04.05", "{INDIVIDU_FAX}"),
        ("Adresse Email de l'individu", u"monadresse@perso.fr", "{INDIVIDU_MAIL}"),
        ("Nom de famille du médecin traitant", "BERGOT", "{MEDECIN_NOM}"),
        ("Prénom du médecin traitant", "Albert", "{MEDECIN_PRENOM}"),
        ("Rue de l'adresse du médecin", "3 rue des allergies", "{MEDECIN_RUE}"),
        ("Code postal de l'adresse du médecin traitant", u"29870", "{MEDECIN_CP}"),
        ("Ville de l'adresse du médecin traitant", "LANNILIS", "{MEDECIN_VILLE}"),
        ("Numéro de téléphone du cabinet du médecin", u"01.02.03.04.05", "{MEDECIN_TEL_CABINET}"),
        ("Numéro de portable du médecin", u"06.02.03.04.05", "{MEDECIN_TEL_MOBILE}"),
        ("Mémo de l'individu", "informations diverses...", "{INDIVIDU_MEMO}"),
        ("Date de création de la fiche individuelle", u"15/07/2014", "{INDIVIDU_DATE_CREATION}"), ]

    if "individu" in mode:
        listeChamps.extend(listeChampsIndividu)

    # Inscriptions
    listeChampsInscription = [
        ("Activité de l'inscription n°x", "Accueil de Loisirs", "{INSCRIPTION_x_ACTIVITE}"),
        ("Groupe de l'inscription n°x", "3-6 ans", "{INSCRIPTION_x_GROUPE}"),
        ("Catégorie de tarif de l'inscription n°x", "Hors commune", "{INSCRIPTION_x_CATEGORIE_TARIF}"),
        ("Famille rattachée à l'inscription n°x", "DUPOND Philippe et Marie", "{INSCRIPTION_x_NOM_TITULAIRES}"),
        ("Parti de l'inscription n°x", "Oui", "{INSCRIPTION_x_PARTI}"),
        ("Date de l'inscription n°x", u"15/07/2014", "{INSCRIPTION_x_DATE_INSCRIPTION}"),
         ]

    if "individu" in mode:
        listeChamps.extend(listeChampsInscription)

    # Infos médicales
    listeChampsInfosMedicales = [
        ("Intitulé de l'information médicale n°x", "Allergie aux acariens", "{MEDICAL_x_INTITULE}"),
        ("Description de l'information médicale n°x", "Fait des boutons", "{MEDICAL_x_DESCRIPTION}"),
        ("Traitement médical de l'information médicale n°x", "Amoxicilline", "{MEDICAL_x_TRAITEMENT_MEDICAL}"),
        ("Description du traitement de l'information médicale n°x", "Prendre tous les midis","{MEDICAL_x_DESCRIPTION_TRAITEMENT}"),
        ("Date de début de traitement de l'information médicale n°x", u"01/07/2014", "{MEDICAL_x_DATE_DEBUT_TRAITEMENT}"),
        ("Date de fin de traitement de l'information médicale n°x", u"31/07/2014","{MEDICAL_x_DATE_FIN_TRAITEMENT}"),
    ]

    if "individu" in mode:
        listeChamps.extend(listeChampsInfosMedicales)

    # Infos scolarité
    listeChampsScolarite = [
        ("Date de début de l'étape de scolarité", u"01/09/2014", "{SCOLARITE_DATE_DEBUT}"),
        ("Date de fin de l'étape de scolarité", u"30/06/2015", "{SCOLARITE_DATE_FIN}"),
        ("Nom de l'école", "Ecole Jules Ferry", "{SCOLARITE_NOM_ECOLE}"),
        ("Nom de la classe", "CP/CE1 de Mme Machin", "{SCOLARITE_NOM_CLASSE}"),
        ("Nom du niveau scolaire", "Cours élémentaire 1", "{SCOLARITE_NOM_NIVEAU}"),
        ("Nom abrégé du niveau scolaire", "CE1", "{SCOLARITE_ABREGE_NIVEAU}"),
    ]

    if "individu" in mode:
        listeChamps.extend(listeChampsScolarite)

    # Infos cotisations
    listeChampsCotisations = [
        ("Date de début de l'adhésion actuelle", u"01/09/2018", "{COTISATION_DATE_DEBUT}"),
        ("Date de fin de l'adhésion actuelle", u"30/06/2019", "{COTISATION_DATE_FIN}"),
        ("Nom du type de l'adhésion actuelle", "Adhésion annuelle", "{COTISATION_TYPE}"),
        ("Nom de l'unité de l'adhésion actuelle", "2018-19", "{COTISATION_UNITE}"),
        ("Numéro de l'adhésion actuelle", "12345678", "{COTISATION_NUMERO}"),
    ]

    if "individu" in mode:
        listeChamps.extend(listeChampsCotisations)

    # Famille
    listeChampsFamille = [
        ("Noms des titulaires de la famille", "DUPOND Philippe et Marie", "{FAMILLE_NOM}"),
        ("Rue de l'adresse de la famille", "10 rue des oiseaux", "{FAMILLE_RUE}"),
        ("Code postal de l'adresse de la famille", u"29870", "{FAMILLE_CP}"),
        ("Ville de l'adresse de la famille", "LANNILIS", "{FAMILLE_VILLE}"),
        ("Secteur de l'adresse de la famille", "Quartier sud", "{FAMILLE_SECTEUR}"),
        ("Nom de la caisse d'allocations", "CAF", "{FAMILLE_NOM_CAISSE}"),
        ("Nom du régime social", "Régime général", "{FAMILLE_NOM_REGIME}"),
        ("Numéro allocataire", "1234567X", "{FAMILLE_NUM_ALLOCATAIRE}"),
        ("Nom de l'allocataire titulaire", "DUPOND Philippe", "{FAMILLE_NOM_ALLOCATAIRE}"),
        ("Mémo de la famille", "Informations diverses...", "{FAMILLE_MEMO}"),
        ("Date de création de la fiche familiale", u"15/07/2014", "{FAMILLE_DATE_CREATION}"),
        ("Quotient familial actuel de la famille", u"340", "{FAMILLE_QF_ACTUEL}"),
        ("Liste des adhésions manquantes", "Adhésion familiale", "{COTISATIONS_MANQUANTES}"),
        ("Liste des pièces manquantes", "Certificat médical", "{PIECES_MANQUANTES}"),
    ]

    if "famille" in mode:
        listeChamps.extend(listeChampsFamille)

    # Messages
    listeChampsMessages = [
        ("Date de saisie du message n°x", u"18/07/2014", "{MESSAGE_x_DATE_SAISIE}"),
        ("Date de parution du message n°x", u"18/07/2014", "{MESSAGE_x_DATE_PARUTION}"),
        ("Texte du message n°x", "Envoyer une facture à la famille", "{MESSAGE_x_TEXTE}"),
        ("Nom de l'individu ou de la famille rattachée au message n°x", "DUPOND Philippe et Marie", "{MESSAGE_x_NOM}"),
        ("Catégorie du message n°x", "Courrier", "{MESSAGE_x_CATEGORIE}"),
    ]

    if "individu" in mode or "famille" in mode:
        listeChamps.extend(listeChampsMessages)

    # Rattachements
    listeRattachements = [
        ("REPRESENTANT_RATTACHE_x","le représentant rattaché n°x"),
        ("ENFANT_RATTACHE_x","l'enfant rattaché n°x"),
        ("CONTACT_RATTACHE_x","le contact rattaché n°x"),
    ]
    listeChampsRattachements = [
        ("Nombre de représentants rattachés à la famille", "2", "{NBRE_REPRESENTANTS_RATTACHES}"),
        ("Nombre d'enfants rattachés à la famille", "1", "{NBRE_ENFANTS_RATTACHES}"),
        ("Nombre de contacts rattachés à la famille", "3", "{NBRE_CONTACTS_RATTACHES}"),
    ]
    for champRattachement, labelRattachement in listeRattachements:
        for label, exemple, champ in listeChampsIndividu:
            if champ.startswith("{INDIVIDU"):
                label = label.replace("l'individu", labelRattachement)
                champ = champ.replace("INDIVIDU", champRattachement)
                listeChampsRattachements.append((label, exemple, champ))
        listeChampsRattachements.append(("Liens pour %s" % labelRattachement, "Philippe est concubin de Marie...", "{%s_LIEN}" % champRattachement))
        listeChampsRattachements.append(("%s est titulaire ?" % labelRattachement, "Oui", "{%s_TITULAIRE}" % champRattachement))

    if "famille" in mode:
        listeChamps.extend(listeChampsRattachements)

    # Liens
    listeLiensPossibles = [
        ("PERE", "le père"),
        ("MERE", "la mère"),
        ("CONJOINT", "le ou la conjointe"),
        ("ENFANT", "l'enfant n°x"),
        ("AUTRE_LIEN", "l'autre lien n°x"),
    ]
    listeLiens = [
        ("Nombre d'enfants de l'individu", "2", "{NBRE_ENFANTS}"),
        ("Nombre d'autres liens de l'individu", "4", "{NBRE_AUTRES_LIENS}"),
    ]
    for champLien, labelLien in listeLiensPossibles:
        for label, exemple, champ in listeChampsIndividu:
            if champ.startswith("{INDIVIDU"):
                label = label.replace("l'individu", labelLien)
                champ = champ.replace("INDIVIDU", champLien)
                listeLiens.append((label, exemple, champ))
        listeLiens.append(("Autorisation pour %s" % labelLien, "Responsable légal", "{%s_AUTORISATION}" % champLien))
        listeLiens.append(("Nom du lien pour %s" % labelLien, "Enfant", "{%s_NOM_LIEN}" % champLien))

    if "individu" in mode:
        listeChamps.extend(listeLiens)

    # Questionnaires
    # DB = GestionDB.DB()
    # req = """SELECT IDquestion, questionnaire_questions.label, type, controle, defaut
    # FROM questionnaire_questions
    # LEFT JOIN questionnaire_categories ON questionnaire_categories.IDcategorie = questionnaire_questions.IDcategorie
    # WHERE questionnaire_categories.type IN ('famille', 'individu')
    # ORDER BY questionnaire_questions.ordre
    # ;"""
    # DB.ExecuterReq(req)
    # listeQuestions = DB.ResultatReq()
    # DB.Close()
    # for IDquestion, label, public, controle, defaut in listeQuestions:
    #     if public in mode:
    #         code = "{QUESTION_%d}" % IDquestion
    #         listeChamps.append((label, u"", code))

    return listeChamps


class Informations():
    def __init__(self, date_reference=datetime.date.today(), qf=True, inscriptions=True, messages=True,
                 infosMedicales=True, cotisationsManquantes=True, piecesManquantes=True, questionnaires=True,
                 scolarite=True, cotisations=True, liste_familles=[]):
        self.date_reference = date_reference
        self.qf = qf
        self.inscriptions = inscriptions
        self.messages = messages
        self.infosMedicales = infosMedicales
        self.cotisationsManquantes = cotisationsManquantes
        self.piecesManquantes = piecesManquantes
        self.questionnaires = questionnaires
        self.scolarite = scolarite
        self.cotisations = cotisations
        self.liste_familles = liste_familles

        # Condition familles
        if len(self.liste_familles) > 999:
            self.liste_familles = []
        if self.liste_familles:
            self.condition_familles = Q(famille__in=self.liste_familles)
        else:
            self.condition_familles = Q()

        # Lancement du calcul
        self.Run()

    def Run(self):
        """ Procédure de recherche et de calcul des résultats """
        # Lecture des données de base
        self.dictIndividus = self.GetDictIndividus()
        self.dictFamilles = self.GetDictFamilles()
        self.dictLiens = self.GetLiens()
        self.dictRattachements = self.GetRattachements()

        # # Lecture des autres types de données
        if self.qf: self.RechercheQF()
        if self.inscriptions: self.RechercheInscriptions()
        if self.messages: self.RechercheMessages()
        if self.infosMedicales: self.RechercheInfosMedicales()
        # # if self.cotisationsManquantes: self.RechercheCotisationsManquantes()
        if self.piecesManquantes: self.RecherchePiecesManquantes()
        if self.questionnaires: self.RechercheQuestionnaires()
        if self.scolarite: self.RechercheScolarite()
        if self.cotisations: self.RechercheCotisations()

        return self.dictIndividus

    def GetNomsChampsReq(self, listeChamps={}):
        listeNomsCodes = []
        listeNomsChamps = []
        for code, champ in listeChamps:
            listeNomsCodes.append(code)
            listeNomsChamps.append(champ)
        return listeNomsCodes, listeNomsChamps

    def GetListeChampsIndividus(self):
        return [
            ("IDINDIVIDU", "IDindividu"), ("individu_IDcivilite", "IDcivilite"), ("INDIVIDU_NOM", "individus.nom"),
            ("INDIVIDU_PRENOM", "individus.prenom"), ("INDIVIDU_NUM_SECU", "num_secu"),
            ("INDIVIDU_DATE_NAISS", "date_naiss"), ("INDIVIDU_CP_NAISS", "cp_naiss"),
            ("INDIVIDU_VILLE_NAISS", "ville_naiss"), ("INDIVIDU_ANNEE_DECES", "annee_deces"),
            ("individu_adresse_auto", "adresse_auto"), ("INDIVIDU_RUE", "individus.rue_resid"),
            ("INDIVIDU_CP", "individus.cp_resid"), ("INDIVIDU_VILLE", "individus.ville_resid"),
            ("INDIVIDU_SECTEUR", "secteurs.nom"), ("INDIVIDU_CATEGORIE_TRAVAIL", "categories_travail.nom"),
            ("INDIVIDU_PROFESSION", "profession"), ("INDIVIDU_EMPLOYEUR", "employeur"),
            ("INDIVIDU_TEL_PRO", "travail_tel"), ("INDIVIDU_FAX_PRO", "travail_fax"),
            ("INDIVIDU_MAIL_PRO", "travail_mail"), ("INDIVIDU_TEL_DOMICILE", "tel_domicile"),
            ("INDIVIDU_TEL_MOBILE", "individus.tel_mobile"), ("INDIVIDU_TEL_PORTABLE", "individus.tel_mobile"),
            ("INDIVIDU_FAX", "tel_fax"), ("INDIVIDU_MAIL", "mail"), ("MEDECIN_NOM", "medecins.nom"),
            ("MEDECIN_PRENOM", "medecins.prenom"), ("MEDECIN_RUE", "medecins.rue_resid"),
            ("MEDECIN_CP", "medecins.cp_resid"), ("MEDECIN_VILLE", "medecins.ville_resid"),
            ("MEDECIN_TEL_CABINET", "medecins.tel_cabinet"), ("MEDECIN_TEL_MOBILE", "medecins.tel_mobile"),
            ("INDIVIDU_MEMO", "individus.memo"), ("INDIVIDU_DATE_CREATION", "individus.date_creation"),
        ]

    def GetDictIndividus(self):
        """ Récupère toutes les infos de base sur les individus """
        dictTemp = {}

        dict_civilites = data_civilites.GetDictCivilites()

        individus = Individu.objects.select_related('secteur', 'medecin', 'categorie_travail').all()
        for individu in individus:
            age = individu.Get_age()
            dictTemp[individu.pk] = {
                "IDINDIVIDU": individu.pk,
                "individu_IDcivilite": individu.civilite,
                "INDIVIDU_NOM": individu.nom,
                "INDIVIDU_NOM_COMPLET": individu.Get_nom(),
                "CODEBARRES_ID_INDIVIDU": "I%06d" % individu.pk,
                "INDIVIDU_PRENOM": individu.prenom,
                "INDIVIDU_DATE_NAISS": utils_dates.ConvertDateToFR(individu.date_naiss),
                "INDIVIDU_CP_NAISS": individu.cp_naiss,
                "INDIVIDU_VILLE_NAISS": individu.ville_naiss,
                "INDIVIDU_ANNEE_DECES": individu.annee_deces,
                "individu_adresse_auto": individu.adresse_auto,
                "INDIVIDU_RUE": individu.rue_resid,
                "INDIVIDU_CP": individu.cp_resid,
                "INDIVIDU_VILLE": individu.ville_resid,
                "INDIVIDU_SECTEUR": individu.secteur.nom if individu.secteur else "",
                "INDIVIDU_SECTEUR_COLORE": ("<font color='%s'>%s</font>" % (individu.secteur.couleur or "#000000", individu.secteur)) if individu.secteur else "",
                "INDIVIDU_CATEGORIE_TRAVAIL": individu.categorie_travail,
                "INDIVIDU_PROFESSION": individu.profession,
                "INDIVIDU_EMPLOYEUR": individu.employeur,
                "INDIVIDU_TEL_PRO": individu.travail_tel,
                "INDIVIDU_FAX_PRO": individu.travail_fax,
                "INDIVIDU_MAIL_PRO": individu.travail_mail,
                "INDIVIDU_TEL_DOMICILE": individu.tel_domicile,
                "INDIVIDU_TEL_MOBILE": individu.tel_mobile,
                "INDIVIDU_TEL_PORTABLE": individu.tel_mobile,
                "INDIVIDU_FAX": individu.tel_fax,
                "INDIVIDU_MAIL": individu.mail,
                "INDIVIDU_PHOTO": individu.Get_photo(forTemplate=False),
                "MEDECIN_NOM": individu.medecin.nom if individu.medecin else "",
                "MEDECIN_PRENOM": individu.medecin.prenom if individu.medecin else "",
                "MEDECIN_RUE": individu.medecin.rue_resid if individu.medecin else "",
                "MEDECIN_CP": individu.medecin.cp_resid if individu.medecin else "",
                "MEDECIN_VILLE": individu.medecin.ville_resid if individu.medecin else "",
                "MEDECIN_TEL_CABINET": individu.medecin.tel_cabinet if individu.medecin else "",
                "MEDECIN_TEL_MOBILE": individu.medecin.tel_mobile if individu.medecin else "",
                "INDIVIDU_MEMO": individu.memo,
                "INDIVIDU_DATE_CREATION": utils_dates.ConvertDateToFR(individu.date_creation),
                "INDIVIDU_AGE": "%d ans" % age if age else "",
                "INDIVIDU_AGE_INT": individu.Get_age(),
                "INDIVIDU_CIVILITE_COURT": dict_civilites[individu.civilite]["abrege"],
                "INDIVIDU_CIVILITE_LONG": dict_civilites[individu.civilite]["label"],
                "INDIVIDU_SEXE": dict_civilites[individu.civilite]["sexe"],
                "NBRE_ENFANTS": 0,
                "NBRE_AUTRES_LIENS": 0,
                "liens": [],
                "SCOLARITE_DATE_DEBUT": "",
                "SCOLARITE_DATE_FIN": "",
                "SCOLARITE_NOM_ECOLE": "",
                "SCOLARITE_NOM_CLASSE": "",
                "SCOLARITE_NOM_NIVEAU": "",
                "SCOLARITE_ABREGE_NIVEAU": "",
            }

        # Recherche les adresses de chaque individu
        dictIndividus = {}
        for IDindividu, dictIndividu in dictTemp.items():
            adresse_auto = dictIndividu["individu_adresse_auto"]
            if adresse_auto and adresse_auto in dictTemp:
                dictIndividu["INDIVIDU_RUE"] = dictTemp[adresse_auto]["INDIVIDU_RUE"]
                dictIndividu["INDIVIDU_CP"] = dictTemp[adresse_auto]["INDIVIDU_CP"]
                dictIndividu["INDIVIDU_VILLE"] = dictTemp[adresse_auto]["INDIVIDU_VILLE"]
                dictIndividu["INDIVIDU_SECTEUR"] = dictTemp[adresse_auto]["INDIVIDU_SECTEUR"]

            # Mémorisation
            dictIndividus[IDindividu] = dictIndividu

        return dictIndividus

    def GetRattachements(self):
        """ Récupération des rattachements """
        rattachements = Rattachement.objects.filter(self.condition_familles)

        dictRattachementsFamilles = {}
        dictRattachementsIndividus = {}
        for rattachement in rattachements:
            valeurs = {
                "IDrattachement": rattachement.pk, "IDindividu": rattachement.individu_id,
                "IDfamille": rattachement.famille_id, "IDcategorie": rattachement.categorie, "titulaire": rattachement.titulaire
            }
            dictRattachementsFamilles.setdefault(rattachement.famille_id, [])
            dictRattachementsFamilles[rattachement.famille_id].append(valeurs)
            dictRattachementsIndividus.setdefault(rattachement.individu_id, [])
            dictRattachementsIndividus[rattachement.individu_id].append(valeurs)
        dictRattachements = {"familles": dictRattachementsFamilles, "individus": dictRattachementsIndividus}

        # Insertion des liens rattachés dans le dictFamilles
        for IDfamille, listeRattachements in dictRattachementsFamilles.items():
            if IDfamille in self.dictFamilles:
                for dictValeurs in listeRattachements:
                    IDindividu = dictValeurs["IDindividu"]
                    IDcategorie = dictValeurs["IDcategorie"]
                    titulaire = dictValeurs["titulaire"]
                    if titulaire == 1:
                        titulaireStr = "Oui"
                    else:
                        titulaireStr = "Non"

                    dictCibles = {
                        1: {"code": "REPRESENTANT_RATTACHE", "key": "NBRE_REPRESENTANTS_RATTACHES"},
                        2: {"code": "ENFANT_RATTACHE", "key": "NBRE_ENFANTS_RATTACHES"},
                        3: {"code": "CONTACT_RATTACHE", "key": "NBRE_CONTACTS_RATTACHES"},
                    }

                    self.dictFamilles[IDfamille][dictCibles[IDcategorie]["key"]] += 1
                    index = self.dictFamilles[IDfamille][dictCibles[IDcategorie]["key"]]
                    codeCible = dictCibles[IDcategorie]["code"] + "_%d" % index

                    # Récupération des infos sur l'individu pour transfert vers dictFamilles
                    for code, valeur in self.dictIndividus.get(IDindividu, {}).items():
                        if code.startswith("INDIVIDU"):
                            self.dictFamilles[IDfamille][code.replace("INDIVIDU", codeCible)] = valeur
                    self.dictFamilles[IDfamille][codeCible + "_TITULAIRE"] = titulaireStr

                    # Récupération du lien de l'individu rattaché dans les liens
                    listeLiens = []
                    nom_sujet = self.dictIndividus[IDindividu]["INDIVIDU_PRENOM"]
                    for dictLien in self.dictFamilles[IDfamille]["liens"]:
                        if dictLien["IDindividu_sujet"] == IDindividu:
                            nom_objet = self.dictIndividus[dictLien["IDindividu_objet"]]["INDIVIDU_PRENOM"]
                            listeLiens.append("%s de %s" % (dictLien["lien"].lower(), nom_objet))
                    texte = ""
                    if len(listeLiens) == 1:
                        texte = "%s est %s" % (nom_sujet, listeLiens[0])
                    if len(listeLiens) > 1:
                        texte = "%s est " % nom_sujet
                        texte += ", ".join(listeLiens[:-1])
                        texte += " et %s" % listeLiens[-1]
                    self.dictFamilles[IDfamille][codeCible + "_LIENS"] = texte

        return dictRattachements

    def GetLiens(self):
        """ Récupération des liens """
        dict_autorisations = {code: label for code, label in CHOIX_AUTORISATIONS}

        # Importation des liens
        liens = Lien.objects.filter(self.condition_familles)
        dictLiens = {}
        for lien in liens:
            if lien.famille_id in self.dictFamilles and lien.individu_objet_id in self.dictIndividus and lien.individu_sujet_id in self.dictIndividus:

                # Recherche les détails du lien
                if lien.idtype_lien != None:
                    sexe = self.dictIndividus[lien.individu_sujet_id]["INDIVIDU_SEXE"]
                    if sexe in ("M", "F"):
                        nomLien = DICT_TYPES_LIENS[lien.idtype_lien][sexe].capitalize()
                        typeLien = DICT_TYPES_LIENS[lien.idtype_lien]["type"]
                        texteLien = DICT_TYPES_LIENS[lien.idtype_lien]["texte"][sexe]
                    else:
                        nomLien = ""
                        typeLien = ""
                        texteLien = ""

                    # Autorisation
                    autorisation = dict_autorisations.get(lien.autorisation, "")

                    # Mémorisation de la liste
                    self.dictIndividus[lien.individu_objet_id]["liens"].append({"IDindividu": lien.individu_sujet_id, "lien": nomLien, "type": typeLien, "texte": texteLien, "autorisation": autorisation})
                    self.dictFamilles[lien.famille_id]["liens"].append({"IDindividu_sujet": lien.individu_sujet_id, "IDindividu_objet": lien.individu_objet_id, "lien": nomLien, "type": typeLien, "texte": texteLien, "autorisation": autorisation})

                    # Mémorisation des informations sur le père et la mère de l'individu uniquement au format texte
                    if lien.idtype_lien == 1:
                        if sexe == "M":
                            codeCible = "PERE"
                        else:
                            codeCible = "MERE"
                        for code, valeur in self.dictIndividus[lien.individu_sujet_id].items():
                            if code.startswith("INDIVIDU"):
                                # Mémorisation dans dictIndividus
                                self.dictIndividus[lien.individu_objet_id][code.replace("INDIVIDU", codeCible)] = valeur
                                # Mémorisation dans dictFamilles
                                self.dictFamilles[lien.famille_id][code.replace("INDIVIDU", codeCible)] = valeur
                        self.dictIndividus[lien.individu_objet_id][codeCible + "_AUTORISATION"] = autorisation
                        self.dictIndividus[lien.individu_objet_id][codeCible + "_NOM_LIEN"] = nomLien

                    # Mémorisation des informations sur le conjoint de l'individu uniquement au format texte
                    elif lien.idtype_lien in (10, 11):
                        for code, valeur in self.dictIndividus[lien.individu_sujet_id].items():
                            if code.startswith("INDIVIDU"):
                                self.dictIndividus[lien.individu_objet_id][code.replace("INDIVIDU", "CONJOINT")] = valeur
                        self.dictIndividus[lien.individu_objet_id]["CONJOINT_AUTORISATION"] = autorisation
                        self.dictIndividus[lien.individu_objet_id]["CONJOINT_NOM_LIEN"] = nomLien

                    # Mémorisation des informations sur les enfants de l'individu uniquement au format texte
                    elif lien.idtype_lien == 2:
                        self.dictIndividus[lien.individu_objet_id]["NBRE_ENFANTS"] += 1
                        codeCible = "ENFANT_%d" % self.dictIndividus[lien.individu_objet_id]["NBRE_ENFANTS"]
                        for code, valeur in self.dictIndividus[lien.individu_sujet_id].items():
                            if code.startswith("INDIVIDU"):
                                # Mémorisation dans dictIndividus
                                self.dictIndividus[lien.individu_objet_id][code.replace("INDIVIDU", codeCible)] = valeur
                                # Mémorisation dans dictFamilles
                                self.dictFamilles[lien.famille_id][code.replace("INDIVIDU", codeCible)] = valeur
                        self.dictIndividus[lien.individu_objet_id][codeCible + "_AUTORISATION"] = autorisation
                        self.dictIndividus[lien.individu_objet_id][codeCible + "_NOM_LIEN"] = nomLien

                    # Mémorisation des informations sur les autres types de liens uniquement au format texte
                    else:
                        self.dictIndividus[lien.individu_objet_id]["NBRE_AUTRES_LIENS"] += 1
                        codeCible = "AUTRE_LIEN_%d" % self.dictIndividus[lien.individu_objet_id]["NBRE_AUTRES_LIENS"]
                        for code, valeur in self.dictIndividus[lien.individu_sujet_id].items():
                            if code.startswith("INDIVIDU"):
                                # Mémorisation dans dictIndividus
                                self.dictIndividus[lien.individu_objet_id][code.replace("INDIVIDU", codeCible)] = valeur
                                # Mémorisation dans dictFamilles
                                self.dictFamilles[lien.famille_id][code.replace("INDIVIDU", codeCible)] = valeur
                        self.dictIndividus[lien.individu_objet_id][codeCible + "_AUTORISATION"] = autorisation
                        self.dictIndividus[lien.individu_objet_id][codeCible + "_NOM_LIEN"] = nomLien

        return dictLiens

    def GetDictFamilles(self):
        """ Récupération des infos de base sur les familles """
        condition = Q(pk__in=self.liste_familles) if self.liste_familles else Q()
        familles = Famille.objects.select_related('caisse', 'caisse__regime', 'secteur').filter(condition)
        dictFamilles = {}
        for famille in familles:
            dictFamilles[famille.pk] = {
                "FAMILLE_DATE_CREATION": utils_dates.ConvertDateToFR(famille.date_creation),
                "FAMILLE_NOM_CAISSE": famille.caisse.nom if famille.caisse else "",
                "FAMILLE_NOM_REGIME": famille.caisse.regime.nom if famille.caisse else "",
                "FAMILLE_NUM_ALLOCATAIRE": famille.num_allocataire,
                "IDallocataire": famille.allocataire_id,
                "FAMILLE_NOM_ALLOCATAIRE": self.dictIndividus[famille.allocataire_id]["INDIVIDU_NOM_COMPLET"] if famille.allocataire_id else "",
                "FAMILLE_MEMO": famille.memo,
                "FAMILLE_NOM": famille.nom,
                "FAMILLE_RUE": famille.rue_resid,
                "FAMILLE_CP": famille.cp_resid,
                "FAMILLE_VILLE": famille.ville_resid,
                "FAMILLE_SECTEUR": famille.secteur.nom if famille.secteur else "",
                "IDFAMILLE": str(famille.pk),
                "liens": [],
                "NBRE_REPRESENTANTS_RATTACHES": 0,
                "NBRE_ENFANTS_RATTACHES": 0,
                "NBRE_CONTACTS_RATTACHES": 0,
            }
        return dictFamilles

    def RechercheQF(self):
        """ Recherche les QF des familles """
        quotients = Quotient.objects.filter(self.condition_familles)
        for quotient in quotients:
            if quotient.famille_id in self.dictFamilles:
                # Mémorisation du QF actuel au format texte
                if quotient.date_debut <= self.date_reference and quotient.date_fin >= self.date_reference:
                    self.dictFamilles[quotient.famille_id]["FAMILLE_QF_ACTUEL"] = str(quotient.quotient)
                    self.dictFamilles[quotient.famille_id]["FAMILLE_QF_ACTUEL_INT"] = quotient.quotient
                # Mémorisation sous forme de liste
                if "qf" not in self.dictFamilles[quotient.famille_id]:
                    self.dictFamilles[quotient.famille_id]["qf"] = []
                self.dictFamilles[quotient.famille_id]["qf"].append({
                    "IDquotient": quotient.pk, "date_debut": utils_dates.ConvertDateToFR(quotient.date_debut),
                     "date_fin": utils_dates.ConvertDateToFR(quotient.date_fin), "quotient": quotient.quotient, "observations": quotient.observations
                })

    def RechercheInscriptions(self):
        """ Récupération des inscriptions à des activités """
        inscriptions = Inscription.objects.select_related('famille', 'activite', 'groupe', 'categorie_tarif').filter(self.condition_familles)
        for inscription in inscriptions:
            # Mémorise le nombre d'inscriptions
            if "inscriptions" not in self.dictIndividus[inscription.individu_id]:
                self.dictIndividus[inscription.individu_id]["inscriptions"] = {"nombre": 0, "liste": []}
            self.dictIndividus[inscription.individu_id]["inscriptions"]["nombre"] += 1

            # Mémorise l'inscription au format texte
            index = self.dictIndividus[inscription.individu_id]["inscriptions"]["nombre"]
            code = "INSCRIPTION_%d_" % index
            self.dictIndividus[inscription.individu_id][code + "ACTIVITE"] = inscription.activite.nom
            self.dictIndividus[inscription.individu_id][code + "GROUPE"] = inscription.groupe.nom
            self.dictIndividus[inscription.individu_id][code + "CATEGORIE_TARIF"] = inscription.categorie_tarif.nom
            self.dictIndividus[inscription.individu_id][code + "NOM_TITULAIRES"] = inscription.famille.nom
            self.dictIndividus[inscription.individu_id][code + "PARTI"] = "Oui" if (inscription.date_fin and inscription.date_fin < datetime.date.today()) else "Non"
            self.dictIndividus[inscription.individu_id][code + "DATE_INSCRIPTION"] = utils_dates.ConvertDateToFR(inscription.date_debut)

            # Mémorise l'inscription au format liste
            self.dictIndividus[inscription.individu_id]["inscriptions"]["liste"].append(
                {"index": index, "activite": inscription.activite.nom, "groupe": inscription.groupe.nom, "categorie_tarif": inscription.categorie_tarif.nom,
                 "nomTitulaires": inscription.famille.nom, "parti": "Oui" if (inscription.date_fin and inscription.date_fin < datetime.date.today()) else "Non",
                 "date_inscription": utils_dates.ConvertDateToFR(inscription.date_debut)})

    def RechercheInfosMedicales(self):
        """ Récupération des informations personnelles des individus """
        problemes = Information.objects.select_related('categorie').all()
        for probleme in problemes:
            # Mémorise le nombre d'informations personnelles
            if "medical" not in self.dictIndividus[probleme.individu_id]:
                self.dictIndividus[probleme.individu_id]["medical"] = {"nombre": 0, "liste": []}
            self.dictIndividus[probleme.individu_id]["medical"]["nombre"] += 1

            # Mémorise l'information médicale au format texte
            index = self.dictIndividus[probleme.individu_id]["medical"]["nombre"]
            code = "MEDICAL_%d_" % index
            self.dictIndividus[probleme.individu_id][code + "INTITULE"] = probleme.intitule
            self.dictIndividus[probleme.individu_id][code + "DESCRIPTION"] = probleme.description
            self.dictIndividus[probleme.individu_id][code + "TRAITEMENT_MEDICAL"] = probleme.traitement_medical
            self.dictIndividus[probleme.individu_id][code + "DESCRIPTION_TRAITEMENT"] = probleme.description_traitement
            self.dictIndividus[probleme.individu_id][code + "DATE_DEBUT_TRAITEMENT"] = utils_dates.ConvertDateToFR(probleme.date_debut_traitement)
            self.dictIndividus[probleme.individu_id][code + "DATE_FIN_TRAITEMENT"] = utils_dates.ConvertDateToFR(probleme.date_fin_traitement)

            # Mémorise l'information médicale au format liste
            self.dictIndividus[probleme.individu_id]["medical"]["liste"].append(
                {"categorie": probleme.categorie.nom, "intitule": probleme.intitule, "description": probleme.description,
                 "traitement_medical": probleme.traitement_medical, "description_traitement": probleme.description_traitement,
                 "date_debut_traitement": utils_dates.ConvertDateToFR(probleme.date_debut_traitement),
                 "date_fin_traitement": utils_dates.ConvertDateToFR(probleme.date_fin_traitement),
                 })

    def RechercheMessages(self):
        """ Recherche les messages des familles et des individus """
        notes = Note.objects.select_related('categorie').all()
        for note in notes:
            for ID, dictCible in [(note.individu_id, self.dictIndividus), (note.famille_id, self.dictFamilles)]:
                if ID:
                    if ID in dictCible:
                        if "messages" not in dictCible[ID]:
                            dictCible[ID]["messages"] = {"nombre": 0, "liste": []}
                        dictCible[ID]["messages"]["nombre"] += 1

                        # Mémorise l'information médicale au format texte
                        index = dictCible[ID]["messages"]["nombre"]
                        code = "MESSAGE_%d_" % index
                        dictCible[ID][code + "DATE_SAISIE"] = utils_dates.ConvertDateToFR(note.date_saisie)
                        dictCible[ID][code + "DATE_PARUTION"] = utils_dates.ConvertDateToFR(note.date_parution)
                        dictCible[ID][code + "TEXTE"] = note.texte
                        #dictCible[ID][code + "NOM"] = note.nom
                        dictCible[ID][code + "CATEGORIE"] = note.categorie.nom if note.categorie else ""

                        # Mémorise l'information médicale au format liste
                        dictCible[ID]["messages"]["liste"].append(
                            {"IDmessage": str(note.pk), "type": note.type, "IDcategorie": note.categorie_id,
                             "date_saisie": utils_dates.ConvertDateToFR(note.date_saisie), "date_parution": utils_dates.ConvertDateToFR(note.date_parution),
                             "priorite": note.priorite,  "afficher_accueil": note.afficher_accueil,
                             "afficher_liste": note.afficher_liste, "texte": note.texte, #"nom": note.nom,
                             "categorie_nom": note.categorie.nom if note.categorie else "",
                             })

    def RechercheCotisationsManquantes(self):
        """ Récupération de la liste des cotisations manquantes """
        dictCotisations = UTILS_Cotisations_manquantes.GetListeCotisationsManquantes(dateReference=self.date_reference)
        for IDfamille, dictValeurs in dictCotisations.items():
            if IDfamille in self.dictFamilles:
                self.dictFamilles[IDfamille]["COTISATIONS_MANQUANTES"] = dictValeurs["cotisations"]

    def RecherchePiecesManquantes(self):
        """ Recherche des pièces manquantes """
        dictPieces = utils_pieces_manquantes.Get_liste_pieces_manquantes(date_reference=self.date_reference, liste_familles=self.liste_familles)
        for IDfamille, dictValeurs in dictPieces.items():
            if IDfamille in self.dictFamilles:
                self.dictFamilles[IDfamille]["PIECES_MANQUANTES"] = dictValeurs["texte"]

    def RechercheQuestionnaires(self):
        """ Récupération des questionnaires familiaux et individuels """
        for public, dictPublic in [("famille", self.dictFamilles), ("individu", self.dictIndividus)]:
            q = utils_questionnaires.ChampsEtReponses(categorie=public)
            for ID in list(dictPublic.keys()):
                if ID in dictPublic:
                    if "questionnaires" not in dictPublic[ID]:
                        dictPublic[ID]["questionnaires"] = []
                    listeDonnees = q.GetDonnees(ID, formatStr=False)
                    for donnee in listeDonnees:
                        # Mémorisation de la liste
                        dictPublic[ID]["questionnaires"].append(donnee)
                        # Mémorisation au format texte
                        code = donnee["champ"].replace("{", "").replace("}", "")
                        dictPublic[ID][code] = donnee["reponse"]

    def RechercheScolarite(self):
        """ Recherche les étapes de scolarité des individus """
        scolarites = Scolarite.objects.select_related('ecole', 'classe', 'niveau').all()
        for scolarite in scolarites:
            if scolarite.date_debut <= self.date_reference and scolarite.date_fin >= self.date_reference:
                self.dictIndividus[scolarite.individu_id]["SCOLARITE_DATE_DEBUT"] = utils_dates.ConvertDateToFR(scolarite.date_debut)
                self.dictIndividus[scolarite.individu_id]["SCOLARITE_DATE_FIN"] = utils_dates.ConvertDateToFR(scolarite.date_fin)
                self.dictIndividus[scolarite.individu_id]["SCOLARITE_NOM_ECOLE"] = scolarite.ecole.nom if scolarite.ecole else ""
                self.dictIndividus[scolarite.individu_id]["SCOLARITE_NOM_CLASSE"] = scolarite.classe.nom if scolarite.classe else ""
                self.dictIndividus[scolarite.individu_id]["SCOLARITE_NOM_NIVEAU"] = scolarite.niveau.nom if scolarite.niveau else ""
                self.dictIndividus[scolarite.individu_id]["SCOLARITE_ABREGE_NIVEAU"] = scolarite.niveau.abrege if scolarite.niveau else ""

            if "scolarite" not in self.dictIndividus[scolarite.individu_id]:
                self.dictIndividus[scolarite.individu_id]["scolarite"] = {"nombre": 0, "liste": []}
            self.dictIndividus[scolarite.individu_id]["scolarite"]["nombre"] += 1

            # Mémorise l'étape de scolarité au format liste
            self.dictIndividus[scolarite.individu_id]["scolarite"]["liste"].append({
                "date_debut": utils_dates.ConvertDateToFR(scolarite.date_debut), "date_fin": utils_dates.ConvertDateToFR(scolarite.date_fin),
                "ecole_nom": scolarite.ecole.nom if scolarite.ecole else "",
                "classe_nom": scolarite.classe.nom if scolarite.classe else "",
                "niveau_nom": scolarite.niveau.nom if scolarite.niveau else "",
                "niveau_abrege": scolarite.niveau.abrege if scolarite.niveau else "",
            })

    # ---------------------------------------------------------------------------------------------------------------------------------

    def RechercheCotisations(self):
        """ Recherche la cotisation actuelle des individus """
        cotisations = Cotisation.objects.select_related('type_cotisation', 'unite_cotisation').all()
        for cotisation in cotisations:
            if cotisation.individu_id:
                if cotisation.date_debut <= self.date_reference and cotisation.date_fin >= self.date_reference:
                    self.dictIndividus[cotisation.individu_id]["COTISATION_DATE_DEBUT"] = utils_dates.ConvertDateToFR(cotisation.date_debut)
                    self.dictIndividus[cotisation.individu_id]["COTISATION_DATE_FIN"] = utils_dates.ConvertDateToFR(cotisation.date_fin)
                    self.dictIndividus[cotisation.individu_id]["COTISATION_TYPE"] = cotisation.type_cotisation.nom
                    self.dictIndividus[cotisation.individu_id]["COTISATION_UNITE"] = cotisation.unite_cotisation.nom
                    self.dictIndividus[cotisation.individu_id]["COTISATION_NUMERO"] = cotisation.numero

                if "cotisations" not in self.dictIndividus[cotisation.individu_id]:
                    self.dictIndividus[cotisation.individu_id]["cotisations"] = {"nombre": 0, "liste": []}
                self.dictIndividus[cotisation.individu_id]["cotisations"]["nombre"] += 1

                # Mémorise l'étape de scolarité au format liste
                self.dictIndividus[cotisation.individu_id]["cotisations"]["liste"].append({
                    "date_debut": utils_dates.ConvertDateToFR(cotisation.date_debut), "date_fin": utils_dates.ConvertDateToFR(cotisation.date_fin),
                    "nom_type": cotisation.type_cotisation.nom, "nom_unite": cotisation.unite_cotisation.nom, "numero": cotisation.numero})

    # ---------------------------------------------------------------------------------------------------------------------------------






    def GetNomsChampsPresents(self, mode="individu+famille", listeID=None):
        """ Renvoie les noms des champs disponibles après calcul des données. """
        """ mode='individu' ou 'famille' ou 'individu+famille' """
        """ listeID = [liste IDindividu ou IDfamille] ou None pour tous """
        listeNomsChamps = []
        for modeTemp, dictTemp in [("individu", self.dictIndividus), ("famille", self.dictFamilles)]:
            if modeTemp in mode:
                for ID, dictValeurs in dictTemp.items():
                    if listeID == None or ID in listeID:
                        if type(dictValeurs) == dict:
                            for key, valeur in dictValeurs.items():
                                if key[0] == key[0].upper() and key not in listeNomsChamps:
                                    listeNomsChamps.append(key)
        listeNomsChamps.sort()
        return listeNomsChamps

    def GetDictValeurs(self, mode="individu", ID=None, formatChamp=True):
        """ mode = 'individu' ou 'famille' """
        """ ID = IDindividu ou IDfamille ou None pour avoir tout le monde """
        """ formatChamp = Pour avoir uniquement les keys pour publipostage au format {xxx} """

        def FormateDict(dictTemp2):
            if formatChamp == True:
                dictFinal = {}
                for key, valeur in dictTemp2.items():
                    if key[0] == key[0].upper():
                        dictFinal["{%s}" % key] = valeur
                return dictFinal
            else:
                return dictTemp2

        if mode == "individu":
            dictTemp = self.dictIndividus
        else:
            dictTemp = self.dictFamilles
        if ID != None:
            if (ID in dictTemp) == False:
                return {}
            else:
                return FormateDict(dictTemp[ID])
        else:
            if formatChamp == True:
                dictFinal2 = {}
                for ID, dictValeurs in dictTemp.items():
                    dictFinal2[ID] = FormateDict(dictValeurs)
                return dictFinal2
            else:
                return dictTemp

    def SetAsAttributs(self, parent=None, mode="individu", ID=None):
        """ Attribue les valeurs en tant que attribut à un module. Sert pour les tracks des objectlistview """
        dictDonnees = self.GetDictValeurs(mode=mode, ID=ID, formatChamp=False)
        for code, valeur in dictDonnees.items():
            setattr(parent, code, valeur)

    def StockageTable(self, mode="famille"):
        """ Stockage des infos dans une table SQLITE """
        listeNomsChamps = self.GetNomsChampsPresents(mode=mode)

        DB = GestionDB.DB()

        nomTable = "table_test"

        # Suppression de la table si elle existe
        DB.ExecuterReq("DROP TABLE IF EXISTS %s" % nomTable)

        # Création de la table de données
        req = "CREATE TABLE IF NOT EXISTS %s (ID INTEGER PRIMARY KEY AUTOINCREMENT, " % nomTable
        for nom in listeNomsChamps:
            req += "%s %s, " % (nom, "VARCHAR(500)")
        req = req[:-2] + ")"
        DB.ExecuterReq(req)

        # Insertion des données
        dictValeurs = self.GetDictValeurs(mode=mode, formatChamp=False)
        listeDonnees = []
        for ID, dictTemp in dictValeurs.items():
            listeValeurs = [ID, ]
            for champ in listeNomsChamps:
                if champ in dictTemp:
                    valeur = dictTemp[champ]
                else:
                    valeur = ""
                listeValeurs.append(valeur)
            listeDonnees.append(listeValeurs)

        listeNomsChamps.insert(0, "ID")
        req = "INSERT INTO %s (%s) VALUES (%s)" % (
        nomTable, ", ".join(listeNomsChamps), ",".join("?" * len(listeNomsChamps)))
        DB.Executermany(req=req, listeDonnees=listeDonnees, commit=True)

        DB.Close()

    def StockagePickleFichier(self, mode="famille"):#, nomFichier=UTILS_Fichiers.GetRepTemp(fichier="infos_individus.pickle")):
        import pickle
        dictValeurs = self.GetDictValeurs(mode=mode, formatChamp=False)
        fichier = open(nomFichier, 'wb')
        pickle.dump(dictValeurs, fichier)

    def GetPickleChaine(self, mode="famille", cryptage=False):
        dictValeurs = self.GetDictValeurs(mode=mode, formatChamp=False)
        chaine = cPickle.dumps(dictValeurs)
        if cryptage == True:
            chaine = base64.b64encode(chaine)
        return chaine

    def EnregistreFichier(self, mode="famille"):#, nomFichier=UTILS_Fichiers.GetRepTemp(fichier="infos_f.dat")):
        chaine = self.GetPickleChaine(mode=mode, cryptage=True)
        fichier = open(nomFichier, "w")
        fichier.write(chaine)
        fichier.close()

    def LectureFichier(self):#, nomFichier=UTILS_Fichiers.GetRepTemp(fichier="infos_f.dat")):
        fichier = open(nomFichier, "r")
        chaine = fichier.read()
        fichier.close()
        chaine = base64.b64decode(chaine)
        dictTemp = cPickle.loads(chaine)
        return dictTemp

    def EnregistreDansDB(self):#, nomFichier=UTILS_Fichiers.GetRepTemp(fichier="database.dat")):
        dbdest = GestionDB.DB(suffixe=None, nomFichier=nomFichier, modeCreation=True)
        dictTables = {

            "individus": [("IDindividu", "INTEGER PRIMARY KEY AUTOINCREMENT", "ID de la personne"),
                          ("IDcivilite", "INTEGER", "Civilité de la personne"),
                          ("nom", "VARCHAR(100)", "Nom de famille de la personne"),
                          ("prenom", "VARCHAR(100)", "Prénom de la personne"),
                          ("photo", "BLOB", "Photo de la personne"),
                          ],

            "informations": [("IDinfo", "INTEGER PRIMARY KEY AUTOINCREMENT", "ID de la ligne"),
                             ("IDindividu", "INTEGER", "ID de la personne"),
                             ("champ", "VARCHAR(500)", "Nom du champ"),
                             ("valeur", "VARCHAR(500)", "Valeur du champ"),
                             ]}
        try:
            dbdest.CreationTables(dicoDB=dictTables)
        except:
            pass

        def Enregistre(nomTable, listeChamps, listeDonnees):
            txtChamps = ", ".join(listeChamps)
            txtQMarks = ", ".join(["?" for x in listeChamps])
            req = "INSERT INTO %s (%s) VALUES (%s)" % (nomTable, txtChamps, txtQMarks)
            dbdest.cursor.executemany(req, listeDonnees)

        # Insertion des données du dictIndividus
        dictValeurs = self.GetDictValeurs(mode="individu", formatChamp=False)
        listeDonnees = []
        for ID, dictTemp in dictValeurs.items():
            for champ, valeur in dictTemp.items():
                if type(valeur) in (str, six.text_type) and valeur not in ("", None):
                    listeDonnees.append((ID, champ, valeur))

        Enregistre(nomTable="informations", listeChamps=["IDindividu", "champ", "valeur"], listeDonnees=listeDonnees)

        # Insertion des données individus
        db = GestionDB.DB(suffixe="PHOTOS")
        req = """SELECT IDindividu, photo FROM photos;"""
        db.ExecuterReq(req)
        listePhotos = db.ResultatReq()
        db.Close()
        dictPhotos = {}
        for IDindividu, photo in listePhotos:
            dictPhotos[IDindividu] = photo

        db = GestionDB.DB()
        req = """SELECT IDindividu, IDcivilite, nom, prenom FROM individus;"""
        db.ExecuterReq(req)
        listeIndividus = db.ResultatReq()
        db.Close()
        listeDonnees = []
        for IDindividu, IDcivilite, nom, prenom in listeIndividus:
            if IDindividu in dictPhotos:
                photo = sqlite3.Binary(dictPhotos[IDindividu])
            else:
                photo = None
            listeDonnees.append((IDindividu, IDcivilite, nom, prenom, photo))

        Enregistre(nomTable="individus", listeChamps=["IDindividu", "IDcivilite", "nom", "prenom", "photo"],
                   listeDonnees=listeDonnees)

        # Cloture de la base
        dbdest.connexion.commit()
        dbdest.Close()

    # ---------------------------------------------------------------------------------------------------------------------------------

    def Tests(self):
        """ Pour les tests """
        # Récupération des noms des champs
        # print len(self.GetNomsChampsPresents(mode="individu", listeID=None))
        print(len(GetNomsChampsPossibles(mode="individu")))  # for x in self.GetNomsChampsPresents(mode="individu", listeID=None) :  # print x

        # self.EnregistreFichier(mode="individu", nomFichier="Temp/infos_individus.dat")   # self.EnregistreDansDB()



if __name__ == '__main__':
    infos = Informations()
    infos.Tests()
