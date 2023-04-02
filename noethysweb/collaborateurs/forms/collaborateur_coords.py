# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Collaborateur
from core.widgets import Telephone, CodePostal, Ville
from fiche_individu.widgets import CarteOSM


class Formulaire(FormulaireBase, ModelForm):
    carte = forms.ChoiceField(label="Localisation", widget=CarteOSM(), required=False)

    class Meta:
        model = Collaborateur
        fields = ["rue_resid", "cp_resid", "ville_resid", "tel_domicile", "tel_mobile", "mail", "travail_tel", "travail_mail"]
        widgets = {
            'tel_domicile': Telephone(),
            'tel_mobile': Telephone(),
            'travail_tel': Telephone(),
            'rue_resid': forms.Textarea(attrs={'rows': 2}),
            'cp_resid': CodePostal(attrs={"id_ville": "id_ville_resid"}),
            'ville_resid': Ville(attrs={"id_codepostal": "id_cp_resid"}),
        }
        help_texts = {
            "rue_resid": "Saisissez le numéro et le nom de la voie. Exemple : 12 Rue des acacias.",
            "cp_resid": "Saisissez le code postal de la ville de résidence, attendez une seconde et sélectionnez la ville dans la liste déroulante.",
            "ville_resid": "Saisissez le nom de la ville en majuscules.",
            "tel_domicile": "Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx.",
            "tel_mobile": "Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx.",
            "mail": "Saisissez une adresse Email valide.",
            "travail_tel": "Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx.",
            "travail_mail": "Saisissez une adresse Email valide.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'collaborateur_coords_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="collaborateur_coords_modifier", modifier_args="idcollaborateur=idcollaborateur", modifier=True, enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'collaborateur_coords' idcollaborateur=idcollaborateur %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Fieldset("Adresse de résidence",
                Field("rue_resid"),
                Field("cp_resid"),
                Field("ville_resid"),
                Field("carte"),
            ),
            Fieldset("Coordonnées personnelles",
                Field("tel_domicile"),
                Field("tel_mobile"),
                Field("mail"),
            ),
            Fieldset("Coordonnées professionnelles",
                Field("travail_tel"),
                Field("travail_mail"),
            ),
        )
