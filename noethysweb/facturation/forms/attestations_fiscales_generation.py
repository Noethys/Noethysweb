# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.contrib import messages
from core.forms.select2 import Select2Widget
from django.db.models import Max
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML, Hidden
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget, Select_avec_commandes, SelectionActivitesWidget, DateRangePickerWidget
from core.models import LotAttestationsFiscales, Famille, AttestationFiscale
from core.forms.base import FormulaireBase
from core.utils import utils_dates
from facturation.widgets import ChampAutomatiqueWidget


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    lot_attestations_fiscales = forms.ModelChoiceField(label="Lot d'attestations fiscales", queryset=LotAttestationsFiscales.objects.all().order_by("-pk"), required=False, widget=Select_avec_commandes({
            "donnees_extra": {}, "url_ajax": "ajax_modifier_lot_attestations_fiscales",
            "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot d'attestations fiscales", "modifier": "Modifier un lot d'attestations fiscales"}}))
    date_emission = forms.DateField(label="Date d'émission", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    prochain_numero = forms.CharField(label="Prochain numéro", required=True, widget=ChampAutomatiqueWidget({"label_checkbox": "Automatique", "title": "Attribuez ici le prochain numéro de la première attestation générée. Les attestations suivantes seront incrémentées automatiquement.", "type": "number"}))
    choix_selection_prestations = [("TOUTES", "Toutes les prestations individuelles"), ("ACTIVITES", "Uniquement les prestations individuelles des activités sélectionnées")]
    selection_prestations = forms.TypedChoiceField(label="Sélection des prestations", choices=choix_selection_prestations, initial="ACTIVITES", required=False)
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget())
    choix_selection_familles = [("TOUTES", "Toutes les familles"), ("FAMILLE", "Uniquement la famille sélectionnée")]
    selection_familles = forms.TypedChoiceField(label="Sélection des familles", choices=choix_selection_familles, initial="TOUTES", required=False)
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget({"lang": "fr", "data-width": "100%"}), queryset=Famille.objects.all().order_by("nom"), required=False)
    date_naiss_min = forms.DateField(label="Date de naissance minimale", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}), help_text="Saisissez la date de naissance minimale des individus. Laissez vide pour sélectionner tous les individus quelque soit leur âge.")
    type_donnee = forms.ChoiceField(label="Type de donnée", choices=[("FACTURE", "Les prestations de la période"), ("REGLE", "Les prestations de la période réglées"), ("REGLE_PERIODE", "Les prestations réglées durant la période")], initial="FACTURE", required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        idfamille = kwargs.pop('idfamille', None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_attestations_fiscales_generation'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Période
        annee_precedente = datetime.date.today().year - 1
        self.fields["periode"].initial = "%s - %s" % (utils_dates.ConvertDateToFR(datetime.date(annee_precedente, 1, 1)),
                                                      utils_dates.ConvertDateToFR(datetime.date(annee_precedente, 12, 31)))

        # Date de naissance min
        self.fields["date_naiss_min"].initial = datetime.date(annee_precedente - 6, 1, 1)

        # Date d'émission
        self.fields["date_emission"].initial = datetime.date.today()

        # Prochain numéro
        numero = (AttestationFiscale.objects.all().aggregate(Max('numero')))['numero__max']
        if not numero: numero = 0
        self.fields["prochain_numero"].initial = numero + 1

        # Sélection famille
        if idfamille:
            self.fields["selection_familles"].initial = "FAMILLE"
            self.fields["famille"].initial = idfamille

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'facturation_toc' %}", enregistrer_label="<i class='fa fa-search margin-r-5'></i>Rechercher les données", ajouter=False),
            Hidden('liste_prestations_json', value=""),
            Hidden('liste_attestations_fiscales_json', value=""),
            Fieldset('Généralités',
                Field('periode'),
                Field('type_donnee'),
                Field('lot_attestations_fiscales'),
                Field('prochain_numero'),
                Field('date_emission'),
                Field('date_naiss_min'),
            ),
            Fieldset('Prestations',
                Field('selection_prestations'),
                Field('activites'),
            ),
            Fieldset('Options',
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
        if not self.cleaned_data["lot_attestations_fiscales"]:
            messages.add_message(self.request, messages.INFO, "Remarque : Vous n'avez pas sélectionné de lot d'attestations fiscales")

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// validite_type
function On_change_selection_prestations() {
    $('#div_id_activites').hide();
    if($(this).val() == 'ACTIVITES') {$('#div_id_activites').show()};
}
$(document).ready(function() {
    $('#id_selection_prestations').change(On_change_selection_prestations);
    On_change_selection_prestations.call($('#id_selection_prestations').get(0));
});

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
