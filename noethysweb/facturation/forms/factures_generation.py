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
from core.widgets import DatePickerWidget, DateRangePickerWidget, Select_avec_commandes, SelectionActivitesWidget, CheckDateWidget
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
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    lot_factures = forms.ModelChoiceField(label="Lot de factures", queryset=LotFactures.objects.all().order_by("-pk"), required=False, widget=Select_avec_commandes({
            "donnees_extra": {}, "url_ajax": "ajax_modifier_lot_factures",
            "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot de factures", "modifier": "Modifier un lot de factures"}}))
    prefixe = forms.ModelChoiceField(label="Préfixe de numéro", queryset=PrefixeFacture.objects.all(), required=False)
    prochain_numero = forms.CharField(label="Prochain numéro", required=True, widget=ChampAutomatiqueWidget({"label_checkbox": "Automatique", "title": "Attribuez ici le prochain numéro de facture. Les factures suivantes seront incrémentées automatiquement.", "type": "number"}))
    date_emission = forms.DateField(label="Date d'émission", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    date_echeance = forms.DateField(label="Date d'échéance", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    choix_categories = [("consommation", "Consommations"), ("cotisation", "Adhésions"), ("location", "Locations"), ("autre", "Autres"), ]
    categories = forms.MultipleChoiceField(label="Catégories de prestations", widget=Select2MultipleWidget(), choices=choix_categories, required=True)
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget())
    prestations_anterieures = forms.DateField(label="Prestations antérieures", required=False, widget=DatePickerWidget({"afficher_check": True, "label_checkbox": "Inclure les prestations antérieures non facturées depuis le"}))
    inclure_cotisations_si_conso = forms.BooleanField(label="Inclure les adhésions uniquement pour les familles qui sur les activités cochées", required=False, initial=False)
    choix_selection_familles = [("TOUTES", "Toutes les familles"), ("FAMILLE", "Uniquement la famille sélectionnée")]
    selection_familles = forms.TypedChoiceField(label="Sélection des familles", choices=choix_selection_familles, initial="TOUTES", required=False)
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget(), queryset=Famille.objects.all().order_by("nom"), required=False)
    date_limite_paiement = forms.DateField(label="Date limite paiement en ligne", required=False, widget=DatePickerWidget({"afficher_check": True, "label_checkbox": "Interdire le paiement en ligne après le"}))

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