# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.utils import utils_questionnaires
from core.forms.base import FormulaireBase


LISTE_CHOIX = [
    ("aucun", "Aucune", 50),
    ("date_debut", "Date de début", 50),
    ("date_fin", "Date de fin", 50),
    ("groupe", "Groupe", 70),
    ("categorie_tarif", "Catégorie de tarif", 70),
    ("nom", "Nom de l'individu", 70),
    ("prenom", "Prénom de l'individu", 70),
    ("date_naiss", "Date de naissance", 60),
    ("age", "Age", 20),
    ("mail", "Email", 50),
    ("portable", "Tél. mobile", 50),
    ("individu_ville", "Ville de résidence", 70),
    ("tel_parents", "Tél parents", 50),
    ("tel_contacts", "Tél contacts d'urgence et de sortie", 50),
    ("famille", "Nom de la famille", 70),
    ("mail_parents", "Mail parents", 70),
    ("famille_ville", "Ville de la famille", 70),
    ("num_cotisation", "Numéro d'adhésion", 30),
    ("ecole", "Ecole", 50),
    ("classe", "Classe", 50),
    ("statut", "Statut de l'inscription", 50),
    ("solde", "Solde", 50),
]

class Formulaire(FormulaireBase, forms.Form):
    nom = forms.CharField(label="Nom", required=False)

    # Intégration des questionnaires
    liste_choix = copy.copy(LISTE_CHOIX)
    q = utils_questionnaires.Questionnaires()
    for public in ("famille", "individu"):
        for dictTemp in q.GetQuestions(public):
            label = "Question %s. : %s" % (public[:3], dictTemp["label"])
            code = "question_%s_%d" % (public, dictTemp["IDquestion"])
            liste_choix.append((code, label, 30))

    donnee = forms.ChoiceField(label="Donnée associée", choices=[(item[0], item[1]) for item in liste_choix], initial="aucun", required=False)

    liste_choix_largeur = [("automatique", "Automatique")] + [(str(x), "%d pixels" % x) for x in range(5, 205, 5)]
    largeur = forms.ChoiceField(label="Largeur de la colonne", choices=liste_choix_largeur, initial="automatique", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_colonne_personnalisee'
        self.helper.form_method = 'post'
        self.helper.form_tag = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-4'
        self.helper.field_class = 'col-md-8'

        # Affichage
        self.helper.layout = Layout(
            Field("nom"),
            Field("donnee"),
            Field("largeur"),
        )
