# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Div, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Organisateur
from core.widgets import Telephone, CodePostal, Ville, Rue, Selection_image


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Organisateur
        fields = ['nom', 'rue', 'cp', 'ville', 'tel', 'fax', 'mail', 'site',
                  'num_agrement', 'num_siret', 'code_ape', 'logo']
        widgets = {
            'tel': Telephone(),
            'fax': Telephone(),
            'rue': Rue(attrs={"id_codepostal": "id_cp", "id_ville": "id_ville"}),
            'cp': CodePostal(attrs={"id_ville": "id_ville"}),
            'ville': Ville(attrs={"id_codepostal": "id_cp"}),
            'logo': Selection_image(),
        }
        help_texts = {
            "nom": "Saisissez le nom de l'organisateur. Exemples : Mairie de Lannilis, Association Les Petits Loups...",
            "rue": "Saisissez le numéro et le nom de la voie. Exemple : 12 rue des Lilas.",
            "cp": "Saisissez le code postal. La ville correspondante vous sera proposée automatiquement.",
            "ville": "Saisissez le nom de la ville.",
            "tel": "Saisissez le numéro de téléphone. Exemple : 02 98 12 34 56.",
            "fax": "Saisissez si besoin le numéro de fax.",
            "mail": "Saisissez l'adresse email. Exemple : contact@mairie.fr.",
            "site": "Saisissez l'adresse du site internet. Exemple : www.mairie.fr.",
            "num_agrement": "Saisissez si besoin le numéro d'agrément de l'organisateur.",
            "num_siret": "Saisissez le numéro SIRET de l'organisateur (14 chiffres).",
            "code_ape": "Saisissez le code APE (activité principale exercée). Exemples : 8411Z pour une commune, 9499Z pour une association.",
            "logo": "Sélectionnez le logo de l'organisateur. Il sera utilisé sur les documents et par défaut pour les activités.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'organisateur_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'parametrage_toc' %}", ajouter=False),
            Fieldset("Généralités",
                Field('nom'),
            ),
            Fieldset("Coordonnées",
                Field('rue'),
                Field('cp'),
                Field('ville'),
                Field('tel'),
                Field('fax'),
                Field('mail'),
                Field('site'),
            ),
            Fieldset("Numéros d'identification",
                Field('num_agrement'),
                Field('num_siret'),
                Field('code_ape'),
            ),
            Fieldset("Logo",
                Div(
                    Field('logo'),
                ),
            ),
            HTML("<br>"),
        )
