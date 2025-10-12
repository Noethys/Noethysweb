# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import CompteBancaire


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = CompteBancaire
        fields = ["nom", "numero", "defaut", "raison", "code_etab", "code_guichet",
                  "cle_rib", "cle_iban", "iban", "bic", "code_ics", "dft_titulaire",
                  "dft_iban", "structure", "adresse_service", "adresse_rue", "adresse_numero",
                  "adresse_batiment", "adresse_etage", "adresse_boite", "adresse_cp",
                  "adresse_ville", "adresse_pays"]
        labels = {
            "numero" : "Numéro de compte",
        }
        help_texts = {
            "code_ics": "Le Identifiant Créancier SEPA qui vous a été communiqué par votre banque ou votre trésorerie. Exemple : FR12Z99123456.",
            "raison": "Nom du créancier. Exemple : Ville de Brest.",
            "adresse_service": "Identité du destinataire ou du service. Exemple : Service comptabilité.",
            "adresse_rue": "Libellé de la voie sans le numéro. Exemple : Rue des alouettes.",
            "adresse_numero": "Numéro de la voie. Exemple : 14.",
            "adresse_batiment": "Nom de l'immeuble, du bâtiment ou de la résidence, etc... Exemple : Résidence les acacias.",
            "adresse_etage": "Numéro de l'étage, de l'annexe, etc... Exemple : Etage 4.",
            "adresse_boite": "Boîte postale, tri service arrivée, etc... Exemple : BP64.",
            "adresse_cp": "Code postal. Exemple : 29200.",
            "adresse_ville": "Nom de la ville. Exemple : BREST.",
            "adresse_pays": "Code du pays. Exemple : FR.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "comptes_bancaires_form"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Définir comme valeur par défaut
        self.fields["defaut"].label = "Définir comme compte par défaut"
        if len(CompteBancaire.objects.all()) == 0 or self.instance.defaut == True:
            self.fields["defaut"].initial = True
            self.fields["defaut"].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'comptes_bancaires_liste' %}"),
            Fieldset("Généralités",
                Field("nom"),
                Field("defaut"),
            ),
            Fieldset("Coordonnées bancaires",
                Field("numero"),
                Field("code_etab"),
                Field("code_guichet"),
                Field("cle_rib"),
                Field("cle_iban"),
                Field("iban"),
                Field("bic"),
            ),
            Fieldset("Identification du créancier pour les prélèvements",
                Field("code_ics"),
                Field("raison"),
                Field("adresse_service"),
                Field("adresse_numero"),
                Field("adresse_rue"),
                Field("adresse_batiment"),
                Field("adresse_etage"),
                Field("adresse_boite"),
                Field("adresse_cp"),
                Field("adresse_ville"),
                Field("adresse_pays"),
                Field("dft_titulaire"),
                Field("dft_iban"),
            ),
            Fieldset("Structure associée",
                Field("structure"),
            ),
        )
