# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.forms.select2 import Select2MultipleWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, SelecteurModelesPlanningWidget
from core.utils.utils_commandes import Commandes
from core.forms.base import FormulaireBase
from core.models import ModelePlanningCollaborateur


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(), help_text="Sélectionnez la période sur laquelle appliquer les modèles.")
    modeles = forms.ModelMultipleChoiceField(label="Modèles", required=True, widget=SelecteurModelesPlanningWidget({}),
                                             queryset=ModelePlanningCollaborateur.objects.none(), help_text="Sélectionnez un ou plusieurs modèles de planning à appliquer.")
    departs = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.fields["modeles"].queryset = ModelePlanningCollaborateur.objects.all().order_by("nom")
        resolver = getattr(self.request, "resolver_match", None)
        self.fields["modeles"].widget.attrs["idcollaborateur"] = int(resolver.kwargs.get("idcollaborateur", 0)) if resolver else 0

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Appliquer", ajouter=False, annuler_url="{% url 'collaborateur_evenements_liste' idcollaborateur=idcollaborateur %}"),
            Field("periode"),
            Field("modeles"),
            Field("departs"),
            HTML(FRISE_HTML),
        )


FRISE_HTML = """
{% load static %}
<div class="form-group row"><div class="col-md-2"></div><div class="col-md-10"><div id="frise_modeles" hidden></div></div></div>
<script src="{% static 'js/frise_modeles_planning.js' %}"></script>
<script>
    $(document).ready(function() {
        function Dates_formulaire() {
            var texte = $("#id_periode").val() || "";
            var morceaux = texte.split(" - ");
            if (morceaux.length !== 2) { return []; }
            var debut = moment(morceaux[0], "DD/MM/YYYY"), fin = moment(morceaux[1], "DD/MM/YYYY");
            if (!debut.isValid() || !fin.isValid() || fin.diff(debut, "days") > 400) { return []; }
            var dates = [];
            for (var date = debut.clone(); date.isSameOrBefore(fin); date.add(1, "days")) { dates.push(date.format("YYYY-MM-DD")); }
            return dates;
        }
        var departs_initiaux = {};
        try { departs_initiaux = JSON.parse($("#id_departs").val() || "{}"); } catch (e) {}
        var frise = FriseModelesPlanning({
            departs: departs_initiaux,
            conteneur: "#frise_modeles", url: "{% url 'ajax_modeles_planning_get_frise' %}", csrf: "{{ csrf_token }}",
            parametres: function() { return {modeles: ($("#id_modeles").val() || []).map(function(id) { return parseInt(id); }), dates: Dates_formulaire()}; },
            change: function() { $("#id_departs").val(JSON.stringify(frise.departs())); }
        });
        $("#id_modeles").on("change", frise.maj);
        $("#id_periode").on("change apply.daterangepicker", frise.maj);
        frise.maj();
    });
</script>
"""
