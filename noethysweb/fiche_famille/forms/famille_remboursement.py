# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, decimal
from django import forms
from django.forms import ModelForm
from django.db.models import Q, Sum
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field, PrependedText
from core.forms.select2 import Select2Widget
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Reglement, ModeReglement, Payeur, CompteBancaire, Prestation
from core.widgets import DatePickerWidget, Select_avec_commandes
from core.utils import utils_preferences
from fiche_famille.widgets import Selection_mode_reglement


class Formulaire(FormulaireBase, ModelForm):
    date = forms.DateField(label="Date", required=True, widget=DatePickerWidget())
    montant = forms.DecimalField(label="Montant", max_digits=6, decimal_places=2, initial=0.0, required=True, help_text="Saisissez le montant du remboursement.")
    observations = forms.CharField(label="Observations", widget=forms.Textarea(attrs={'rows': 2}), required=False, help_text="Vous pouvez saisir un commentaire qui sera stocké dans le règlement généré.")
    compte = forms.ModelChoiceField(label="Compte", widget=Select2Widget({"data-minimum-input-length": 0}), queryset=CompteBancaire.objects.none(), required=True)
    mode = forms.ModelChoiceField(label="Mode de règlement", queryset=ModeReglement.objects.all().order_by("label"), widget=Selection_mode_reglement(), required=True)
    payeur = forms.ModelChoiceField(label="Payeur", queryset=Payeur.objects.none(), widget=Select_avec_commandes(), required=True)

    class Meta:
        model = Reglement
        fields = ["famille", "date", "mode", "payeur", "observations", "montant", "compte"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_remboursement_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date
        self.fields["date"].initial = datetime.date.today()

        # Compte bancaire
        self.fields["compte"].queryset = CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")

        # Payeur
        self.fields['payeur'].queryset = Payeur.objects.filter(famille_id=idfamille).order_by("nom")
        self.fields['payeur'].widget.attrs.update({"donnees_extra": {"idfamille": idfamille}, "url_ajax": "ajax_modifier_payeur",
                                                   "textes": {"champ": "Nom du payeur", "ajouter": "Saisir un payeur", "modifier": "Modifier un payeur"}})

        # Compte bancaire par défaut
        try:
            compte = CompteBancaire.objects.get(defaut=True)
            if not self.instance.idreglement and compte:
                self.fields["compte"].initial = compte
        except:
            pass

        # Calcul du solde de la famille
        total_prestations = Prestation.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
        total_reglements = Reglement.objects.values('famille_id').filter(famille_id=idfamille).aggregate(total=Sum("montant"))
        total_du = total_prestations["total"] if total_prestations["total"] else decimal.Decimal(0)
        total_regle = total_reglements["total"] if total_reglements["total"] else decimal.Decimal(0)
        solde = total_du - total_regle
        if solde < 0:
            self.fields["montant"].initial = -solde

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}", ajouter=False),
            Hidden("famille", value=idfamille),
            Fieldset("Généralités",
                Field("date"),
                PrependedText("montant", utils_preferences.Get_symbole_monnaie()),
                Field("observations"),
            ),
            Fieldset("Options",
                Field("compte"),
                Field("mode"),
                Field("payeur"),
            ),
        )

    def clean(self):
        self.cleaned_data["montant"] = -self.cleaned_data["montant"]
        return self.cleaned_data
