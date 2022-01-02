# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.forms.base import FormulaireBase
from core.widgets import DatePickerWidget, Telephone


class Formulaire(FormulaireBase, forms.Form):
    type_recherche = forms.ChoiceField(label="Type de recherche", widget=forms.RadioSelect, initial="TEXTE", required=False, choices=[("TEXTE", "Textuelle"), ("PHONETIQUE", "Phonétique")])
    nom = forms.CharField(label="Nom de famille", required=False)
    nom_jfille = forms.CharField(label="Nom de naissance", required=False)
    prenom = forms.CharField(label="Prénom", required=False)
    date_naiss = forms.DateField(label="Date", required=False, widget=DatePickerWidget())
    cp_naiss = forms.CharField(label="Code postal", required=False)
    ville_naiss = forms.CharField(label="Ville", required=False)
    rue_resid = forms.CharField(label="Rue", required=False)
    cp_resid = forms.CharField(label="Code postal", required=False)
    ville_resid = forms.CharField(label="Ville", required=False)
    tel_domicile = forms.CharField(label="Tél fixe", required=False)
    tel_mobile = forms.CharField(label="Tél portable", required=False)
    mail = forms.CharField(label="Email personnel", required=False)
    profession = forms.CharField(label="Profession", required=False)
    employeur = forms.CharField(label="Employeur", required=False)
    travail_tel = forms.CharField(label="Tél pro.", required=False)
    travail_mail = forms.CharField(label="Email pro.", required=False)

    class Meta:
        widgets = {
            'tel_domicile': Telephone(),
            'tel_mobile': Telephone(),
            'travail_tel': Telephone(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'recherche_avancee_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            ButtonHolder(
                StrictButton("<i class='fa fa-search margin-r-5'></i>Rechercher", title="Rechercher", name="rechercher", type="submit", css_class="btn-primary"),
                HTML("""<a class="btn btn-danger" href='{% url 'individus_toc' %}' title="Annuler"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """),
                css_class="mb-3",
            ),
            Fieldset("Paramètres de recherche",
                 Field("type_recherche"),
            ),
            Fieldset("Etat-civil",
                Field("nom"),
                Field("nom_jfille"),
                Field("prenom"),
            ),
            Fieldset("Naissance",
                Field("date_naiss"),
                Field("cp_naiss"),
                Field("ville_naiss"),
            ),
            Fieldset("Adresse",
                Field("rue_resid"),
                Field("cp_resid"),
                Field("ville_resid"),
             ),
            Fieldset("Coordonnées",
                Field("tel_domicile"),
                Field("tel_mobile"),
                Field("mail"),
            ),
            Fieldset("Activité professionnelle",
                Field("profession"),
                Field("employeur"),
                Field("travail_tel"),
                Field("travail_mail"),
            ),
        )
