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
from core.widgets import Telephone, CodePostal, Ville, Rue
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
            'rue_resid': Rue(attrs={"id_codepostal": "id_cp_resid", "id_ville": "id_ville_resid"}),
            'cp_resid': CodePostal(attrs={"id_ville": "id_ville_resid"}),
            'ville_resid': Ville(attrs={"id_codepostal": "id_cp_resid"}),
        }
        help_texts = {
            "rue_resid": "Saisissez le numéro et le nom de la voie, avec si besoin un complément d'adresse. Exemple : 12 rue des Acacias.",
            "cp_resid": "Saisissez le code postal, patientez un instant puis sélectionnez la ville dans la liste proposée.",
            "ville_resid": "Saisissez le nom de la ville en majuscules. Il est rempli automatiquement si vous avez choisi la ville à partir du code postal.",
            "tel_domicile": "Saisissez le numéro de téléphone fixe au format 01.23.45.67.89.",
            "tel_mobile": "Saisissez le numéro de portable au format 06.12.34.56.78. Il est utilisé pour l'envoi de SMS au collaborateur.",
            "mail": "Saisissez l'adresse email personnelle. Exemple : marie.dupont@exemple.fr. Elle est utilisée pour l'envoi d'emails au collaborateur.",
            "travail_tel": "Saisissez le numéro de téléphone professionnel (ligne directe ou poste) au format 01.23.45.67.89.",
            "travail_mail": "Saisissez l'adresse email professionnelle si le collaborateur en dispose.",
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
