# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field, TabHolder, Tab, InlineRadios
from core.widgets import SelectionActivitesWidget, ColorPickerWidget, Profil_configuration
from consommations.widgets import SelectionGroupesWidget, SelectionUnitesWidget, ColonnesPersoWidget, SelectionEcolesWidget, SelectionClassesWidget, SelectionEvenementsWidget
from core.models import Parametre, Unite
from core.utils.utils_commandes import Commandes
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil de configuration", queryset=Parametre.objects.none(), widget=Profil_configuration({"categorie": "edition_liste_conso", "module": "consommations.views.edition_liste_conso"}), required=False)

    # Activités
    groupes = forms.CharField(label="Activités", required=False, widget=SelectionGroupesWidget(attrs={"coche_tout": False}))
    regroupement_groupe = forms.BooleanField(label="Regrouper par groupe", required=False, initial=True)
    saut_page_activites = forms.BooleanField(label="Insérer un saut de page après chaque activité", required=False, initial=True)
    saut_page_groupes = forms.BooleanField(label="Insérer un saut de page après chaque groupe", required=False, initial=True)

    # Scolarité
    regroupement_scolarite = forms.ChoiceField(label="Regroupement", widget=forms.RadioSelect, choices=[("aucun", "Aucun regroupement"), ("ecoles", "Regrouper par école"), ("classes", "Regrouper par classe")], initial="aucun", required=False)
    ecoles = forms.CharField(label="Ecoles", required=False, widget=SelectionEcolesWidget(attrs={"coche_tout": True}))
    classes = forms.CharField(label="Classes", required=False, widget=SelectionClassesWidget(attrs={"coche_tout": True}))
    afficher_scolarite_inconnue = forms.BooleanField(label="Inclure les individus dont la scolarité est inconnue", required=False, initial=True)
    saut_page_ecoles = forms.BooleanField(label="Insérer un saut de page après chaque école", required=False, initial=True)
    saut_page_classes = forms.BooleanField(label="Insérer un saut de page après chaque classe", required=False, initial=True)

    # Evénements
    regroupement_evenements = forms.BooleanField(label="Regrouper par événement", required=False, initial=False)
    evenements = forms.CharField(label="Evénements", required=False, widget=SelectionEvenementsWidget(attrs={"coche_tout": True}))
    saut_page_evenements = forms.BooleanField(label="Insérer un saut de page après chaque événement", required=False, initial=True)

    # Unités
    unites = forms.CharField(label="Unités", required=False, widget=SelectionUnitesWidget())

    # Colonnes personnalisées
    colonnes_perso = forms.CharField(label="Colonnes personnalisées", required=False, widget=ColonnesPersoWidget())

    # Options
    orientation = forms.ChoiceField(label="Orientation de la page", choices=[("automatique", "Automatique"), ("portrait", "Portrait"), ("paysage", "Paysage")], initial="automatique", required=False)
    tri = forms.ChoiceField(label="Tri", choices=[("nom", "Nom"), ("prenom", "Prénom"), ("age", "Âge")], initial="nom", required=False)
    ordre = forms.ChoiceField(label="Ordre", choices=[("croissant", "Croissant"), ("decroissant", "Décroissant")], initial="croissant", required=False)
    nbre_lignes_vierges = forms.IntegerField(label="Lignes vierges", initial=3, min_value=0, required=True)
    afficher_inscrits = forms.BooleanField(label="Afficher tous les inscrits", initial=False, required=False)
    masquer_presents = forms.BooleanField(label="Masquer les présents", initial=False, required=False)
    liste_choix_hauteur = [("automatique", "Automatique")] + [(str(x), "%d pixels" % x) for x in range(5, 205, 5)]
    hauteur_ligne_individu = forms.ChoiceField(label="Hauteur de la ligne Individu", choices=liste_choix_hauteur, initial="automatique", required=False)
    couleur_fond_titre = forms.CharField(label="Couleur ligne de titre", required=True, widget=ColorPickerWidget(), initial="#D0D0D0")
    couleur_fond_entetes = forms.CharField(label="Couleur ligne des entêtes", required=True, widget=ColorPickerWidget(), initial="#F0F0F0")
    couleur_fond_total = forms.CharField(label="Couleur ligne de total", required=True, widget=ColorPickerWidget(), initial="#D0D0D0")
    activite_taille_nom = forms.IntegerField(label="Taille de police du nom d'activité", initial=5, min_value=3, required=True)
    afficher_photos = forms.ChoiceField(label="Afficher les photos", choices=[("non", "Non"), ("petite", "Petite taille"), ("moyenne", "Moyenne taille"), ("grande", "Grande taille")], initial="non", required=False)
    liste_choix_largeur = [("automatique", "Automatique")] + [(str(x), "%d pixels" % x) for x in range(5, 305, 5)]
    largeur_colonne_nom = forms.ChoiceField(label="Largeur de la colonne", choices=liste_choix_largeur, initial="automatique", required=False)
    afficher_age = forms.BooleanField(label="Afficher la colonne", initial=True, required=False)
    liste_choix_largeur = [("automatique", "Automatique")] + [(str(x), "%d pixels" % x) for x in range(5, 305, 5)]
    largeur_colonne_age = forms.ChoiceField(label="Largeur de la colonne", choices=liste_choix_largeur, initial="automatique", required=False)
    afficher_evenements = forms.BooleanField(label="Afficher les évènements", initial=False, required=False)
    masquer_consommations = forms.BooleanField(label="Masquer les consommations", initial=False, required=False)
    masquer_horaires = forms.BooleanField(label="Masquer les horaires et les quantités", initial=False, required=False)
    afficher_tous_etats = forms.BooleanField(label="Inclure tous les états de consommations", initial=False, required=False)
    liste_choix_largeur = [("automatique", "Automatique")] + [(str(x), "%d pixels" % x) for x in range(5, 105, 5)]
    largeur_colonne_unite = forms.ChoiceField(label="Largeur de la colonne", choices=liste_choix_largeur, initial="automatique", required=False)
    liste_choix_largeur = [(str(x), "%d pixels" % x) for x in range(5, 105, 5)]
    largeur_colonne_perso = forms.ChoiceField(label="Largeur par défaut des colonnes", choices=liste_choix_largeur, initial="40", required=False)
    afficher_informations = forms.BooleanField(label="Afficher la colonne", initial=True, required=False)
    masquer_informations = forms.BooleanField(label="Masquer les informations", initial=False, required=False)
    afficher_regimes_alimentaires = forms.BooleanField(label="Afficher les régimes alimentaires", initial=True, required=False)
    afficher_recapitulatif = forms.BooleanField(label="Afficher le récapitulatif des informations individuelles", initial=True, required=False)
    afficher_cotisations_manquantes = forms.BooleanField(label="Afficher les cotisations manquantes", initial=False, required=False)
    afficher_pieces_manquantes = forms.BooleanField(label="Afficher les pièces manquantes", initial=False, required=False)
    liste_choix_largeur = [("automatique", "Automatique")] + [(str(x), "%d pixels" % x) for x in range(5, 505, 5)]
    largeur_colonne_informations = forms.ChoiceField(label="Largeur de la colonne", choices=liste_choix_largeur, initial="automatique", required=False)


    def __init__(self, *args, **kwargs):
        dates = kwargs.pop("dates", [])
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Pour permettre la récupération de forms multiples
        self.helper.form_tag = False

        # Profil
        conditions = Q(categorie="edition_liste_conso")
        conditions &= (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True))
        conditions &= (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        self.fields['profil'].queryset = Parametre.objects.filter(conditions).order_by("nom")
        self.fields["profil"].widget.request = self.request
        self.fields['profil'].label = False

        # Groupes
        self.fields['groupes'].label = False
        self.fields['groupes'].widget.attrs.update({'dates': dates})
        self.fields["groupes"].widget.request = self.request

        # Scolarité
        self.fields['regroupement_scolarite'].label = False
        self.fields['ecoles'].label = False
        self.fields['classes'].label = False
        self.fields['classes'].widget.attrs.update({'dates': dates})

        # Evénements
        self.fields['evenements'].label = False
        self.fields['evenements'].widget.attrs.update({'dates': dates})

        # Unités
        self.fields['unites'].label = False
        self.fields['unites'].widget.attrs.update({'dates': dates})
        self.fields["unites"].widget.request = self.request

        # Colonnes personnalisées
        self.fields['colonnes_perso'].label = False

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'consommations_toc' %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""
                        <div class="btn-group margin-r-3">
                            <a type='button' class="btn btn-primary" onclick="generer_pdf()" title="Générer le PDF"><i class='fa fa-file-pdf-o margin-r-5'></i> Générer le PDF</a>
                            <button type="button" class="btn btn-primary dropdown-toggle dropdown-icon" data-toggle="dropdown">
                                <span class="sr-only">Ouvrir le menu</span>
                            </button>
                            <div class="dropdown-menu" role="menu">
                                <a type='button' class="btn" onclick="generer_pdf(telechargement=true)" title="Télécharger le PDF"><i class='fa fa-download margin-r-5'></i> Télécharger le PDF</a>
                            </div>
                        </div>
                    """),
                    HTML("""<a type='button' class="btn btn-default" onclick="exporter_excel()" title="Exporter vers Excel"><i class='fa fa-file-excel-o margin-r-5'></i> Exporter vers Excel</a> """)
                ],
            ),
            Field('profil'),
            TabHolder(
                Tab("Activités",
                    Field('groupes'),
                    Field('regroupement_groupe'),
                    Field('saut_page_activites'),
                    Field('saut_page_groupes'),
                    ),
                Tab("Scolarité",
                    InlineRadios('regroupement_scolarite'),
                    Field('ecoles'),
                    Field('classes'),
                    Field('afficher_scolarite_inconnue'),
                    Field('saut_page_ecoles'),
                    Field('saut_page_classes'),
                    ),
                Tab("Evénements",
                    Field('regroupement_evenements'),
                    Field('evenements'),
                    Field('saut_page_evenements'),
                    ),
                Tab("Unités",
                    Field('unites'),
                    ),
                Tab("Colonnes perso.",
                    Field('colonnes_perso'),
                    ),
                Tab("Options",
                    Fieldset("Page",
                        Field('orientation'),
                    ),
                    Fieldset("Lignes",
                        Field('tri'),
                        Field('ordre'),
                        Field('nbre_lignes_vierges'),
                        Field('afficher_inscrits'),
                        Field('masquer_presents'),
                        Field('hauteur_ligne_individu'),
                        Field('couleur_fond_titre'),
                        Field('couleur_fond_entetes'),
                        Field('couleur_fond_total'),
                        Field('activite_taille_nom'),
                    ),
                    Fieldset("Photos",
                        Field('afficher_photos'),
                    ),
                    Fieldset("Colonne Individu",
                        Field('largeur_colonne_nom'),
                    ),
                    Fieldset("Colonne Âge",
                        Field('afficher_age'),
                        Field('largeur_colonne_age'),
                    ),
                    Fieldset("Colonnes des unités",
                        Field('afficher_evenements'),
                        Field('masquer_consommations'),
                        Field('masquer_horaires'),
                        Field('afficher_tous_etats'),
                        Field('largeur_colonne_unite'),
                    ),
                    Fieldset("Colonnes personnalisées",
                        Field('largeur_colonne_perso'),
                    ),
                    Fieldset("Colonne Informations",
                        Field('afficher_informations'),
                        Field('masquer_informations'),
                        Field('afficher_regimes_alimentaires'),
                        Field('afficher_recapitulatif'),
                        Field('afficher_cotisations_manquantes'),
                        Field('afficher_pieces_manquantes'),
                        Field('largeur_colonne_informations'),
                    ),
                ),
            ),
            HTML(EXTRA_HTML),
        )

    # def clean(self):
    #     if not self.cleaned_data.get("groupes"):
    #         self.add_error('groupes', "Vous devez cocher au moins un groupe dans l'onglet Activités")
    #         return
    #
    #     return self.cleaned_data


EXTRA_HTML = """
<script>
    
    // Regroupement scolarite
    function On_change_regroupement_scolarite() {
        $('#div_id_ecoles').hide();
        $('#div_id_classes').hide();
        $('#div_id_afficher_scolarite_inconnue').hide();
        $('#div_id_saut_page_ecoles').hide();
        $('#div_id_saut_page_classes').hide();
        var mode_scolarite = $("input[name=regroupement_scolarite]:checked").val();
        if (mode_scolarite === "ecoles") {
            $('#div_id_afficher_scolarite_inconnue').show();
            $('#div_id_saut_page_ecoles').show();
            $('#div_id_ecoles').show();
        };
        if (mode_scolarite === "classes") {
            $('#div_id_afficher_scolarite_inconnue').show();
            $('#div_id_classes').show();
            $('#div_id_saut_page_ecoles').show();
            $('#div_id_saut_page_classes').show();
        };
    }
    $(document).ready(function() {
        $('input[type=radio][name=regroupement_scolarite]').on('change', On_change_regroupement_scolarite);
        On_change_regroupement_scolarite.call($('input[type=radio][name=regroupement_scolarite]').get(0));
    });


    // Regroupement événements
    function On_change_regroupement_evenements() {
        $('#div_id_evenements').hide();
        $('#div_id_saut_page_evenements').hide();
        if ($(this).prop("checked")) {
            $('#div_id_evenements').show();
            $('#div_id_saut_page_evenements').show();
        };
    }
    $(document).ready(function() {
        $('#id_regroupement_evenements').on('change', On_change_regroupement_evenements);
        On_change_regroupement_evenements.call($('#id_regroupement_evenements').get(0));
    });

    function get_parametres_profil() {
        return $("#form_general").serialize();
    };
    
    function appliquer_profil(idprofil) {
        $("#form_general").submit();
    };

</script>
"""