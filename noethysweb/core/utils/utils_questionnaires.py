# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
import datetime
from core.utils import utils_dates
from core.data import data_civilites
from core.models import LISTE_CONTROLES_QUESTIONNAIRES, QuestionnaireQuestion, QuestionnaireReponse
from django.db.models import Q


def Creation_reponses(categorie="famille", liste_instances=[], question=None):
    """ Création des réponses par défaut pour les questionnaires """
    """ à utiliser à la création de fiches familles ou individuelles, et de nouvelles questions """
    logger.debug("Création des réponses des questionnaires de type %s" % categorie)
    logger.debug("Recherche sur %d %ss..." % (len(liste_instances), categorie))

    # Importation des questions
    condition = Q(categorie=categorie)
    if question:
        condition &= Q(pk=question.pk)
    questions = QuestionnaireQuestion.objects.filter(condition)

    # Importation des réponses existantes
    condition = Q(**{categorie + "__in": liste_instances}) if liste_instances else Q()
    if question:
        condition &= Q(question=question)
    reponses_existantes = [(getattr(reponse, categorie + "_id"), reponse.question_id) for reponse in QuestionnaireReponse.objects.filter(condition)]

    # Création des questions
    liste_ajouts = []
    for instance in liste_instances:
        for question in questions:
            if (instance.pk, question.pk) not in reponses_existantes:
                reponse = None
                if question.controle in ("liste_deroulante", "liste_coches"):
                    reponse = ""
                if question.controle == "case_coche":
                    reponse = "False"
                donnees = {categorie: instance, "question": question, "reponse": reponse}
                liste_ajouts.append(QuestionnaireReponse(**donnees))

    # Enregistrement dans la base
    if liste_ajouts:
        QuestionnaireReponse.objects.bulk_create(liste_ajouts)

    logger.debug("%d réponses créées" % len(liste_ajouts))




def FormateStr(valeur=u""):
    try :
        if valeur == None : return u""
        elif type(valeur) == int : return str(valeur)
        elif type(valeur) == float : return str(valeur)
        else : return valeur
    except : 
        return u""

def GetReponse(dictReponses={}, IDquestion=None, ID=None):
    if IDquestion in dictReponses :
        if ID in dictReponses[IDquestion] :
            return dictReponses[IDquestion][ID]
    return u""

def FormateDate(date):
    if date in (None, "") : return ""
    if type(date) == datetime.date :
        return UTILS_Dates.DateDDEnFr(date)
    return datetime.date(int(date[:4]), int(date[5:7]), int(date[8:10]))

def GetColonnesForOL(liste_questions=[]):
    """ Ajout des questions des questionnaires aux colonnes d'un OL """
    liste_colonnes = []
    for dictQuestion in liste_questions:
        Formatter = None
        filtre = dictQuestion["filtre"]
        if filtre == "texte":
            typeDonnee = "texte"
        elif filtre == "entier":
            typeDonnee = "entier"
        elif filtre == "montant":
            typeDonnee = "montant"
        elif filtre == "choix":
            typeDonnee = "texte"
        elif filtre == "coche":
            typeDonnee = "texte"
        elif filtre == "date":
            typeDonnee = "date"
            Formatter = FormateDate
        else:
            typeDonnee = "texte"
        liste_colonnes.append(ColumnDefn(dictQuestion["label"], "left", 150, "question_%d" % dictQuestion["IDquestion"], stringConverter=Formatter, typeDonnee=typeDonnee))
    return liste_colonnes




class Questionnaires():
    def __init__(self):
        self.dictControles = self.GetControles()
        # self.dictChoix = self.GetChoix()
    
    def GetControles(self):
        dictControles = {}
        for dictControle in LISTE_CONTROLES_QUESTIONNAIRES:
            dictControles[dictControle["code"]] = dictControle
        return dictControles
    
    # def GetChoix(self):
    #     DB = GestionDB.DB()
    #     req = """SELECT IDchoix, IDquestion, label
    #     FROM questionnaire_choix;"""
    #     DB.ExecuterReq(req)
    #     listeChoix = DB.ResultatReq()
    #     dictChoix = {}
    #     for IDchoix, IDquestion, label in listeChoix :
    #         dictChoix[IDchoix] = label
    #     DB.Close()
    #     return dictChoix
    
    def GetFiltre(self, controle=""):
        if controle in self.dictControles:
            return self.dictControles[controle]["filtre"]
        else:
            return None

    def FormatageReponse(self, reponse="", controle=""):
        filtre = self.GetFiltre(controle)
        texteReponse = u""
        if filtre == "texte" : texteReponse = reponse
        if filtre == "entier" : texteReponse = int(reponse)
        if filtre == "montant" : texteReponse = float(reponse)#decimal.Decimal(reponse)
        if filtre == "choix" :
            if reponse != None :
                if type(reponse) == int:
                    listeTemp = [reponse,]
                else:
                    listeTemp = reponse.split(";")
                listeTemp2 = []
                for IDchoix in listeTemp :
                    try :
                        IDchoix = int(IDchoix)
                        if IDchoix in self.dictChoix :
                            listeTemp2.append(self.dictChoix[IDchoix])
                    except :
                        pass
                texteReponse = ", ".join(listeTemp2)
        if filtre == "coche":
            if reponse in (1, "1"):
                texteReponse = "Oui"
            else :
                texteReponse = "Non"
        if filtre == "date":
            texteReponse = DateEngEnDateDD(reponse)
        return texteReponse


    def GetQuestions(self, categorie="individu", avec_filtre=True):
        """ Type = None (tout) ou 'individu' ou 'famille' """
        if categorie:
            condition = Q(categorie=categorie)
        else:
            condition = Q()
        liste_questions = QuestionnaireQuestion.objects.filter(condition).order_by("ordre")
        liste_resultats = []
        try:
            for question in liste_questions:
                if not avec_filtre or self.GetFiltre(question.controle):
                    liste_resultats.append({"IDquestion": question.pk, "label": question.label, "categorie": question.categorie,
                                            "controle": question.controle, "filtre": self.GetFiltre(question.controle)})
        except:
            pass
        return liste_resultats


    def GetReponses(self, categorie="individu"):
        """ Récupération des réponses des questionnaires """
        # Importation des questions
        liste_reponses = QuestionnaireReponse.objects.select_related('question').filter(question__categorie=categorie)
        dictReponses = {}
        for reponse in liste_reponses:
            filtre = self.GetFiltre(reponse.question.controle)
            if filtre != None :
                # Formatage de la réponse
                texteReponse = self.FormatageReponse(reponse.reponse, reponse.question.controle) if reponse.reponse else ""

                # Mémorisation
                if reponse.individu_id:
                    ID = reponse.individu_id
                elif reponse.famille_id:
                    ID = reponse.famille_id
                else:
                    ID = reponse.donnee
                if reponse.question_id not in dictReponses:
                    dictReponses[reponse.question_id] = {}
                if ID not in dictReponses[reponse.question_id]:
                    dictReponses[reponse.question_id][ID] = texteReponse
            
        return dictReponses

    def GetReponse(self, IDquestion=None, IDfamille=None, IDindividu=None):
        DB = GestionDB.DB()        
        req = """SELECT IDreponse, IDindividu, IDfamille, reponse, controle
        FROM questionnaire_reponses
        LEFT JOIN questionnaire_questions ON questionnaire_questions.IDquestion = questionnaire_reponses.IDquestion
        WHERE questionnaire_reponses.IDquestion=%d AND (IDindividu=%d OR IDfamille=%d)
        ;""" % (IDquestion, IDindividu, IDfamille)
        DB.ExecuterReq(req)
        listeReponses = DB.ResultatReq()
        DB.Close() 
        if len(listeReponses) == 0 :
            return None
        dictReponses = {}
        IDreponse, IDindividu, IDfamille, reponse, controle = listeReponses[0]
        filtre = self.GetFiltre(controle)
        texteReponse = None
        if filtre != None :
            # Formatage de la réponse
            if reponse == None :
                texteReponse = u""
            else :
                texteReponse = self.FormatageReponse(reponse, controle)
        return texteReponse
        

class ChampsEtReponses():
    """ Retourne une donnée de type "{QUESTION_24}" = valeur """
    def __init__(self, categorie="individu"):
        questionnaires = Questionnaires()
        self.listeQuestions = questionnaires.GetQuestions(categorie=categorie)
        self.dictReponses = questionnaires.GetReponses(categorie=categorie)

    def GetDonnees(self, ID, formatStr=True):
        listeDonnees = []
        for dictQuestion in self.listeQuestions:
            reponse = GetReponse(self.dictReponses, dictQuestion["IDquestion"], ID)
            if formatStr == True :
                reponse = FormateStr(reponse)
            champ = "{QUESTION_%d}" % dictQuestion["IDquestion"]
            dictReponse = {
                "champ": champ, "reponse":reponse, "IDquestion": dictQuestion["IDquestion"], "label": dictQuestion["label"],
                "categorie": dictQuestion["categorie"], "controle": dictQuestion["controle"],
                #"defaut": dictQuestion["defaut"]
                }
            listeDonnees.append(dictReponse)
        return listeDonnees
