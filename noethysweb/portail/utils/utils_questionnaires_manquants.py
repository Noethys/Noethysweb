# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from core.models import Individu, Rattachement, Inscription, QuestionnaireQuestion, QuestionnaireReponse, Activite

def est_question_complétée(reponse):
    """
    Vérifie si une réponse à une question est réellement complétée.
    """
    if not reponse:
        return False

    valeur = reponse.Get_reponse_for_ctrl()  # récupère la valeur réelle comme pour le formulaire

    if valeur is None:
        return False

    # Cas booléen : False est une réponse valide
    if isinstance(reponse.question.controle, str) and reponse.question.controle == "case_coche":
        return True

    # Cas texte / textarea
    if isinstance(valeur, str):
        return bool(valeur.strip())

    # Cas liste à choix multiples
    if isinstance(valeur, (list, tuple)):
        return len(valeur) > 0

    # Cas entier / decimal / slider / date
    if isinstance(valeur, (int, float, complex)):
        return True
    if hasattr(valeur, 'isoformat'):  # date ou datetime
        return True

    return False

def Get_question_individu(individu):
    """
    Retourne la liste des questions non complétées pour l'individu.
    """
    # Activités de l'individu
    inscriptions = Inscription.objects.filter(individu=individu)
    activite_ids = inscriptions.values_list('activite', flat=True).distinct()
    activites = Activite.objects.filter(idactivite__in=activite_ids, structure__visible=True)

    # Toutes les questions
    questions = QuestionnaireQuestion.objects.filter(
        categorie="individu",
        visible_portail=True,
        activite__in=activites
    ).order_by("ordre")

    # Filtrage des questions non complétées
    questions_non_complétées = []
    for question in questions:
        reponse = QuestionnaireReponse.objects.filter(
            individu=individu,
            question=question
        ).first()
        if not reponse or not est_question_complétée(reponse):
            questions_non_complétées.append(question)

    return questions_non_complétées


def Get_questions_par_inscriptions(inscriptions):
    """
    Version optimisée : retourne les questions manquantes par individu pour une liste d'inscriptions.
    BATCH : 3 requêtes SQL au total peu importe le nombre d'inscriptions.

    Args:
        inscriptions: QuerySet ou liste d'instances Inscription

    Returns:
        dict[individu.pk] -> liste de questions non complétées
    """
    inscriptions_list = list(inscriptions)
    
    if not inscriptions_list:
        return {}

    # Extraire tous les individus et activités
    individus = list(set(ins.individu for ins in inscriptions_list))
    individu_ids = [ind.pk for ind in individus]
    activite_ids = list(set(ins.activite_id for ins in inscriptions_list))

    # UNE requête pour toutes les activités avec structures visibles
    activites = Activite.objects.filter(
        idactivite__in=activite_ids,
        structure__visible=True
    )

    # UNE requête pour toutes les questions
    questions = QuestionnaireQuestion.objects.filter(
        categorie="individu",
        visible_portail=True,
        activite__in=activites
    ).order_by("ordre")

    # UNE requête pour toutes les réponses de tous les individus
    reponses_qs = QuestionnaireReponse.objects.filter(
        individu__in=individu_ids,
        question__in=questions
    ).select_related('question')

    # Construire un dict de lookup : (individu_id, question_id) -> reponse
    dict_reponses = {}
    for reponse in reponses_qs:
        key = (reponse.individu_id, reponse.question_id)
        dict_reponses[key] = reponse

    # Construire les résultats par individu
    dict_resultats = {}
    for individu in individus:
        questions_non_completees = []
        for question in questions:
            key = (individu.pk, question.pk)
            reponse = dict_reponses.get(key, None)
            if not reponse or not est_question_complétée(reponse):
                questions_non_completees.append(question)
        
        dict_resultats[individu.pk] = questions_non_completees

    return dict_resultats


def Get_questions_manquantes_famille(famille):
    """
    Retourne un dict avec, pour chaque individu de la famille,
    la liste des questions individu non répondues.
    """
    if not famille:
        return {}

    result = {}

    rattachements = Rattachement.objects.select_related('individu').filter(
        famille=famille,
        individu__deces=False
    )

    for rattachement in rattachements:
        individu = rattachement.individu

        questions_manquantes = Get_question_individu(individu)

        result[individu.pk] = {
            "individu": individu,
            "rattachement": rattachement,
            "questions": questions_manquantes,
            "nbre": len(questions_manquantes),
        }

    return result