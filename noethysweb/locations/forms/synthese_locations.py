# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget
from core.utils import utils_questionnaires
from core.models import CategorieProduit
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    categories_produits = forms.ModelMultipleChoiceField(label="Catégories de produits", required=True, widget=Select2MultipleWidget({"data-minimum-input-length": 0}),
                                             queryset=CategorieProduit.objects.all(), initial=CategorieProduit.objects.all())
    donnees = forms.ChoiceField(label="Données", choices=[("quantite", "Quantité"), ("duree", "Durée")], initial="quantite", required=False)

    choix_regroupement = [
        ("jour", "Jour"), ("mois", "Mois"), ("annee", "Année"), ("categorie", "Catégorie de produits"), ("ville_residence", "Ville de résidence"),
        ("secteur", "Secteur géographique"), ("famille", "Famille"), ("regime", "Régime social"), ("caisse", "Caisse d'allocations"),
    ]
    q = utils_questionnaires.Questionnaires()
    for public in ("famille",):
        for dictTemp in q.GetQuestions(public):
            label = "Question %s. : %s" % (public[:3], dictTemp["label"])
            code = "question_%s_%d" % (public, dictTemp["IDquestion"])
            choix_regroupement.append((code, label))
    regroupement = forms.ChoiceField(label="Regroupement", widget=Select2Widget(), choices=choix_regroupement, initial="jour", required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Field("periode"),
            Field("categories_produits"),
            Field("donnees"),
            Field("regroupement"),
        )
