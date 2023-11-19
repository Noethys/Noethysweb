# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, ButtonHolder, Hidden
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget, Select_avec_commandes, SelectionActivitesWidget, DateRangePickerWidget
from core.models import LotRappels, Famille, LotFactures
from core.forms.select2 import Select2MultipleWidget, Select2Widget
import datetime
from django.contrib import messages
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    date_reference = forms.DateField(label="Date de référence", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    lot_rappels = forms.ModelChoiceField(label="Lot de rappels", queryset=LotRappels.objects.all().order_by("-pk"), required=False, widget=Select_avec_commandes({
            "donnees_extra": {}, "url_ajax": "ajax_modifier_lot_rappels",
            "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot de rappels", "modifier": "Modifier un lot de rappels"}}))
    date_emission = forms.DateField(label="Date d'émission", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    choix_categories = [("consommation", "Consommations"), ("cotisation", "Adhésions"), ("location", "Locations"), ("autre", "Autres"), ]
    categories = forms.MultipleChoiceField(label="Catégories de prestations", widget=Select2MultipleWidget(), choices=choix_categories, required=True)
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget())
    choix_selection_familles = [("TOUTES", "Toutes les familles"), ("FAMILLE", "Uniquement la famille sélectionnée"),
                                ("SANS_PRESTATION", "Uniquement les familles qui n'ont pas de prestations sur une période donnée"),
                                ("ABSENT_LOT_FACTURES", "Uniquement les familles qui n'ont aucune facture dans un lot de factures donné")]
    selection_familles = forms.TypedChoiceField(label="Sélection des familles", choices=choix_selection_familles, initial="TOUTES", required=False)
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget(), queryset=Famille.objects.all().order_by("nom"), required=False)
    periode = forms.CharField(label="Période", required=False, widget=DateRangePickerWidget())
    lot_factures = forms.ModelChoiceField(label="Lot de factures", widget=Select2Widget(), queryset=LotFactures.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        idfamille = kwargs.pop('idfamille', None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_rappels_generation'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date de référence
        self.fields["date_reference"].initial = datetime.date.today()

        # Date d'émission
        self.fields["date_emission"].initial = datetime.date.today()

        # Catégories
        self.fields["categories"].initial = ["consommation", "cotisation", "location", "autre"]

        # Sélection famille
        if idfamille:
            self.fields["selection_familles"].initial = "FAMILLE"
            self.fields["famille"].initial = idfamille

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'facturation_toc' %}", enregistrer_label="<i class='fa fa-search margin-r-5'></i>Rechercher des lettres de rappel à générer", ajouter=False),
            Hidden('liste_rappels_json', value=""),
            Fieldset('Généralités',
                Field('date_reference'),
                Field('lot_rappels'),
                Field('date_emission'),
            ),
            Fieldset('Activités',
                Field('activites'),
            ),
            Fieldset('Options',
                Field('categories'),
                Field('selection_familles'),
                Field('famille'),
                Field('periode'),
                Field('lot_factures'),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Sélection des familles
        if self.cleaned_data["selection_familles"] == "FAMILLE" and not self.cleaned_data["famille"]:
            self.add_error('famille', "Vous devez sélectionner une famille dans la liste")
            return

        if self.cleaned_data["selection_familles"] == "ABSENT_LOT_FACTURES" and not self.cleaned_data["lot_factures"]:
            self.add_error('lot_factures', "Vous devez sélectionner un lot de factures dans la liste")
            return

        # Avertissements
        if not self.cleaned_data["lot_rappels"]:
            messages.add_message(self.request, messages.INFO, "Remarque : Vous n'avez pas sélectionné de lot de rappels")

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// validite_type
function On_change_selection_familles() {
    $('#div_id_famille').hide();
    $('#div_id_periode').hide();
    $('#div_id_lot_factures').hide();
    if($(this).val() == 'FAMILLE') {$('#div_id_famille').show()};
    if($(this).val() == 'SANS_PRESTATION') {$('#div_id_periode').show()};
    if($(this).val() == 'ABSENT_LOT_FACTURES') {$('#div_id_lot_factures').show()};
}
$(document).ready(function() {
    $('#id_selection_familles').change(On_change_selection_familles);
    On_change_selection_familles.call($('#id_selection_familles').get(0));
});

</script>
"""