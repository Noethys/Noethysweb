# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div, HTML
from crispy_forms.bootstrap import Field
from core.models import TypeCotisation, Cotisation, Activite
from core.utils.utils_commandes import Commandes


class Formulaire(FormulaireBase, ModelForm):
    # Modification du label de la checkbox
    carte = forms.BooleanField(label="Est représentée par une carte adhérent.", required=False, help_text="Cochez cette case si cette adhésion donne lieu à la remise d'une carte d'adhérent.")

    class Meta:
        model = TypeCotisation
        fields = "__all__"
        help_texts = {
            "nom": "Saisissez le nom du type d'adhésion. Exemples : Adhésion annuelle, Carte famille, Licence sportive...",
            "type": "Indiquez si l'adhésion est souscrite pour toute la famille ou pour un individu.",
            "code_comptable": "Saisissez si besoin le code comptable, pour les exports comptables.",
            "code_analytique": "Saisissez si besoin le code analytique, pour les exports comptables.",
            "code_produit_local": "Cette option n'est utilisée que par les structures publiques pour des exports vers des logiciels de comptabilité publique.",
            "defaut": "Cochez cette case pour que ce type d'adhésion soit proposé par défaut lors de la saisie d'une adhésion.",
            "activite": "Sélectionnez si besoin l'activité à laquelle seront rattachées les prestations de cette adhésion. Utile notamment pour les exports comptables par activité.",
            "structure": "Sélectionnez la structure associée à ce type d'adhésion. Laissez 'Toutes les structures' pour que ce type d'adhésion soit disponible dans toutes les structures.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'types_cotisations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Type
        if self.instance and Cotisation.objects.filter(type_cotisation_id=self.instance.pk):
            self.fields["type"].disabled = True

        # Activités associées
        activites_associees = []
        if self.instance.pk:
            activites_associees = [activite.nom for activite in Activite.objects.filter(cotisations=self.instance)]

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme type d'adhésion par défaut"
        if len(TypeCotisation.objects.all()) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_cotisations_liste' %}"),
            Fieldset('Généralités',
                Field('nom'),
                Field('type'),
                Field('carte'),
                Field('defaut'),
            ),
            Fieldset('Options',
                Field('activite'),
                Field('code_comptable'),
                Field('code_analytique'),
                Field("code_produit_local"),
            ),
            Fieldset('Structure associée',
                Field('structure'),
            ),
            Fieldset("Activités pour lesquelles ce type d'adhésion est obligatoire",
                Div(
                    HTML("""
                    <span>%s</span>
                    """ % (", ".join(activites_associees) if activites_associees else "Aucune activité")),
                    css_class="alert alert-light text-center"
                ),
            ),
        )

