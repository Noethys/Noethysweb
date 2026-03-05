# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
import json
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column, Fieldset
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import HelloAssoConfig, Activite, StripeCompte
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget
from django.core.exceptions import ValidationError

# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field, HTML
from core.utils.utils_commandes import Commandes
from core.models import Activite, StripeCompte
from core.forms.select2 import Select2MultipleWidget
from django.core.exceptions import ValidationError


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = StripeCompte
        # On utilise directement les champs du modèle StripeCompte
        fields = ["nom", "secret_key", "publishable_key", "webhook_secret", "actif", "activites"]
        widgets = {
            "activites": Select2MultipleWidget(),
        }

    def __init__(self, *args, **kwargs):
        # On pop l'idconfig passé par la vue CRUD de Noethys
        self.idconfig = kwargs.pop("idconfig", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'config_stripe_form'
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'

        # Filtrage des activités selon les structures de l'utilisateur
        self.fields["activites"].queryset = Activite.objects.filter(
            structure__in=self.request.user.structures.all(),
            actif = True
        )

        # Layout simplifié uniquement pour Stripe
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'config_paiement_stripe_liste' %}"),

            Fieldset("Configuration du compte Stripe",
                     Field('nom', placeholder="Ex: Compte Section Basket"),
                     Field('actif'),
                     Field('activites'),
                     HTML(
                         "<p class='help-block small'>Sélectionnez les activités qui utiliseront ce compte Stripe.</p>"),
                     ),

            Fieldset("Clés API (Dashboard Stripe)",
                     Field('secret_key', placeholder="sk_live_..."),
                     Field('publishable_key', placeholder="pk_live_..."),
                     Field('webhook_secret', placeholder="whsec_..."),
                     ),
        )

    def clean(self):
        cleaned_data = super().clean()
        actif = cleaned_data.get("actif")
        activites = cleaned_data.get("activites")

        # Si la configuration n'est pas active, on ne vérifie aucun conflit
        if not actif:
            return cleaned_data

        if not activites:
            return cleaned_data

        # --- 1. Conflit avec les configurations HELLOASSO ---
        from core.models import HelloAssoConfig
        # On ne cherche que les configs HelloAsso qui sont ACTIVES (en excluant l'instance actuelle si c'est le form HA)
        qs_ha = HelloAssoConfig.objects.filter(actif=True)
        if hasattr(self.instance, 'client_id'):  # Si on est dans le formulaire HelloAsso
            qs_ha = qs_ha.exclude(pk=self.instance.pk)

        conflits_ha = qs_ha.filter(activites__in=activites).distinct()
        if conflits_ha.exists():
            noms = ", ".join([a.nom for a in activites.filter(helloasso_configs__in=conflits_ha)])
            raise ValidationError(f"Conflit : Ces activités ont déjà un HelloAsso ACTIF : {noms}")

        # --- 2. Conflit avec les comptes STRIPE ---
        from core.models import StripeCompte
        # On ne cherche que les comptes Stripe qui sont ACTIFS (en excluant l'instance actuelle si c'est le form Stripe)
        qs_stripe = StripeCompte.objects.filter(actif=True)
        if hasattr(self.instance, 'secret_key'):  # Si on est dans le formulaire Stripe
            qs_stripe = qs_stripe.exclude(pk=self.instance.pk)

        conflits_stripe = qs_stripe.filter(activites__in=activites).distinct()
        if conflits_stripe.exists():
            noms = ", ".join([a.nom for a in activites.filter(stripe_comptes__in=conflits_stripe)])
            raise ValidationError(f"Conflit : Ces activités ont déjà un compte Stripe ACTIF : {noms}")

        return cleaned_data