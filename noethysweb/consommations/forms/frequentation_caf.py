# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import Parametre
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, Profil_configuration

CATEGORIE_PROFIL = "profil_frequentation_caf"


def Get_periode_defaut():
    """ Année civile précédente (période de la déclaration annuelle à la CAF) """
    annee = datetime.date.today().year - 1
    return "%s;%s" % (datetime.date(annee, 1, 1), datetime.date(annee, 12, 31))


def Get_profils(request=None, categorie=CATEGORIE_PROFIL):
    """ Profils accessibles : ceux de l'utilisateur, de ses structures ou communs """
    conditions = Q(categorie=categorie) & (Q(utilisateur=request.user) | Q(utilisateur__isnull=True))
    conditions &= (Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True))
    return Parametre.objects.filter(conditions).order_by("nom")


class Form_selection(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(attrs={"afficher_periodes_predefinies": False, "auto_application": True}))
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))

    def __init__(self, *args, **kwargs):
        super(Form_selection, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_frequentation_caf_selection"
        self.helper.form_method = "post"
        self.helper.form_tag = True
        self.fields["periode"].initial = Get_periode_defaut()
        self.helper.layout = Layout(
            Field("periode"),
            Field("activites"),
        )


class Form_profil(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil", queryset=Parametre.objects.none(), required=False,
                                    widget=Profil_configuration({"categorie": CATEGORIE_PROFIL, "module": "consommations.views.frequentation_caf"}))

    def __init__(self, *args, **kwargs):
        super(Form_profil, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_frequentation_caf_profil"
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.fields["profil"].widget.request = self.request
        self.fields["profil"].queryset = Get_profils(self.request)
        self.fields["profil"].empty_label = "- Aucun profil -"
        self.helper.layout = Layout(Field("profil"))
