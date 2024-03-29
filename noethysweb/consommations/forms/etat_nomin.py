# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field, TabHolder, Tab
from core.forms.select2 import Select2MultipleWidget
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, Profil_configuration
from core.models import Activite, Parametre, Individu, Caisse, Ecole, QuestionnaireQuestion
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from consommations.widgets import ColonnesEtatNominWidget


class Formulaire(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil de configuration", queryset=Parametre.objects.none(), widget=Profil_configuration({"categorie": "etat_nomin", "module": "consommations.views.etat_nomin"}), required=False)
    titre = forms.CharField(label="Titre", required=True, help_text="Titre du document à l'impression.")
    tri = forms.ChoiceField(label="Tri", choices=[], required=False)
    ordre = forms.ChoiceField(label="Ordre", choices=[("croissant", "Croissant"), ("decroissant", "Décroissant")], initial="croissant", required=False)
    format_durees = forms.ChoiceField(label="Format des durées", choices=[("horaire", "Horaire"), ("decimal", "Décimal")], initial="horaire", required=False, help_text="Choisissez le format d'affichage des données de temps: Horaire (Ex: 8h30) ou décimal (Ex: 8.5).")

    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    etats = forms.MultipleChoiceField(required=True, widget=Select2MultipleWidget(), choices=[("reservation", "Réservation"), ("present", "Présent"), ("attente", "Attente"), ("absentj", "Absence justifiée"), ("absenti", "Absence injustifiée")], initial=["reservation", "present"])
    colonnes = forms.CharField(label="Sélection des colonnes", required=False, widget=ColonnesEtatNominWidget())

    filtre_villes = forms.TypedChoiceField(label="Filtre sur les villes", choices=[("TOUTES", "Toutes les villes"), ("SELECTION", "Uniquement les villes sélectionnées")], initial="TOUTES", required=False)
    villes = forms.MultipleChoiceField(label="Sélection de villes", widget=Select2MultipleWidget(), choices=[], required=False)

    filtre_caisses = forms.TypedChoiceField(label="Filtre sur les caisses", choices=[("TOUTES", "Toutes les caisses"), ("SELECTION", "Uniquement les caisses sélectionnées")], initial="TOUTES", required=False)
    caisses = forms.MultipleChoiceField(label="Sélection de caisses", widget=Select2MultipleWidget(), choices=[], required=False)

    filtre_ecoles = forms.TypedChoiceField(label="Filtre sur les écoles", choices=[("TOUTES", "Toutes les écoles"), ("SELECTION", "Uniquement les écoles sélectionnées")], initial="TOUTES", required=False)
    ecoles = forms.MultipleChoiceField(label="Sélection d'écoles", widget=Select2MultipleWidget(), choices=[], required=False)

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
        self.fields["activites"].queryset = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("date_fin", "nom")

        # Titre
        self.fields["titre"].initial = "Etat nominatif"

        # Tri
        liste_choix = [
            ("individu_nom_complet", "Nom de l'individu"),
            ("individu_prenom", "Prénom de l'individu"),
            ("individu_date_naiss", "Date de naissance de l'individu"),
            ("individu_ville", "Ville de l'individu"),
            ("famille_nom_complet", "Noms des titulaires de la famille"),
        ]
        for categorie in ("individu", "famille"):
            for question in QuestionnaireQuestion.objects.filter(categorie=categorie, visible=True).order_by("ordre"):
                liste_choix.append(("question_%d" % question.pk, question.label))
        self.fields["tri"].choices = liste_choix
        self.fields["tri"].default = "individu_nom_complet"

        # Colonnes
        self.fields['colonnes'].label = False

        # Villes
        villes = list({individu.ville_resid: True for individu in Individu.objects.all()}.keys())
        self.fields["villes"].choices = sorted([(ville, ville) for ville in villes if ville])

        # Caisses
        self.fields["caisses"].choices = sorted([(caisse.pk, caisse.nom) for caisse in Caisse.objects.all().order_by("nom")])

        # Ecoles
        self.fields["ecoles"].choices = sorted([(ecole.pk, ecole.nom) for ecole in Ecole.objects.all().order_by("nom")])

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
                    Field("format_durees"),
                    Field("titre"),
                    Field("tri"),
                    Field("ordre"),
                ),
                Tab("Filtres",
                    Field("etats"),
                    Field("filtre_villes"),
                    Field("villes"),
                    Field("filtre_caisses"),
                    Field("caisses"),
                    Field("filtre_ecoles"),
                    Field("ecoles"),
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

    function On_change_ecoles() {
        $('#div_id_ecoles').hide();
        if ($("#id_filtre_ecoles").val() == 'SELECTION') {
            $('#div_id_ecoles').show();
        };
    }
    $(document).ready(function() {
        $('#id_filtre_ecoles').on('change', On_change_ecoles);
        On_change_ecoles.call($('#id_filtre_ecoles').get(0));
    });
    
</script>
"""

HTML_RESULTATS = """

    <script>
        var contenu_table = JSON.parse('{{ liste_lignes|escapejs }}');
        var affiche_pagination = false;
    </script>

    <table id="table" class="table-sm table-xxs" data-height="700" data-show-footer='true'>
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
                    if ((item[colonne]) && (item[colonne].includes("h"))) {
                        var heure = item[colonne].split("h");
                        var heures = parseInt(heure[0]);
                        var minutes = parseInt(heure[1]);
                        total += heures + (minutes / 60)
                    }
                };
            });
            return total;
        };
    </script>

"""
