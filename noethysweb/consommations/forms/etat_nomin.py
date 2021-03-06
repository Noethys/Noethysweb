# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field, TabHolder, Tab
from django_select2.forms import Select2MultipleWidget
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, Profil_configuration
from core.models import Activite, Parametre, Individu, Caisse
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from consommations.widgets import ColonnesEtatNominWidget


class Formulaire(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil de configuration", queryset=Parametre.objects.none(), widget=Profil_configuration({"categorie": "etat_nomin", "module": "consommations.views.etat_nomin"}), required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    etats = forms.MultipleChoiceField(required=True, widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), choices=[("reservation", "Pointage en attente"), ("present", "Présent"), ("attente", "Attente"), ("absentj", "Absence justifiée"), ("absenti", "Absence injustifiée")], initial=["reservation", "present"])
    colonnes = forms.CharField(label="Sélection des colonnes", required=False, widget=ColonnesEtatNominWidget())

    filtre_villes = forms.TypedChoiceField(label="Filtre sur les villes", choices=[("TOUTES", "Toutes les villes"), ("SELECTION", "Uniquement les villes sélectionnées")], initial="TOUTES", required=False)
    villes = forms.MultipleChoiceField(label="Sélection de villes", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), choices=[], required=False)

    filtre_caisses = forms.TypedChoiceField(label="Filtre sur les caisses", choices=[("TOUTES", "Toutes les caisses"), ("SELECTION", "Uniquement les caisses sélectionnées")], initial="TOUTES", required=False)
    caisses = forms.MultipleChoiceField(label="Sélection de caisses", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Profil
        conditions = Q(categorie="etat_nomin")
        conditions &= (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True))
        conditions &= (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        self.fields['profil'].queryset = Parametre.objects.filter(conditions).order_by("nom")
        self.fields["profil"].widget.request = self.request
        self.fields['profil'].label = False

        # Sélectionne uniquement les activités autorisées
        self.fields["activites"].queryset = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("date_fin")

        # Colonnes
        self.fields['colonnes'].label = False

        # Villes
        villes = list({individu.ville_resid: True for individu in Individu.objects.all()}.keys())
        self.fields["villes"].choices = sorted([(ville, ville) for ville in villes if ville])

        # Caisses
        self.fields["caisses"].choices = sorted([(caisse.pk, caisse.nom) for caisse in Caisse.objects.all().order_by("nom")])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'consommations_toc' %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""<button type="submit" form="form_parametres" class="btn btn-primary margin-r-5" name="type_submit" title="Actualiser les résultats"><i class="fa fa-refresh margin-r-5"></i> Actualiser les résultats</button>""")
                ]
            ),
            Field("profil"),
            TabHolder(
                Tab("Généralités",
                    Field("periode"),
                    Field("activites"),
                ),
                Tab("Filtres",
                    Field("etats"),
                    Field("filtre_villes"),
                    Field("villes"),
                    Field("filtre_caisses"),
                    Field("caisses"),
                ),
                Tab("Colonnes",
                    Field("colonnes"),
                ),
                Tab("Résultats",
                    HTML(HTML_RESULTATS),
                ),
            ),
            HTML(EXTRA_HTML),
        )


EXTRA_HTML = """
<script>

    function get_parametres_profil() {
        return $("#form_parametres").serialize();
    };

    function appliquer_profil(idprofil) {
        $("#form_parametres").submit();
    };

    function On_change_villes() {
        $('#div_id_villes').hide();
        if ($("#id_filtre_villes").val() == 'SELECTION') {
            $('#div_id_villes').show();
        };
    }
    $(document).ready(function() {
        $('#id_filtre_villes').on('change', On_change_villes);
        On_change_villes.call($('#id_filtre_villes').get(0));
    });

    function On_change_caisses() {
        $('#div_id_caisses').hide();
        if ($("#id_filtre_caisses").val() == 'SELECTION') {
            $('#div_id_caisses').show();
        };
    }
    $(document).ready(function() {
        $('#id_filtre_caisses').on('change', On_change_caisses);
        On_change_caisses.call($('#id_filtre_caisses').get(0));
    });

</script>
"""

HTML_RESULTATS = """

    <script>
        var contenu_table = JSON.parse('{{ liste_lignes|escapejs }}');
        var affiche_pagination = false;
    </script>

    <table id="table" class="table-sm" data-height="700" data-show-footer='true'>
        <thead>
            <tr>
                {% for colonne in liste_colonnes %}
                    <th data-field="{{ forloop.counter0 }}" data-halign="center" data-align="center" data-footer-formatter="calcule_total">{{ colonne }}</th>
                {% endfor %}
            </tr>
        </thead>
    </table>

    <script>
        function calcule_total(items) {
            {# Calcule le total de chaque colonne #}
            var colonne = this.field;
            if (colonne === "0") {return "Total"}
            var total = 0;
            items.forEach(function(item) {
                if ($.isNumeric(item[colonne])) {
                    total = total + item[colonne];
                } else {
                    if (item[colonne].includes("h")) {
                        var heure = item[colonne].split("h");
                        var heures = parseInt(heure[0]);
                        var minutes = parseInt(heure[1]);
                        total += heures + (0.1 * minutes * 100 / 60)
                    }
                };
            });
            return total;
        };
    </script>

"""
