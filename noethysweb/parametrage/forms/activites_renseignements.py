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
from core.models import Activite, TypePiece, TypeCotisation, TypeConsentement
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Activite
        fields = ["pieces", "cotisations", "vaccins_obligatoires", "assurance_obligatoire", "types_consentements"]
        widgets = {
            "pieces": Select2MultipleWidget(),
            "cotisations": Select2MultipleWidget(),
            "types_consentements": Select2MultipleWidget(),
         }
        help_texts = {
            "pieces": "Sélectionnez dans la liste les types de pièces qui doivent être à jour. Exemples : Fiche d'inscription, Fiche sanitaire, Photocopie des vaccinations... Il est possible de créer de nouveaux types de pièces dans le menu Paramétrage > Types de pièces.",
            "cotisations": "Sélectionnez dans la liste des types d'adhésions qui doivent être à jour. L'individu devra avoir à jour l'un de ces types d'adhésions. Il est possible de créer de nouveaux types d'adhésions dans le menu Paramétrage > Types d'adhésions.",
            "types_consentements": "Sélectionnez dans la liste les types de consentements internet nécessaires. Il peut s'agir par exemple du règlement intérieur de l'activité : L'usager devra alors approuver ce règlement intérieur avant de pouvoir accéder aux réservations sur le portail famille. Il est possible de créer de nouveaux types de consentements dans le menu Paramétrage > Types de consentements.",
            "vaccins_obligatoires": "Cochez cette case si vous souhaitez que l'application affiche si les vaccinations obligatoires sont à jour ou non. Sur le portail famille, les familles sont ainsi incitées à les renseigner.",
            "assurance_obligatoire": "Cochez cette case si vous souhaitez que l'application affiche si les assurances sont à jour ou non. Sur le portail famille, les familles sont ainsi incitées à les renseigner.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_renseignements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="activites_renseignements_modifier", modifier_args="idactivite=activite.idactivite", modifier=True, enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'activites_renseignements' idactivite=activite.idactivite %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Fieldset("Pièces à fournir",
                Field("pieces"),
            ),
            Fieldset("Adhésions à jour",
                Field("cotisations"),
            ),
            Fieldset("Consentements internet nécessaires",
                Field("types_consentements"),
            ),
            Fieldset("Vaccinations",
                Field("vaccins_obligatoires"),
            ),
            Fieldset("Assurances",
                Field("assurance_obligatoire"),
            ),
        )
