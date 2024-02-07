# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import random
from django import forms
from django.db.models import Q
from core.widgets import DateMask
from core.models import Rattachement
from core.utils import utils_portail


def Generation_secquest(famille=None):
    code_question = None

    # Recherche si option activée
    parametres_portail = utils_portail.Get_dict_parametres()

    # Recherche d'une question possible
    if parametres_portail.get("connexion_question_perso", True):
        questions_possibles = []
        conditions = Q(famille=famille) & ((Q(categorie=1) & Q(titulaire=True)) | Q(categorie=2))
        for rattachement in Rattachement.objects.select_related("individu").filter(conditions):
            if rattachement.individu.date_naiss and rattachement.individu.prenom:
                questions_possibles.append("datenaiss_%d" % rattachement.pk)
        if questions_possibles:
            code_question = random.choice(questions_possibles)

    # Enregistrement de la question
    famille.internet_secquest = code_question
    famille.save()


def Generation_field_secquest(famille=None):
    champ, idrattachement = famille.internet_secquest.split("_")
    rattachement = Rattachement.objects.select_related("individu").get(pk=int(idrattachement))
    label = "Quelle est la date de naissance de %s ?" % rattachement.individu.prenom
    field = forms.CharField(label=label, required=True, widget=DateMask(attrs={"class": "form-control", "title": "Répondez à la question", "placeholder": "Répondez à la question"}))
    return field


def Check_secquest(famille=None, reponse=None):
    if famille.internet_secquest:
        champ, idrattachement = famille.internet_secquest.split("_")
        rattachement = Rattachement.objects.select_related("individu").get(pk=int(idrattachement))
        if not rattachement.individu.date_naiss.strftime("%d/%m/%Y") == reponse:
            return False
    return True
