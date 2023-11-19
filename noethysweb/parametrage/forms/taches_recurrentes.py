# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.utils.utils_commandes import Commandes
from core.models import Tache_recurrente, Structure, LISTE_MOIS, LISTE_VACANCES
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):

    choix_frequence = [("DAILY", "Journalier"), ("WEEKLY", "Hebdomadaire"), ("MONTHLY_DAY", "Mensuel par jour"), ("MONTHLY_DATE", "Mensuel par date"), ("YEARLY_DAY", "Annuel par jour"), ("YEARLY_DATE", "Annuel par date"), ("VACANCES", "Vacances")]
    frequence = forms.ChoiceField(label="Fréquence", choices=choix_frequence, initial="DAILY", required=True)

    choix_interval_daily = [(1, "Tous les jours"),] + [(x, "Tous les %d jours" % x) for x in range(2, 31)]
    interval_daily = forms.ChoiceField(label="Répétition", choices=choix_interval_daily, initial=1, required=False)

    choix_interval_weekly = [(1, "Toutes les semaines"),] + [(x, "Toutes les %d semaines" % x) for x in range(2, 25)]
    interval_weekly = forms.ChoiceField(label="Répétition", choices=choix_interval_weekly, initial=1, required=False)

    choix_interval_monthly = [(1, "Tous les mois"),] + [(x, "Tous les %d mois" % x) for x in range(2, 13)]
    interval_monthly = forms.ChoiceField(label="Répétition", choices=choix_interval_monthly, initial=1, required=False)

    choix_interval_yearly = [(1, "Tous les ans"),] + [(x, "Toutes les %d années" % x) for x in range(2, 11)]
    interval_yearly = forms.ChoiceField(label="Répétition", choices=choix_interval_yearly, initial=1, required=False)

    choix_interval_vacances = [(0, "Toutes les périodes"),] + LISTE_VACANCES
    interval_vacances = forms.ChoiceField(label="Répétition", choices=choix_interval_vacances, initial=0, required=False)

    choix_weeklyday = [("MO", "Lundi"), ("TU", "Mardi"), ("WE", "Mercredi"), ("TH", "Jeudi"), ("FR", "Vendredi"), ("SA", "Samedi"), ("SU", "Dimanche")]
    repeat_weeklyday = forms.MultipleChoiceField(label="Jours", widget=Select2MultipleWidget(), choices=choix_weeklyday, required=False)

    repeat_yearly_month = forms.ChoiceField(label="Mois", choices=LISTE_MOIS, initial=0, required=False)

    choix_monthlydate = [(1, "Le 1er jour du mois")] + [(x, "Le %dème jour du mois" % x) for x in range(2, 32)]
    repeat_monthlydate = forms.MultipleChoiceField(label="Jour", widget=Select2MultipleWidget(), choices=choix_monthlydate, required=False)

    choix_monthlyday = []
    for num, label_num in [(1, "Premier"), (2, "Deuxième"), (3, "Troisième"), (4, "Quatrième"), (5, "Cinquième"), (-1, "Dernier")]:
        for code_jour, label_jour in choix_weeklyday:
            choix_monthlyday.append(("%d%s" % (num, code_jour), "%s %s" % (label_num, label_jour.lower())))
    repeat_monthlyday = forms.MultipleChoiceField(label="Jour", widget=Select2MultipleWidget(), choices=choix_monthlyday, required=False)

    choix_repeat_vacances = [("FIRST", "Le 1er jour des vacances"), ("LAST", "Le dernier jour des vacances"),
                             ("BEFORE_FIRST", "X jours avant le premier jour des vacances"), ("AFTER_FIRST", "X jours après le premier jour des vacances"),
                             ("BEFORE_LAST", "X jours avant le dernier jour des vacances"), ("AFTER_LAST", "X jours après le dernier jour des vacances"),]
    repeat_vacances = forms.ChoiceField(label="Jour", choices=choix_repeat_vacances, initial=1, required=False)

    nbre_jours = forms.IntegerField(label="Nbre de jours", initial=0, min_value=0, max_value=300, required=False)

    choix_periode = [(None, "Toutes les périodes"), ("VACS_IN", "Durant une période de vacances"), ("VACS_OUT", "Durant une période scolaire")]
    periode = forms.ChoiceField(label="Période", choices=choix_periode, initial=None, required=False)

    acces = forms.ChoiceField(label="Utilisateurs associés", initial="automatique", required=True, help_text="Sélectionnez les utilisateurs destinataires de cette tâche.", choices=[
        (None, "-------"), ("moi", "Uniquement moi"),
        ("structure", "Les utilisateurs de la structure suivante"),
        ("tous", "Tous les utilisateurs"),
    ])
    structure = forms.ModelChoiceField(label="Structure", queryset=Structure.objects.none(), required=False, help_text="Sélectionnez une structure dans la liste proposée.")

    class Meta:
        model = Tache_recurrente
        fields = "__all__"
        widgets = {
            "titre": forms.Textarea(attrs={"rows": 4}),
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'taches_recurrentes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        liste_mots_cles = [
            ("{DATE_COURTE}", "Date courte"),
            ("{DATE_LONGUE}", "Date longue"),
            ("{NOM_JOUR}", "Nom du jour de la semaine"),
            ("{MOIS}", "Nom du mois"),
            ("{MOIS_PRECEDENT}", "Nom du mois précédent"),
            ("{MOIS_SUIVANT}", "Nom du mois suivant"),
            ("{ANNEE}", "Année"),
            ("{ANNEE_PRECEDENTE}", "Année précédente"),
            ("{ANNEE_SUIVANTE}", "Année suivante"),
            ("{NOM_VACANCE}", "Nom de la période de vacances"),
        ]

        # Date de début
        if not self.instance.pk:
            self.fields["date_debut"].initial = datetime.date.today()

        # Importation de la rrule
        if self.instance.pk:
            parametres = {param.split("=")[0]: param.split("=")[1] for param in self.instance.recurrence.split(";")}
            if parametres["FREQ"] == "DAILY":
                self.fields["frequence"].initial = "DAILY"
                self.fields["interval_daily"].initial = parametres["INTERVAL"]
            if parametres["FREQ"] == "WEEKLY":
                self.fields["frequence"].initial = "WEEKLY"
                self.fields["interval_weekly"].initial = parametres["INTERVAL"]
                self.fields["repeat_weeklyday"].initial = parametres["BYDAY"].split(",")
            if parametres["FREQ"] == "MONTHLY" and "BYMONTHDAY" in parametres:
                self.fields["frequence"].initial = "MONTHLY_DATE"
                self.fields["interval_monthly"].initial = parametres["INTERVAL"]
                self.fields["repeat_monthlydate"].initial = parametres["BYMONTHDAY"].split(",")
            if parametres["FREQ"] == "MONTHLY" and "BYDAY" in parametres:
                self.fields["frequence"].initial = "MONTHLY_DAY"
                self.fields["interval_monthly"].initial = parametres["INTERVAL"]
                self.fields["repeat_monthlyday"].initial = parametres["BYDAY"].split(",")
            if parametres["FREQ"] == "YEARLY" and "BYMONTHDAY" in parametres:
                self.fields["frequence"].initial = "YEARLY_DATE"
                self.fields["interval_yearly"].initial = parametres["INTERVAL"]
                self.fields["repeat_yearly_month"].initial = parametres["BYMONTH"]
                self.fields["repeat_monthlydate"].initial = parametres["BYMONTHDAY"].split(",")
            if parametres["FREQ"] == "YEARLY" and "BYDAY" in parametres:
                self.fields["frequence"].initial = "YEARLY_DAY"
                self.fields["interval_yearly"].initial = parametres["INTERVAL"]
                self.fields["repeat_yearly_month"].initial = parametres["BYMONTH"]
                self.fields["repeat_monthlyday"].initial = parametres["BYDAY"].split(",")
            if parametres["FREQ"] == "VACANCES":
                self.fields["frequence"].initial = "VACANCES"
                self.fields["interval_vacances"].initial = parametres["INTERVAL"]
                self.fields["repeat_vacances"].initial = parametres["BASE"]
                self.fields["nbre_jours"].initial = parametres["NBJOURS"]

        # Accès publication
        self.fields["structure"].empty_label = "-------"
        if self.instance.pk:
            if self.instance.utilisateur:
                self.fields["acces"].initial = "moi"
            elif self.instance.structure:
                self.fields["acces"].initial = "structure"
            else:
                self.fields["acces"].initial = "tous"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'taches_recurrentes_liste' %}"),
            Fieldset("Titre",
                Field("titre"),
                Div(
                    HTML("<label class='col-form-label col-md-2 requiredField'>Mots-clés</label>"),
                    Div(HTML(Get_html_mots_cles(liste_mots_cles)), css_class="col-md-10"),
                    css_class="form-group row"
                ),
            ),
            Fieldset("Période de validité",
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset("Programmation",
                Field("frequence"),
                Field("interval_daily"),
                Field("interval_monthly"),
                Field("interval_weekly"),
                Field("interval_yearly"),
                Field("interval_vacances"),
                Field("repeat_weeklyday"),
                Field("repeat_yearly_month"),
                Field("repeat_monthlydate"),
                Field("repeat_monthlyday"),
                Field("repeat_vacances"),
                Field("nbre_jours"),
                Field("periode"),
            ),
            Fieldset("Public",
                Field("acces"),
                Field("structure"),
            ),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        # Vérification de la saisie
        if self.cleaned_data["frequence"] == "WEEKLY" and not self.cleaned_data["repeat_weeklyday"]:
            self.add_error("repeat_weeklyday", "Vous devez sélectionner au moins un jour")
            return

        if self.cleaned_data["frequence"] == "MONTHLY_DAY" and not self.cleaned_data["repeat_monthlyday"]:
            self.add_error("repeat_monthlyday", "Vous devez sélectionner au moins un jour")
            return

        if self.cleaned_data["frequence"] == "MONTHLY_DATE" and not self.cleaned_data["repeat_monthlydate"]:
            self.add_error("repeat_monthlydate", "Vous devez sélectionner au moins une date")
            return

        if self.cleaned_data["frequence"] == "YEARLY_DAY" and not self.cleaned_data["repeat_monthlyday"]:
            self.add_error("repeat_monthlyday", "Vous devez sélectionner au moins un jour")
            return

        if self.cleaned_data["frequence"] == "YEARLY_DATE" and not self.cleaned_data["repeat_monthlydate"]:
            self.add_error("repeat_monthlydate", "Vous devez sélectionner au moins une date")
            return

        if self.cleaned_data["frequence"] == "VACANCES" and self.cleaned_data["frequence"] == "repeat_vacances" and not self.cleaned_data["nbre_jours"]:
            self.add_error("nbre_jours", "Vous devez saisir un nombre de jours")
            return

        # Accès publication
        self.cleaned_data["utilisateur"] = self.request.user if self.cleaned_data["acces"] == "moi" else None
        self.cleaned_data["structure"] = self.cleaned_data["structure"] if self.cleaned_data["acces"] == "structure" else None
        if self.cleaned_data["acces"] == "structure" and not self.cleaned_data["structure"]:
            raise forms.ValidationError('Vous devez sélectionner une structure dans la liste proposée.')

        # Génération de la rrule
        rrule = None
        if self.cleaned_data["frequence"] == "DAILY":
            rrule = "FREQ=DAILY;INTERVAL=%s" % self.cleaned_data["interval_daily"]
        if self.cleaned_data["frequence"] == "WEEKLY":
            rrule = "FREQ=WEEKLY;INTERVAL=%s;BYDAY=%s" % (self.cleaned_data["interval_weekly"], ",".join(self.cleaned_data["repeat_weeklyday"]))
        if self.cleaned_data["frequence"] == "MONTHLY_DATE":
            rrule = "FREQ=MONTHLY;INTERVAL=%s;BYMONTHDAY=%s" % (self.cleaned_data["interval_monthly"], ",".join(self.cleaned_data["repeat_monthlydate"]))
        if self.cleaned_data["frequence"] == "MONTHLY_DAY":
            rrule = "FREQ=MONTHLY;INTERVAL=%s;BYDAY=%s" % (self.cleaned_data["interval_monthly"], ",".join(self.cleaned_data["repeat_monthlyday"]))
        if self.cleaned_data["frequence"] == "YEARLY_DATE":
            rrule = "FREQ=YEARLY;INTERVAL=%s;BYMONTH=%s;BYMONTHDAY=%s" % (self.cleaned_data["interval_yearly"], self.cleaned_data["repeat_yearly_month"], ",".join(self.cleaned_data["repeat_monthlydate"]))
        if self.cleaned_data["frequence"] == "YEARLY_DAY":
            rrule = "FREQ=YEARLY;INTERVAL=%s;BYMONTH=%s;BYDAY=%s" % (self.cleaned_data["interval_yearly"], self.cleaned_data["repeat_yearly_month"], ",".join(self.cleaned_data["repeat_monthlyday"]))
        if self.cleaned_data["frequence"] == "VACANCES":
            rrule = "FREQ=VACANCES;INTERVAL=%s;BASE=%s;NBJOURS=%s" % (self.cleaned_data["interval_vacances"], self.cleaned_data["repeat_vacances"], self.cleaned_data["nbre_jours"])

        if self.cleaned_data["frequence"] != "VACANCES" and self.cleaned_data["periode"] in ["VACS_IN", "VACS_OUT"]:
            rrule += ";OPTIONS=%s" % self.cleaned_data["periode"]

        self.cleaned_data["recurrence"] = rrule
        return self.cleaned_data


def Get_html_mots_cles(liste_mots_cles=[]):
    html_detail = []
    for code, label in liste_mots_cles:
        html_detail.append("""<li><a href='#' title="%s" name="%s" class="mot_cle"><i class='fa fa-tag'></i> %s</a></li> """ % (label, code, code))
    html = """
    <style>
        .liste_mots_cles {
            background: #f4f4f4;
            padding: 10px;
            margin-bottom: 10px;
        }
        .liste_mots_cles li {
            display: inline;
            white-space: nowrap;
            margin-right: 20px;
        }
    </style>
    <div class='card'>
        <div class='card-body liste_mots_cles m-0'>
            <div style='color: #b4b4b4;margin-bottom: 5px;'>
                <i class='fa fa-lightbulb-o'></i> Cliquez sur un mot-clé pour l'insérer dans le texte
            </div>
            <div>
                <ul class='list-unstyled' style="margin-bottom: 2px;">
                    %s
                </ul>
            </div>
        </div>
    </div>
    <script>
        $(".mot_cle").on('click', function(event) {
            event.preventDefault();
            var tav = $('#id_titre').val(),
            strPos = $('#id_titre')[0].selectionStart;
            texte_avant = (tav).substring(0, strPos),
            texte_apres = (tav).substring(strPos, tav.length); 
            $('#id_titre').val(texte_avant + this.name + texte_apres);
        });
    </script>
    """ % "".join(html_detail)
    return html


EXTRA_HTML = """
<script>
    function On_change_frequence() {
        $('#div_id_interval_daily').hide();
        $('#div_id_interval_weekly').hide();
        $('#div_id_interval_monthly').hide();
        $('#div_id_interval_yearly').hide();
        $('#div_id_interval_vacances').hide();
        $('#div_id_repeat_weeklyday').hide();
        $('#div_id_repeat_yearly_month').hide();
        $('#div_id_repeat_monthlydate').hide();
        $('#div_id_repeat_monthlyday').hide();
        $('#div_id_repeat_vacances').hide();
        $('#div_id_nbre_jours').hide();
        $('#div_id_periode').hide();
        
        if ($("#id_frequence").val() == 'DAILY') {
            $('#div_id_interval_daily').show();
            $('#div_id_periode').show();
        };
        if ($("#id_frequence").val() == 'WEEKLY') {
            $('#div_id_interval_weekly').show();
            $('#div_id_repeat_weeklyday').show();
            $('#div_id_periode').show();
        };
        if ($("#id_frequence").val() == 'MONTHLY_DAY') {
            $('#div_id_interval_monthly').show();
            $('#div_id_repeat_monthlyday').show();
            $('#div_id_periode').show();
        };
        if ($("#id_frequence").val() == 'MONTHLY_DATE') {
            $('#div_id_interval_monthly').show();
            $('#div_id_repeat_monthlydate').show();
            $('#div_id_periode').show();
        };
        if ($("#id_frequence").val() == 'YEARLY_DAY') {
            $('#div_id_interval_yearly').show();
            $('#div_id_repeat_yearly_month').show();
            $('#div_id_repeat_monthlyday').show();
            $('#div_id_periode').show();
        };
        if ($("#id_frequence").val() == 'YEARLY_DATE') {
            $('#div_id_interval_yearly').show();
            $('#div_id_repeat_yearly_month').show();
            $('#div_id_repeat_monthlydate').show();
            $('#div_id_periode').show();
        };
        if ($("#id_frequence").val() == 'VACANCES') {
            $('#div_id_interval_vacances').show();
            $('#div_id_repeat_vacances').show();
            $('#id_repeat_vacances').trigger('change');
        };
    }
    $(document).ready(function() {
        $('#id_frequence').on('change', On_change_frequence);
        On_change_frequence.call($('#id_frequence').get(0));
    });
    
    function On_change_repeat_vacances() {
        $('#div_id_nbre_jours').hide();
        if ($.inArray($("#id_repeat_vacances").val(), ["BEFORE_FIRST", "AFTER_FIRST", "BEFORE_LAST", "AFTER_LAST"]) !== -1) {
            $('#div_id_nbre_jours').show();
        };
    }
    $(document).ready(function() {
        $('#id_repeat_vacances').on('change', On_change_repeat_vacances);
        On_change_repeat_vacances.call($('#id_repeat_vacances').get(0));
    });

    function On_change_acces() {
        $('#div_id_structure').hide();
        if ($("#id_acces").val() == 'structure') {
            $('#div_id_structure').show();
        };
    }
    $(document).ready(function() {
        $('#id_acces').on('change', On_change_acces);
        On_change_acces.call($('#id_acces').get(0));
    });

</script>
"""
