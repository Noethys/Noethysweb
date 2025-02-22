# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.contrib import messages
from django.db.models import Max
from django.conf import settings
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML, Hidden
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget, Select2Widget
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget, DateRangePickerWidget, Select_avec_commandes, SelectionActivitesWidget
from core.models import LotFactures, PrefixeFacture, Facture, Famille
from core.forms.base import FormulaireBase
from core.utils import utils_parametres
from facturation.widgets import ChampAutomatiqueWidget


def Calc_prochain_numero(prefixe=None):
    mode_prochain_numero = getattr(settings, "PROCHAIN_NUMERO_FACTURES", "MAX")
    if mode_prochain_numero == "MAX":
        # Mode "MAX"
        numero = (Facture.objects.filter(prefixe=prefixe).aggregate(Max('numero')))['numero__max']
    else:
        # Mode "DERNIER"
        numero = Facture.objects.filter(prefixe=prefixe).last()
        numero = numero.numero if numero else None
    if not numero: numero = 0
    return numero + 1


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(), help_text="Sélectionnez la période de facturation souhaitée.")
    lot_factures = forms.ModelChoiceField(label="Lot de factures", queryset=LotFactures.objects.all().order_by("-pk"), required=False, widget=Select_avec_commandes({
            "donnees_extra": {}, "url_ajax": "ajax_modifier_lot_factures",
            "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot de factures", "modifier": "Modifier un lot de factures"}}), help_text="Il est possible d'associer aux factures que vous allez générer un lot de factures. Il s'agit d'un nom qui vous permettra de retrouver plus facilement un ensemble de factures. Exemples : Juillet 2024, Activités adultes - Août 2025...")
    prefixe = forms.ModelChoiceField(label="Préfixe de numéro", queryset=PrefixeFacture.objects.all(), required=False, help_text="Les préfixes ne sont généralement utilisés que par des structures avec de nombreuses activités. Le préfixe alphanumérique, préalablement créé dans le menu Paramétrage, sera ajouté devant chaque numéro de facture pour identifier par exemple des services ou des familles d'activités. Exemples : ALSH, ADOS, LOC...")
    prochain_numero = forms.CharField(label="Prochain numéro", required=True, widget=ChampAutomatiqueWidget({"label_checkbox": "Automatique", "title": "Attribuez ici le prochain numéro de facture. Les factures suivantes seront incrémentées automatiquement.", "type": "number"}), help_text="Le numéro de facture est incrémenté automatiquement. Mais vous pouvez le modifier manuellement si besoin.")
    date_emission = forms.DateField(label="Date d'émission", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}), help_text="La date d'émission est par défaut la date du jour. Il n'est généralement pas nécessaire de la modifier.")
    date_echeance = forms.DateField(label="Date d'échéance", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': True}), help_text="Vous pouvez si vous le souhaitez renseigner une date d'échéance pour le paiement. Elle apparaîtra sur la facture PDF.")
    choix_categories = [("consommation", "Consommations"), ("cotisation", "Adhésions"), ("location", "Locations"), ("autre", "Autres"), ]
    categories = forms.MultipleChoiceField(label="Catégories de prestations", widget=Select2MultipleWidget(), choices=choix_categories, required=True)
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget(), help_text="Cochez les activités ou les groupes d'activités à inclure dans les factures.")
    prestations_anterieures = forms.DateField(label="Prestations antérieures", required=False, widget=DatePickerWidget({"afficher_check": True, "label_checkbox": "Inclure les prestations antérieures non facturées depuis le"}), help_text="Il est possible d'intégrer dans les factures des prestations non facturées antérieures à la période sélectionnée. Cela est notamment utile pour les collectivités qui ne facturent pas les petits montants et attendent qu'ils se cumulent avant de les facturer. Saisissez la date à partir de laquelle il est possible de rechercher ces anciennes prestations.")
    inclure_cotisations_si_conso = forms.BooleanField(label="Inclure les adhésions uniquement pour les familles qui sont sur les activités cochées", required=False, initial=False)
    choix_selection_familles = [("TOUTES", "Toutes les familles"), ("FAMILLE", "Uniquement la famille sélectionnée")]
    selection_familles = forms.TypedChoiceField(label="Sélection des familles", choices=choix_selection_familles, initial="TOUTES", required=False, help_text="Par défaut, les factures de toutes les familles concernées seront générées, mais vous pouvez générer uniquement la facture d'une seule famille.")
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget(), queryset=Famille.objects.all().order_by("nom"), required=False, help_text="Sélectionnez la famille pour laquelle vous souhaitez générer une facture dans la liste proposée.")
    date_limite_paiement = forms.DateField(label="Date limite paiement en ligne", required=False, widget=DatePickerWidget({"afficher_check": True, "label_checkbox": "Interdire le paiement en ligne après le"}), help_text="Vous pouvez saisir une date à partir de laquelle il deviendra impossible de régler cette facture via le paiement en ligne sur le portail.")
    observations = forms.CharField(label="Observations", required=False, help_text="Vous pouvez ajouter un commentaire qui sera mémorisé dans la facture uniquement pour un usage interne par défaut.", widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        idfamille = kwargs.pop('idfamille', None)
        super(Formulaire, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'form_factures_generation'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Prochain numéro
        self.fields["prochain_numero"].initial = Calc_prochain_numero()

        # Date d'émission
        self.fields["date_emission"].initial = datetime.date.today()

        # Catégories
        self.fields["categories"].initial = ["consommation", "cotisation", "location", "autre"]

        # Prestations antérieures
        self.fields["prestations_anterieures"].initial = utils_parametres.Get(nom="prestations_anterieures", categorie="generation_factures", utilisateur=self.request.user, valeur=None)

        # Sélection famille
        if idfamille:
            self.fields["selection_familles"].initial = "FAMILLE"
            self.fields["famille"].initial = idfamille

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'facturation_toc' %}", enregistrer_label="<i class='fa fa-search margin-r-5'></i>Rechercher des factures à générer", ajouter=False),
            Hidden('liste_factures_json', value=""),
            Hidden('montant_minimum', value=""),
            Fieldset('Généralités',
                Field('periode'),
                Field('lot_factures'),
                Field('prefixe'),
                Field('prochain_numero'),
                Field('date_emission'),
                Field('date_echeance'),
                Field('observations'),
            ),
            Fieldset('Activités',
                Field('activites'),
            ),
            Fieldset('Options',
                Field('categories'),
                Field('inclure_cotisations_si_conso'),
                Field('prestations_anterieures'),
                Field('date_limite_paiement'),
                Field('selection_familles'),
                Field('famille'),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Sélection des familles
        if self.cleaned_data["selection_familles"] == "FAMILLE" and not self.cleaned_data["famille"]:
            self.add_error('famille', "Vous devez sélectionner une famille dans la liste")
            return

        # Avertissements
        if not self.cleaned_data["lot_factures"]:
            messages.add_message(self.request, messages.INFO, "Remarque : Vous n'avez pas sélectionné de lot de factures")
        if not self.cleaned_data["date_echeance"]:
            messages.add_message(self.request, messages.INFO, "Remarque : Vous n'avez pas sélectionné de date d'échéance")

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// validite_type
function On_change_selection_familles() {
    $('#div_id_famille').hide();
    if($(this).val() == 'FAMILLE') {$('#div_id_famille').show()};
}
$(document).ready(function() {
    $('#id_selection_familles').change(On_change_selection_familles);
    On_change_selection_familles.call($('#id_selection_familles').get(0));
});

</script>
"""