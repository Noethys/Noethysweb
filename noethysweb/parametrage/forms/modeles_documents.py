# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column, Fieldset, Hidden, Div
from crispy_forms.bootstrap import Field, FormActions, PrependedText
from core.utils.utils_commandes import Commandes
from core.models import ModeleDocument
from core.forms.select2 import Select2Widget


class Formulaire(FormulaireBase, ModelForm):
    champs = forms.ModelChoiceField(label="Champs", widget=Select2Widget(), queryset=ModeleDocument.objects.all(), required=False)
    objets = forms.CharField(required=False)

    class Meta:
        model = ModeleDocument
        fields = "__all__"
        widgets = {
            'observations': forms.Textarea(attrs={'rows': 1}),
        }

    def __init__(self, *args, **kwargs):
        nom = kwargs.pop("nom", "")
        categorie = kwargs.pop("categorie", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_documents_form'
        self.helper.form_method = 'post'
        # self.helper.form_show_labels = False

        # Masquage des labels
        self.fields["nom"].label = False
        self.fields["largeur"].label = False
        self.fields["hauteur"].label = False
        self.fields["fond"].label = False
        self.fields["structure"].label = False

        # Liste des fonds disponibles
        self.fields["fond"].choices = [(None, "Aucun calque de fond")] + [(modele.pk, modele.nom) for modele in ModeleDocument.objects.filter(categorie="fond")]

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme modèle par défaut"
        if len(ModeleDocument.objects.filter(categorie=categorie)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Création ou modification
        if not self.instance.idmodele:
            self.fields["nom"].initial = nom
            self.fields["largeur"].initial = 210
            self.fields["hauteur"].initial = 297
        else:
            categorie = self.instance.categorie

        # Affichage
        self.helper.layout = Layout(
            Hidden('categorie', value=categorie),
            PrependedText('nom', 'Nom'),
            PrependedText('largeur', 'Largeur (mm)'),
            PrependedText('hauteur', 'Hauteur (mm)'),
            # PrependedText('observations', 'Notes'),
            PrependedText('fond', "Fond"),
            PrependedText('structure', "Structure"),
            Field('defaut'),
            Field('objets', type="hidden"),
            ButtonHolder(
                HTML("""<button type="submit" class='btn btn-primary btn-sm' name="dupliquer"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """),
                HTML("""<a type="button" class="btn btn-danger btn-sm" href="{{ view.get_success_url }}"><i class="fa fa-ban margin-r-5"></i>Annuler</a>"""),
                css_class="pull-right"
            ),
        )



class Formulaire_creation(FormulaireBase, ModelForm):

    class Meta:
        model = ModeleDocument
        fields = ["nom", "categorie", "structure"]

    def __init__(self, *args, **kwargs):
        nom = kwargs.pop("nom", "")
        categorie = kwargs.pop("categorie")
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Commandes(ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset('Généralités',
                Field('nom'),
            ),
            Fieldset('Structure associée',
                Field('structure'),
            ),
            Hidden('categorie', value=categorie),
        )


class Formulaire_champs(forms.Form):
    champs = forms.ChoiceField(label="Sélectionnez le champ à insérer", widget=Select2Widget({"lang": "fr", "data-width": "100%"}), choices=[(1, "item 1"), (2, "item 2")], required=True)

    def __init__(self, *args, **kwargs):
        # categorie = kwargs.pop("categorie")
        champs = kwargs.pop("champs")
        super(Formulaire_champs, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'modeles_documents_champs'

        # Remplissage de la liste des champs disponibles
        self.fields["champs"].choices = [(code, "%s - %s" % (label, code)) for (label, exemple, code) in champs]

        self.helper.layout = Layout(
            Field("champs"),
            ButtonHolder(
                Div(
                    Submit('submit', 'Insérer', css_class='btn-primary'),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"
                ),
            ),
        )
