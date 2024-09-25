# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget
from core.utils import utils_questionnaires
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.models import Caisse


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))

    choix_regroupement = [
        ("jour", "Jour"), ("mois", "Mois"), ("annee", "Année"), ("ville_residence", "Ville de résidence"), ("secteur", "Secteur géographique"),
        ("famille", "Famille"), ("individu", "Individu"), ("regime", "Régime social"), ("caisse", "Caisse d'allocations"),
        ("montant_deduction", "Montant de la déduction"), ("nom_deduction", "Label de la déduction"), ("nom_aide", "Label de l'aide"),
    ]
    q = utils_questionnaires.Questionnaires()
    for public in ("famille",):
        for dictTemp in q.GetQuestions(public):
            label = "Question %s. : %s" % (public[:3], dictTemp["label"])
            code = "question_%s_%d" % (public, dictTemp["IDquestion"])
            choix_regroupement.append((code, label))
    regroupement = forms.ChoiceField(label="Regroupement", widget=Select2Widget(), choices=choix_regroupement, initial="individu", required=True)

    caisses = forms.ModelMultipleChoiceField(label="Caisses", required=False, widget=Select2MultipleWidget({"data-minimum-input-length": 0}), queryset=Caisse.objects.all())

    inclure_sans_activite = forms.BooleanField(label="Inclure les déductions non associées à une activité", required=False, initial=True)
    inclure_sans_caisse = forms.BooleanField(label="Inclure les déductions non associées à une caisse", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = "post"

        # Caisses
        self.fields["caisses"].initial = [caisse.pk for caisse in Caisse.objects.all()]

        self.helper.layout = Layout(
            Field("periode"),
            Field("regroupement"),
            Field("activites"),
            Field("inclure_sans_activite"),
            Field("caisses"),
            Field("inclure_sans_caisse"),
        )
