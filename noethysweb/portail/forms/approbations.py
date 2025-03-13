# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from portail.forms.fiche import FormulaireBase
from portail.widgets import ValidationApprobation
from portail.utils import utils_approbations
from core.models import Rattachement


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        self.famille = kwargs.pop('instance', None)
        kwargs.pop('famille', None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_approbations_form'
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False
        self.helper.form_tag = False
        self.helper.layout = Layout()

        familles = []
        # Gérer le cas où l'utilisateur fait directement partie d'une famille
        if hasattr(self.request.user, 'famille'):
            familles.append(self.request.user.famille)
        # Gérer le cas où l'utilisateur est un individu et lié via Rattachement
        elif hasattr(self.request.user, 'individu'):
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            # Ajoutez chaque famille liée à la liste
            for rattachement in rattachements:
                if rattachement.famille and rattachement.titulaire == 1:
                    familles.append(rattachement.famille)

        # Vérifier si des familles existent avant de procéder
        if familles:
            for famille in familles:
                approbations_requises = utils_approbations.Get_approbations_requises(famille=famille)

                # Consentements pour chaque famille
                for unite_consentement in approbations_requises["consentements"]:
                    ctrl = forms.BooleanField(widget=ValidationApprobation(attrs={"unite_consentement": unite_consentement}), required=False)
                    code = "unite_%d_famille_%d" % (unite_consentement.pk, famille.pk)
                    self.fields[code] = ctrl
                    self.helper.layout.append(Field(code))

                # Certifications des fiches individuelles pour chaque famille
                for rattachement in approbations_requises["rattachements"]:
                    ctrl = forms.BooleanField(widget=ValidationApprobation(attrs={"rattachement": rattachement}), required=False)
                    code = "rattachement_%d_famille_%d" % (rattachement.pk, famille.pk)
                    self.fields[code] = ctrl
                    self.helper.layout.append(Field(code))

                # Certification de la fiche famille pour chaque famille
                for famille_cert in approbations_requises["familles"]:
                    ctrl = forms.BooleanField(widget=ValidationApprobation(attrs={"famille": famille_cert}), required=False)
                    code = "famille_%d" % famille_cert.pk
                    self.fields[code] = ctrl
                    self.helper.layout.append(Field(code))

            # Création des contrôles de validation
            if not self.fields:
                self.helper.layout.append(HTML("<strong>Aucune approbation n'est actuellement nécessaire.</strong>"))

