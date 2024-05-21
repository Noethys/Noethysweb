# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, ButtonHolder, Div
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import Individu, Medecin
from core.widgets import Select_avec_commandes_form


class Form_choix_medecin(forms.ModelChoiceField):
    search_fields = ['nom__icontains', 'prenom__icontains', 'ville_resid__icontains']

    def label_from_instance(self, instance):
        return instance.Get_nom(afficher_ville=True)


class Formulaire(FormulaireBase, ModelForm):
    medecin = Form_choix_medecin(label="Médecin", queryset=Medecin.objects.all().order_by("nom", "prenom"), required=False, help_text="Cliquez sur le '+' si vous souhaitez ajouter un nouveau médecin qui n'existe pas dans la liste.",
                                     widget=Select_avec_commandes_form(attrs={"url_ajax": "ajax_ajouter_medecin", "id_form": "medecins_form", "afficher_bouton_ajouter": True,
                                                                              "textes": {"champ": "Nom du médecin", "ajouter": "Ajouter un médecin", "modifier": "Modifier un médecin"}}))

    class Meta:
        model = Individu
        fields = ["medecin"]

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'form_selection_medecin'

        individu = Individu.objects.get(pk=idindividu)
        self.fields["medecin"].initial = individu.medecin

        self.helper.layout = Layout(
            Field("medecin"),
            ButtonHolder(
                Div(
                    Submit('submit', 'Valider', css_class='btn-primary'),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"
                ),
            ),
        )
