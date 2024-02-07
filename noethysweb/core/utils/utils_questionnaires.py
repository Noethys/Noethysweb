# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.models import LISTE_CONTROLES_QUESTIONNAIRES, QuestionnaireQuestion, QuestionnaireReponse
from core.utils import utils_dates


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
        texteReponse = ""
        if filtre == "texte" : texteReponse = reponse
        if filtre == "entier" : texteReponse = int(reponse)
        if filtre == "decimal": texteReponse = float(reponse)
        if filtre == "montant" : texteReponse = float(reponse)#decimal.Decimal(reponse)
        if filtre == "choix" :
            if reponse:
                texteReponse = ", ".join(reponse.split(";"))
        if filtre == "coche":
            texteReponse = "Oui" if reponse in (1, "1", True, "True") else "Non"
        if filtre == "date":
            texteReponse = utils_dates.ConvertDateToFR(reponse) or ""
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
                                            "controle": question.controle, "filtre": self.GetFiltre(question.controle),
                                            "visible_fiche_renseignement": question.visible_fiche_renseignement})
        except:
            pass
        return liste_resultats

    def GetReponses(self, categorie="individu", filtre=None):
        """ Récupération des réponses des questionnaires """
        # Filtre sur les réponses
        filtres_reponses = Q(question__categorie=categorie)
        if filtre:
            filtres_reponses &= filtre

        # Importation des réponses
        liste_reponses = QuestionnaireReponse.objects.select_related('question').filter(filtres_reponses)
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
                elif reponse.collaborateur_id:
                    ID = reponse.collaborateur_id
                else:
                    ID = reponse.donnee
                if reponse.question_id not in dictReponses:
                    dictReponses[reponse.question_id] = {}
                if ID not in dictReponses[reponse.question_id]:
                    dictReponses[reponse.question_id][ID] = texteReponse
            
        return dictReponses


class ChampsEtReponses():
    """ Retourne une donnée de type "{QUESTION_24}" = valeur """
    """ Option : filtres_reponses = Q(collaborateur_is__in=(1, 2, 3)) """
    def __init__(self, categorie="individu", filtre_reponses=None):
        questionnaires = Questionnaires()
        self.listeQuestions = questionnaires.GetQuestions(categorie=categorie)
        self.dictReponses = questionnaires.GetReponses(categorie=categorie, filtre=filtre_reponses)

    def GetDonnees(self, ID, formatStr=True):
        listeDonnees = []
        for dictQuestion in self.listeQuestions:
            reponse = GetReponse(self.dictReponses, dictQuestion["IDquestion"], ID)
            if formatStr == True :
                reponse = FormateStr(reponse)
            champ = "{QUESTION_%d}" % dictQuestion["IDquestion"]
            dictReponse = {
                "champ": champ, "reponse":reponse, "IDquestion": dictQuestion["IDquestion"], "label": dictQuestion["label"],
                "categorie": dictQuestion["categorie"], "controle": dictQuestion["controle"], "visible_fiche_renseignement": dictQuestion["visible_fiche_renseignement"],
                #"defaut": dictQuestion["defaut"]
                }
            listeDonnees.append(dictReponse)
        return listeDonnees
