# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from django_select2.forms import Select2Widget, Select2MultipleWidget
from core.widgets import Profil_configuration, DatePickerWidget, Select_activite
from core.models import Parametre, Activite, Groupe
from core.utils.utils_commandes import Commandes
from core.forms.base import FormulaireBase
from individus.widgets import ColonnesInscritsWidget


class Formulaire(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil", queryset=Parametre.objects.none(), widget=Profil_configuration({"categorie": "imprimer_liste_inscrits", "module": "individus.views.imprimer_liste_inscrits"}), required=False)
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)
    groupes = forms.ModelMultipleChoiceField(label="Groupes", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%", "data-placeholder": "Tous les groupes"}), queryset=Groupe.objects.none(), required=False,
                                             help_text="Laissez vide pour inclure tous les groupes de l'activité.")
    date_situation = forms.DateField(label="Date de situation", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=True)
    colonnes_perso = forms.CharField(label="Colonnes", required=False, widget=ColonnesInscritsWidget())
    orientation = forms.ChoiceField(label="Orientation de la page", choices=[("portrait", "Portrait"), ("paysage", "Paysage")], initial="portrait", required=False)

    def __init__(self, *args, **kwargs):
        if kwargs.get("data", None):
            kwargs["data"]["date_situation"] = str(datetime.date.today())
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Profil
        conditions = Q(categorie="imprimer_liste_inscrits")
        conditions &= (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True))
        conditions &= (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        self.fields['profil'].queryset = Parametre.objects.filter(conditions).order_by("nom")
        self.fields["profil"].widget.request = self.request

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request
        self.fields["date_situation"].initial = datetime.date.today()

        # Groupes de l'activité sélectionnée
        idactivite = None
        if self.data:
            idactivite = self.data.get("activite", None)
        elif self.initial.get("activite"):
            idactivite = self.initial["activite"]
        try:
            idactivite = int(idactivite)
        except (TypeError, ValueError):
            idactivite = None
        if idactivite:
            self.fields["groupes"].queryset = Groupe.objects.filter(activite_id=idactivite, activite__structure__in=self.request.user.structures.all()).order_by("ordre")

        # Colonnes
        self.fields["colonnes_perso"].initial = json.dumps([{'nom': 'Nom', 'code': 'nom', 'largeur': 'automatique'}, {'nom': 'Prénom', 'code': 'prenom', 'largeur': 'automatique'}])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'consommations_toc' %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""
                        <div class="btn-group">
                            <a type='button' class="btn btn-primary" onclick="generer_pdf()" title="Générer le PDF"><i class='fa fa-file-pdf-o margin-r-5'></i> Générer le PDF</a>
                            <button type="button" class="btn btn-primary dropdown-toggle dropdown-icon" data-toggle="dropdown">
                                <span class="sr-only">Ouvrir le menu</span>
                            </button>
                            <div class="dropdown-menu" role="menu">
                                <a type='button' class="btn" onclick="generer_pdf(telechargement=true)" title="Télécharger le PDF"><i class='fa fa-download'></i> Télécharger le PDF</a>
                            </div>
                        </div>
                    """)
                ],
                    autres_commandes=[HTML("""<a type='button' class="btn btn-default" onclick="exporter_excel()" title="Exporter vers Excel"><i class='fa fa-file-excel-o margin-r-5'></i> Exporter vers Excel</a> """)],
                ),
            Field("profil"),
            Fieldset("Sélection de l'activité",
                Field("activite"),
                Field("groupes"),
                Field("date_situation"),
            ),
            Fieldset("Colonnes",
                Field("colonnes_perso"),
            ),
            Fieldset("Options",
                Field("orientation"),
            ),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        self.cleaned_data["colonnes_perso"] = json.loads(self.cleaned_data["colonnes_perso"])
        return self.cleaned_data

EXTRA_HTML = """
<script>
    
    // Actualise la liste des groupes en fonction de l'activité sélectionnée
    function On_change_activite() {
        var selection = $("#id_groupes").val() || [];
        $.ajax({
            type: "POST",
            url: "{% url 'ajax_imprimer_liste_inscrits_get_groupes' %}",
            data: {"idactivite": $("#id_activite").val(), "csrfmiddlewaretoken": "{{ csrf_token }}"},
            datatype: "json",
            success: function(data) {
                var $select = $("#id_groupes");
                $select.empty();
                $.each(data.groupes, function(index, groupe) {
                    var selected = selection.indexOf(String(groupe.id)) !== -1;
                    $select.append(new Option(groupe.nom, groupe.id, selected, selected));
                });
                $select.trigger("change");
            }
        });
    };

    $(document).ready(function() {
        $("#id_activite").on("change", On_change_activite);
    });

    function get_parametres_profil() {
        return $("#form_parametres").serialize();
    };
    
    function appliquer_profil(idprofil) {
        $("#form_parametres").submit();
    };

</script>
"""
