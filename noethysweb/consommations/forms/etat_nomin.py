# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Div
from crispy_forms.bootstrap import Field
from core.forms.accordeon import Accordeon, Section
from core.forms.select2 import Select2MultipleWidget
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, Profil_configuration
from core.models import Activite, Parametre, Individu, Caisse, Ecole, QuestionnaireQuestion
from core.forms.base import FormulaireBase
from consommations.widgets import ColonnesEtatNominWidget, EtatsConsoWidget


CHOIX_ETATS = [("reservation", "Réservation"), ("present", "Présent"), ("attente", "Attente"), ("absentj", "Absence justifiée"), ("absenti", "Absence injustifiée")]
CHOIX_REGROUPEMENTS = [("aucun", "Aucun"), ("activite", "Activité"), ("ecole", "École"), ("ville", "Ville"), ("caisse", "Caisse")]


class Formulaire(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil de configuration", queryset=Parametre.objects.none(), widget=Profil_configuration({"categorie": "etat_nomin", "module": "consommations.views.etat_nomin"}), required=False)
    titre = forms.CharField(label="Titre", required=True, help_text="Titre du document à l'impression.")
    tri = forms.ChoiceField(label="Tri", choices=[], required=False)
    ordre = forms.ChoiceField(label="Ordre", choices=[("croissant", "Croissant"), ("decroissant", "Décroissant")], initial="croissant", required=False)
    format_durees = forms.ChoiceField(label="Format des durées", choices=[("horaire", "Horaire"), ("decimal", "Décimal")], initial="horaire", required=False)
    regroupement = forms.ChoiceField(label="Regrouper par", choices=CHOIX_REGROUPEMENTS, initial="aucun", required=False)

    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    etats = forms.MultipleChoiceField(label="États des consommations", required=True, widget=EtatsConsoWidget(), choices=CHOIX_ETATS, initial=["reservation", "present"])
    colonnes = forms.CharField(label="Sélection des colonnes", required=False, widget=ColonnesEtatNominWidget())

    filtre_villes = forms.TypedChoiceField(label="Villes", choices=[("TOUTES", "Toutes les villes"), ("SELECTION", "Uniquement les villes sélectionnées")], initial="TOUTES", required=False)
    villes = forms.MultipleChoiceField(label="Sélection de villes", widget=Select2MultipleWidget(), choices=[], required=False)

    filtre_caisses = forms.TypedChoiceField(label="Caisses", choices=[("TOUTES", "Toutes les caisses"), ("SELECTION", "Uniquement les caisses sélectionnées")], initial="TOUTES", required=False)
    caisses = forms.MultipleChoiceField(label="Sélection de caisses", widget=Select2MultipleWidget(), choices=[], required=False)

    filtre_ecoles = forms.TypedChoiceField(label="Écoles", choices=[("TOUTES", "Toutes les écoles"), ("SELECTION", "Uniquement les écoles sélectionnées")], initial="TOUTES", required=False)
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
            ("individu_age", "Âge de l'individu"),
            ("individu_age_debut", "Âge au début de la période"),
            ("individu_tranche_age", "Tranche d'âge"),
            ("individu_secteur", "Secteur de l'individu"),
            ("individu_ville", "Ville de l'individu"),
            ("individu_ecole", "École de l'individu"),
            ("famille_nom_complet", "Noms des titulaires de la famille"),
            ("famille_qf", "Quotient familial de la famille"),
            ("famille_regime", "Régime social de la famille"),
        ]
        for categorie in ("individu", "famille"):
            for question in QuestionnaireQuestion.objects.filter(categorie=categorie, visible=True).order_by("ordre"):
                liste_choix.append(("question_%d" % question.pk, question.label))
        self.fields["tri"].choices = liste_choix
        self.fields["tri"].initial = "individu_nom_complet"

        # Colonnes
        self.fields['colonnes'].label = False
        self.fields['colonnes'].widget.request = self.request

        # Villes
        villes = list({individu.ville_resid: True for individu in Individu.objects.all()}.keys())
        self.fields["villes"].choices = sorted([(ville, ville) for ville in villes if ville])

        # Caisses
        self.fields["caisses"].choices = sorted([(caisse.pk, caisse.nom) for caisse in Caisse.objects.all().order_by("nom")])

        # Ecoles
        self.fields["ecoles"].choices = sorted([(ecole.pk, ecole.nom) for ecole in Ecole.objects.all().order_by("nom")])

        # Affichage
        self.helper.layout = Layout(
            HTML(EXTRA_CSS),
            Div(
                # Panneau des paramètres
                Div(
                    Div(
                        HTML("""<div class="card-header"><h3 class="card-title">Paramètres</h3></div>"""),
                        Div(
                            HTML("""<button type="submit" form="form_parametres" class="btn btn-primary btn-block btn-lg" name="type_submit" data-infobulle title="Calcule le tableau avec les paramètres et les colonnes choisis"><i class="fa fa-refresh margin-r-5"></i>Actualiser les résultats</button>
                                    <div id="parametres_modifies" class="text-muted small text-center mt-1" style="display:none;">Les paramètres ont changé depuis le dernier calcul</div>
                                    <div class="mt-3"></div>"""),
                            Field("profil"),
                            Accordeon(
                                Section("Généralités",
                                    Field("periode"),
                                    Field("activites"),
                                    Field("etats"),
                                    css_id="section_generalites",
                                ),
                                Section("Filtres",
                                    Field("filtre_villes"),
                                    Field("villes"),
                                    Field("filtre_caisses"),
                                    Field("caisses"),
                                    Field("filtre_ecoles"),
                                    Field("ecoles"),
                                    css_id="section_filtres",
                                ),
                                Section("Tri et impression",
                                    Field("titre"),
                                    Field("tri"),
                                    Field("ordre"),
                                    css_id="section_impression",
                                ),
                                css_id="accordeon_parametres",
                            ),
                            css_class="card-body",
                        ),
                        css_class="card card-default",
                    ),
                    css_class="col-lg-4 col-xl-3",
                ),
                # Colonnes et résultats
                Div(
                    Div(
                        Div(Field("colonnes"), css_class="card-body"),
                        css_class="card card-default",
                    ),
                    HTML(HTML_RESULTATS),
                    css_class="col-lg-8 col-xl-9",
                ),
                css_class="row",
            ),
            HTML(EXTRA_HTML),
        )


EXTRA_CSS = """
<style>
    #form_parametres .fixed-table-toolbar .bs-bars {margin-left:auto !important;}
    #badge_filtres {text-transform:none; vertical-align:middle;}
    .etat_vide {display:flex; flex-direction:column; align-items:center; text-align:center; gap:10px; padding:48px 24px;}
    .etat_vide_icone {width:64px; height:64px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:26px;
        background:color-mix(in srgb, var(--couleur-principale, #3c8dbc) 12%, #fff); color:var(--couleur-principale, #3c8dbc);}
    .etat_vide_titre {font-size:1.25rem; font-weight:700;}
    .etat_vide_texte {color:#6c757d; max-width:560px;}
    .etat_vide_resume {display:grid; grid-template-columns:auto 1fr; gap:4px 14px; margin:6px 0 4px 0; padding:12px 16px; text-align:left;
        border:1px solid rgba(0,0,0,.08); border-radius:8px; background:rgba(0,0,0,.02); max-width:560px;}
    .etat_vide_resume dt {font-weight:600; color:#6c757d;}
    .etat_vide_resume dd {margin:0;}
    .etat_vide_pistes {display:flex; flex-wrap:wrap; justify-content:center; gap:8px 18px; color:#495057; font-size:13px; margin-bottom:6px;}
    .etat_vide_etapes {display:flex; flex-wrap:wrap; justify-content:center; gap:10px 22px; list-style:none; padding:0; margin:6px 0 0 0; color:#495057; font-size:13px;}
    .etat_vide_etapes span {display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; margin-right:6px; border-radius:50%;
        background:var(--couleur-principale, #3c8dbc); color:#fff; font-weight:700; font-size:12px;}
    .dark-mode .etat_vide_icone {background:#24435a;}
    .dark-mode .etat_vide_resume {border-color:rgba(255,255,255,.1); background:rgba(255,255,255,.03);}
    .dark-mode .etat_vide_pistes, .dark-mode .etat_vide_etapes {color:#ced4da;}
    .kpi_etat_nomin {padding:12px 16px; height:100%;}
    .kpi_etat_nomin .kpi_label {font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.04em; color:#6c757d;}
    .kpi_etat_nomin .kpi_valeur {font-size:26px; font-weight:700; line-height:1.2;}
    .kpi_etat_nomin .kpi_detail {font-size:12px; color:#6c757d;}
    .dark-mode .case_regroupement {background-color:#3a4047;}
</style>
"""

EXTRA_HTML = """
<script>

    function get_parametres_profil() {
        return $("#form_parametres").serialize();
    };

    function appliquer_profil(idprofil) {
        $("#form_parametres").submit();
    };

    function maj_filtres() {
        var nbre_actifs = 0;
        $.each(["villes", "caisses", "ecoles"], function (index, nom) {
            var selection = $("#id_filtre_" + nom).val() === "SELECTION";
            $("#div_id_" + nom).toggle(selection);
            if (selection) {nbre_actifs += 1};
        });
        $("#badge_filtres").text(nbre_actifs ? nbre_actifs + " actif" + (nbre_actifs > 1 ? "s" : "") : "");
    };

    function ouvrir_generalites() {
        $("#section_generalites").collapse("show");
        $("html, body").animate({scrollTop: $("#accordeon_parametres").offset().top - 70}, 300);
    };

    // Infobulles : délégation pour couvrir aussi les éléments créés dynamiquement (pastilles, modale)
    $(document).tooltip({selector: "[data-infobulle]", container: "body", trigger: "hover", boundary: "window"});

    $(document).ready(function() {
        $("#entete_section_filtres a > span").first().append(' <span id="badge_filtres" class="badge badge-primary ml-1"></span>');
        $("#id_filtre_villes, #id_filtre_caisses, #id_filtre_ecoles").on("change", maj_filtres);
        maj_filtres();



        // Signale que les résultats affichés ne correspondent plus aux paramètres
        {% if afficher_resultats %}
            $("#form_parametres").on("change", ":input:not(#id_format_durees, #id_regroupement)", function () {
                $("#parametres_modifies").show();
            });
        {% endif %}
    });

</script>
"""

HTML_RESULTATS = """
{% load static %}
{% if afficher_resultats %}

    {% if erreurs_colonnes %}
        <div class="alert alert-warning" role="alert">
            <i class="fa fa-exclamation-triangle margin-r-5" aria-hidden="true"></i><b>Certaines colonnes calculées n'ont pas pu être calculées :</b>
            <ul class="mb-0 mt-1">{% for erreur in erreurs_colonnes %}<li>{{ erreur }}</li>{% endfor %}</ul>
        </div>
    {% endif %}

    {% if not liste_colonnes or not nbre_lignes %}
        <input type="hidden" name="format_durees" value="{{ form_parametres.format_durees.value|default:'horaire' }}">
        <input type="hidden" name="regroupement" value="{{ form_parametres.regroupement.value|default:'aucun' }}">
    {% endif %}

    {% if not liste_colonnes %}

        <div class="card card-default">
            <div class="card-body etat_vide">
                <div class="etat_vide_icone" aria-hidden="true"><i class="fa fa-columns"></i></div>
                <div class="etat_vide_titre">Aucune colonne à afficher</div>
                <div class="etat_vide_texte">Choisissez un modèle ou ajoutez des colonnes dans le cadre « Colonnes » ci-dessus, puis actualisez les résultats.</div>
            </div>
        </div>

    {% elif not nbre_lignes %}

        <div class="card card-default">
            <div class="card-body etat_vide">
                <div class="etat_vide_icone" aria-hidden="true"><i class="fa fa-search"></i></div>
                <div class="etat_vide_titre">Aucun individu ne correspond à ces paramètres</div>
                <div class="etat_vide_texte">Seuls les individus ayant au moins une consommation dans les états cochés, sur la période et les activités sélectionnées, apparaissent dans la liste.</div>
                <dl class="etat_vide_resume">
                    {% for label, valeur in resume_parametres %}
                        <dt>{{ label }}</dt><dd>{{ valeur }}</dd>
                    {% endfor %}
                </dl>
                <div class="etat_vide_pistes">
                    <span><i class="fa fa-calendar margin-r-5" aria-hidden="true"></i>Élargissez la période</span>
                    <span><i class="fa fa-check-square-o margin-r-5" aria-hidden="true"></i>Cochez d'autres états</span>
                    <span><i class="fa fa-filter margin-r-5" aria-hidden="true"></i>Vérifiez les filtres</span>
                </div>
                <button type="button" class="btn btn-default" onclick="ouvrir_generalites()" data-infobulle title="Afficher la rubrique Généralités du cadre Paramètres"><i class="fa fa-sliders margin-r-5" aria-hidden="true"></i>Modifier les paramètres</button>
            </div>
        </div>

    {% else %}

    <div class="row">
        {% for kpi in kpis %}
            <div class="col-6 col-xl-3 mb-3">
                <div class="card card-default mb-0 kpi_etat_nomin" data-infobulle title="{{ kpi.aide }}">
                    <div class="kpi_label">{{ kpi.label }}</div>
                    <div class="kpi_valeur">{{ kpi.valeur }}</div>
                    <div class="kpi_detail">{{ kpi.detail }}</div>
                </div>
            </div>
        {% endfor %}
    </div>

    <div class="card card-default">
        <div class="card-body">

            <div id="toolbar" class="form-inline">
                <label for="id_regroupement" class="mr-2 text-muted">Regrouper par</label>
                <select name="regroupement" id="id_regroupement" class="form-control form-control-sm mr-3" onchange="$('#form_parametres').append('<input type=hidden name=type_submit value=1>').submit();"
                        data-infobulle title="Regroupe les lignes avec un sous-total par groupe (relance le calcul)">
                    {% for valeur, label in form_parametres.fields.regroupement.choices %}
                        <option value="{{ valeur }}" {% if form_parametres.regroupement.value == valeur %}selected{% endif %}>{{ label }}</option>
                    {% endfor %}
                </select>
                <input type="hidden" name="format_durees" id="id_format_durees" value="{{ form_parametres.format_durees.value|default:'horaire' }}">
                <div class="btn-group btn-group-sm" role="group" aria-label="Format des durées">
                    <button type="button" class="btn btn-default" data-format="horaire" onclick="changer_format_durees('horaire')" data-infobulle title="Durées en heures et minutes (8h30)">8h30</button>
                    <button type="button" class="btn btn-default" data-format="decimal" onclick="changer_format_durees('decimal')" data-infobulle title="Durées en heures décimales (8,5), pratique pour un tableur">8,5</button>
                </div>
            </div>

            <script>
                var contenu_table = JSON.parse('{{ liste_lignes|escapejs }}');
                var colonnes_table = JSON.parse('{{ liste_colonnes_json|escapejs }}');
                var affiche_pagination = false;
                var format_durees = $("#id_format_durees").val();
            </script>

            <table id="table" class="table-sm table-xxs" {% if nbre_lignes > 20 %}data-height="700"{% endif %} data-show-footer="true" {% if est_regroupe %}data-tree-show-field="0"{% endif %}>
                <thead>
                    <tr>
                        {% for colonne in liste_colonnes %}
                            <th data-field="{{ colonne.index }}" data-halign="center" data-align="{% if colonne.type == 'texte' or colonne.type == 'date' %}left{% else %}right{% endif %}"
                                data-sortable="{% if est_regroupe %}false{% else %}true{% endif %}" data-formatter="formater_cellule" data-footer-formatter="calcule_total" data-cell-style="formater_case"
                                {% if colonne.description %}data-title-tooltip="{{ colonne.description }}"{% endif %}
                                {% if colonne.type == 'date' %}data-sorter="trier_dates"{% endif %}>{{ colonne.nom }}</th>
                        {% endfor %}
                    </tr>
                </thead>
            </table>

            <div class="text-muted small mt-2">Calculé le {{ date_calcul|date:"d/m/Y à H:i" }} · survolez un en-tête pour voir le détail de la colonne</div>

        </div>
    </div>

    {% endif %}

    <script>
        function get_colonne(field) {
            return colonnes_table.find(function (colonne) {return colonne.index === field});
        };

        function formater_duree(minutes) {
            if (minutes === null || minutes === undefined || minutes === "") {return ""};
            if (format_durees === "decimal") {
                return (Math.round(minutes / 60 * 100) / 100).toLocaleString("fr-FR");
            }
            var heures = Math.floor(minutes / 60);
            return heures + "h" + String(Math.round(minutes - heures * 60)).padStart(2, "0");
        };

        function formater_valeur(valeur, colonne) {
            if (valeur === null || valeur === undefined) {return ""};
            if (!colonne) {return valeur};
            if (colonne.type === "duree") {return formater_duree(valeur)};
            if (typeof valeur !== "number") {return valeur};
            if (colonne.type === "montant") {return valeur.toLocaleString("fr-FR", {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " €"};
            if (colonne.type === "pourcentage") {return valeur.toLocaleString("fr-FR", {maximumFractionDigits: 1}) + " %"};
            if (colonne.type === "nombre") {return valeur.toLocaleString("fr-FR", {maximumFractionDigits: 2})};
            return valeur;
        };

        function formater_cellule(valeur, ligne) {
            if (ligne.regroupement && this.field === "0") {return valeur};
            return formater_valeur(valeur, get_colonne(this.field));
        };

        function formater_case(valeur, ligne) {
            return ligne.regroupement === true ? {classes: "case_regroupement"} : {};
        };

        function trier_dates(a, b) {
            var convertir = function (date) {return date ? date.split("/").reverse().join("") : ""};
            return convertir(a).localeCompare(convertir(b));
        };

        function calcule_total(items) {
            {# Somme ou moyenne selon le type de colonne, lignes de regroupement exclues #}
            var colonne = get_colonne(this.field);
            var lignes = items.filter(function (item) {return !item.regroupement});
            if (this.field === "0") {return "Total · " + lignes.length + " ligne" + (lignes.length > 1 ? "s" : "")};
            if (!colonne || !colonne.total) {return ""};
            var valeurs = lignes.map(function (item) {return item[colonne.index]}).filter(function (valeur) {return typeof valeur === "number"});
            if (!valeurs.length) {return ""};
            var somme = valeurs.reduce(function (a, b) {return a + b}, 0);
            if (colonne.total === "moyenne") {
                var moyenne = somme / valeurs.length;
                return "moy. " + (colonne.type === "nombre" ? (Math.round(moyenne * 10) / 10).toLocaleString("fr-FR") : formater_valeur(moyenne, colonne));
            }
            return formater_valeur(Math.round(somme * 100) / 100, colonne);
        };

        function changer_format_durees(format) {
            format_durees = format;
            $("#id_format_durees").val(format);
            $("#toolbar [data-format]").each(function () {
                $(this).toggleClass("btn-primary", $(this).data("format") === format).toggleClass("btn-default", $(this).data("format") !== format);
            });
            if ($("#table").data("bootstrap.table")) {$("#table").bootstrapTable("load", contenu_table)};
        };

        $(document).ready(function () {
            if (typeof format_durees !== "undefined") {changer_format_durees(format_durees)};
        });
    </script>

{% else %}

    <div class="card card-default">
        <div class="card-body etat_vide">
            <div class="etat_vide_icone" aria-hidden="true"><i class="fa fa-table"></i></div>
            <div class="etat_vide_titre">Les résultats s'afficheront ici</div>
            <div class="etat_vide_texte">Choisissez une période, des activités et des colonnes, puis cliquez sur <b>Actualiser les résultats</b>.</div>
            <ol class="etat_vide_etapes">
                <li><span>1</span>Période et activités</li>
                <li><span>2</span>Colonnes ou modèle</li>
                <li><span>3</span>Actualiser</li>
            </ol>
        </div>
    </div>
    <input type="hidden" name="format_durees" value="{{ form_parametres.format_durees.value|default:'horaire' }}">
    <input type="hidden" name="regroupement" value="{{ form_parametres.regroupement.value|default:'aucun' }}">

{% endif %}
"""
