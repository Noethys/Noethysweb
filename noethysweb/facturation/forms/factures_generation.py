# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, ButtonHolder, Hidden
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget, DateRangePickerWidget, Select_avec_commandes, SelectionActivitesWidget, CheckDateWidget
from facturation.widgets import ProchainNumeroWidget
from core.models import LotFactures, PrefixeFacture, Facture, Famille
from django_select2.forms import Select2MultipleWidget, Select2Widget
import datetime, json
from django.contrib import messages
from django.db.models import Max



class Formulaire(forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    lot_factures = forms.ModelChoiceField(label="Lot de factures", queryset=LotFactures.objects.all(), required=False, widget=Select_avec_commandes({
            "donnees_extra": {}, "url_ajax": "ajax_modifier_lot_factures",
            "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot de factures", "modifier": "Modifier un lot de factures"}}))
    prefixe = forms.ModelChoiceField(label="Préfixe de numéro", queryset=PrefixeFacture.objects.all(), required=False)
    prochain_numero = forms.CharField(label="Prochain numéro", required=True, widget=ProchainNumeroWidget({"label_checkbox": "Automatique"}))
    date_emission = forms.DateField(label="Date d'émission", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    date_echeance = forms.DateField(label="Date d'échéance", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    choix_categories = [("consommation", "Consommations"), ("cotisation", "Adhésions"), ("location", "Locations"), ("autre", "Autres"), ]
    categories = forms.MultipleChoiceField(label="Catégories de prestations", widget=Select2MultipleWidget({"lang":"fr"}), choices=choix_categories, required=True)
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget())
    # prestations_anterieures = forms.DateField(label="Prestations antérieures", required=False, widget=CheckDateWidget({"label_checkbox": "Inclure les prestations antérieures non facturées depuis le"}))
    prestations_anterieures = forms.DateField(label="Prestations antérieures", required=False, widget=DatePickerWidget({"afficher_check": True, "label_checkbox": "Inclure les prestations antérieures non facturées depuis le"}))
    choix_selection_familles = [("TOUTES", "Toutes les familles"), ("FAMILLE", "Uniquement la famille sélectionnée")]
    selection_familles = forms.TypedChoiceField(label="Sélection des familles", choices=choix_selection_familles, initial="TOUTES", required=False)
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget({"lang": "fr"}), queryset=Famille.objects.all().order_by("nom"), required=False)

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
        numero = (Facture.objects.filter(prefixe=None).aggregate(Max('numero')))['numero__max']
        if not numero: numero = 0
        self.fields["prochain_numero"].initial = numero + 1

        # Date d'émission
        self.fields["date_emission"].initial = datetime.date.today()

        # Catégories
        self.fields["categories"].initial = ["consommation", "cotisation", "location", "autre"]

        # Sélection famille
        if idfamille:
            self.fields["selection_familles"].initial = "FAMILLE"
            self.fields["famille"].initial = idfamille

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'facturation_toc' %}", enregistrer_label="<i class='fa fa-search margin-r-5'></i>Rechercher des factures à générer", ajouter=False),
            Hidden('liste_factures_json', value=""),
            Fieldset('Généralités',
                Field('periode'),
                Field('lot_factures'),
                Field('prefixe'),
                Field('prochain_numero'),
                Field('date_emission'),
                Field('date_echeance'),
            ),
            Fieldset('Activités',
                Field('activites'),
            ),
            Fieldset('Options',
                Field('categories'),
                Field('prestations_anterieures'),
                Field('selection_familles'),
                Field('famille'),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Validation des activités
        # activites = json.loads(self.cleaned_data["activites"])
        # if len(activites["ids"]) == 0:
        #     self.add_error("activites", "Vous devez sélectionner au moins une activité ou un groupe d'activité")

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