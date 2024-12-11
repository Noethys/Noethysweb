# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden
from crispy_forms.bootstrap import Field
from core.utils import utils_questionnaires
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    nom = forms.CharField(label="Nom", required=False)

    liste_choix = [("aucun", "Aucune"), ("genre", "Genre (M/F)"), ("date_naiss", "Date de naissance"),
        ("ville_naissance", "Ville de naissance"), ("medecin_nom", "Nom du médecin"),
        ("tel_mobile", "Tél. mobile"), ("tel_domicile", "Tél. domicile"), ("mail", "Email"),
        ("noms_responsables", "Noms responsables"), ("noms_responsables_titulaires", "Noms responsables titulaires"), ("tel_responsables", "Tél. responsables"), ("mail_responsables", "Email responsables"),
        ("ville_residence", "Ville de résidence"), ("adresse_residence", "Adresse complète de résidence"),
        ("secteur", "Secteur géographique"), ("secteur_colore", "Secteur géographique coloré"), ("nom_ecole", "Ecole"), ("nom_classe", "Classe"),
        ("nom_niveau_scolaire", "Niveau scolaire"), ("famille", "Famille"), ("regime", "Régime social"),
        ("regimes_alimentaires", "Régimes alimentaires"),
        ("caisse", "Caisse d'allocations"), ("codebarres_individu", "Code-barres de l'individu")]

    # Intégration des questionnaires
    q = utils_questionnaires.Questionnaires()
    for public in ("famille", "individu"):
        for dictTemp in q.GetQuestions(public):
            label = "Question %s. : %s" % (public[:3], dictTemp["label"])
            code = "question_%s_%d" % (public, dictTemp["IDquestion"])
            liste_choix.append((code, label))

    donnee = forms.ChoiceField(label="Donnée associée", choices=liste_choix, initial="aucun", required=False)

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
