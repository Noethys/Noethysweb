# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Perception
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Perception
        fields = "__all__"
        help_texts = {
            "nom": "Nom de la perception. Exemple : Perception de Brest.",
            "service": "Identité du destinataire ou du service. Exemple : Service comptabilité.",
            "rue_resid": "Libellé de la voie sans le numéro. Exemple : Rue des alouettes.",
            "numero": "Numéro de la voie. Exemple : 14.",
            "batiment": "Nom de l'immeuble, du bâtiment ou de la résidence, etc... Exemple : Résidence les acacias.",
            "etage": "Numéro de l'étage, de l'annexe, etc... Exemple : Etage 4.",
            "boite": "Boîte postale, tri service arrivée, etc... Exemple : BP64.",
            "cp_resid": "Code postal. Exemple : 29200.",
            "ville_resid": "Nom de la ville. Exemple : BREST.",
            "pays": "Code du pays. Exemple : FR.",
        }
        
    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "perceptions_form"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'perceptions_liste' %}"),
            Fieldset("Identification",
                Field("nom"),
            ),
            Fieldset("Adresse postale",
                Field("service"),
                Field("numero"),
                Field("rue_resid"),
                Field("batiment"),
                Field("etage"),
                Field("boite"),
                Field("cp_resid"),
                Field("ville_resid"),
                Field("pays"),
            ),
        )
