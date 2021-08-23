# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, InlineRadios
from core.utils.utils_commandes import Commandes
from core.models import ContactUrgence
from core.widgets import Telephone, CodePostal, Ville
from fiche_individu.widgets import CarteOSM


class Formulaire(FormulaireBase, ModelForm):
    carte = forms.ChoiceField(label="Localisation", widget=CarteOSM(), required=False)

    class Meta:
        model = ContactUrgence
        fields = "__all__"
        widgets = {
            'tel_domicile': Telephone(),
            'tel_mobile': Telephone(),
            'tel_travail': Telephone(),
            'rue_resid': forms.Textarea(attrs={'rows': 2}),
            'cp_resid': CodePostal(attrs={"id_ville": "id_ville_resid"}),
            'ville_resid': Ville(attrs={"id_codepostal": "id_cp_resid"}),
            'observations': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille", None)
        if kwargs.get("instance", None):
            self.idfamille = kwargs["instance"].famille_id
        self.idindividu = kwargs.pop("idindividu", None)
        if kwargs.get("instance", None):
            self.idindividu = kwargs["instance"].individu_id
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_contacts_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Bouton Annuler
        if self.mode == "fiche_individu":
            annuler_url = "{% url 'individu_contacts_liste' idfamille=idfamille idindividu=idindividu %}"
        else:
            annuler_url = "{% url 'contacts_urgence_liste' %}"

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=self.idfamille),
            Hidden('individu', value=self.idindividu),
            Commandes(annuler_url=annuler_url),
            Fieldset("Identité",
                Field("nom"),
                Field("prenom"),
                Field("lien"),
            ),
            Fieldset("Adresse de résidence",
                Div(
                    Field("rue_resid"),
                    Field("cp_resid"),
                    Field("ville_resid"),
                ),
                Field("carte"),
            ),
            Fieldset("Coordonnées",
                Field("tel_domicile"),
                Field("tel_mobile"),
                Field("tel_travail"),
                Field("mail"),
            ),
            Fieldset("Autorisations",
                Field("autorisation_sortie"),
                Field("autorisation_appel"),
            ),
            Fieldset("Divers",
                Field("observations"),
            ),
        )
