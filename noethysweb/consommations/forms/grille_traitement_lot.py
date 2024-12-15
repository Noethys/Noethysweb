# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, ButtonHolder, Hidden
from crispy_forms.bootstrap import Field, InlineCheckboxes, Div
from core.widgets import DatePickerWidget
from core.models import JOURS_SEMAINE
from core.forms.base import FormulaireBase
from core.utils.utils_texte import Creation_tout_cocher


class Formulaire(FormulaireBase, forms.Form):
    # Action
    choix_action = [("SAISIE", "Ajouter"), ("EFFACER", "Supprimer")]
    action_type = forms.TypedChoiceField(label="Action à réaliser", choices=choix_action, initial='SAISIE', required=False)

    # Période
    date_debut = forms.DateField(label="Du", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    date_fin = forms.DateField(label="Au", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    inclure_feries = forms.BooleanField(label="Inclure les fériés", required=False)

    # Jours
    jours_scolaires = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_scolaires"))
    jours_vacances = forms.MultipleChoiceField(label="Jours de vacances", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_vacances"))
    choix_frequence = [(1, "Toutes les semaines"), (2, "Une semaine sur deux"),
                        (3, "Une semaine sur trois"), (4, "Une semaine sur quatre"),
                        (5, "Les semaines paires"), (6, "Les semaines impaires")]
    frequence_type = forms.TypedChoiceField(label="Fréquence", choices=choix_frequence, initial=1, required=False)

    # Pour le traitement par lot global
    individus_coches = forms.CharField(label="Individus_coches", required=False)
    idactivite = forms.CharField(label="idactivite", required=False)

    def __init__(self, *args, **kwargs):
        mode = kwargs.pop("mode", "grille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'grille_traitement_lot'
        self.helper.form_method = 'post'

        self.fields["jours_scolaires"].initial = [0, 1, 2, 3, 4]
        self.fields["jours_vacances"].initial = [0, 1, 2, 3, 4]

        self.helper.layout = Layout(
            Div(
                Field('action_type', id="traitement_lot_action", wrapper_class="col-md-4"),
                Field('date_debut', id="traitement_lot_debut", wrapper_class="col-md-4"),
                Field('date_fin', id="traitement_lot_fin", wrapper_class="col-md-4"),
                css_class="form-row",
            ),
            Div(
                InlineCheckboxes("jours_scolaires", id="traitement_lot_scolaires", wrapper_class="col-md-6"),
                InlineCheckboxes("jours_vacances", id="traitement_lot_vacances", wrapper_class="col-md-6"),
                css_class="form-row",
            ),
            Field("frequence_type", id="traitement_lot_frequence"),
            Field("inclure_feries", id="traitement_lot_feries"),
            HTML(EXTRA_HTML),
            Hidden("individus_coches", ""),
            Hidden("idactivite", ""),
        )

        # Si mode grille, ajout des boutons de commande
        if mode == "grille":
            self.helper.layout.append(
                ButtonHolder(
                    Div(
                        Submit('submit', 'Valider', css_class='btn-primary'),
                        HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                        css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"),
                ),
            )

        if mode == "consommations_traitement_lot":
            self.helper.layout.insert(0, Fieldset("Paramètres"))
            self.helper.layout.append(Fieldset("Sélection des individus concernés"))

    def clean(self):
        # Période d'application
        if self.cleaned_data["date_debut"] == None:
            self.add_error('date_debut', "Vous devez sélectionner une date de début")
            return
        if self.cleaned_data["date_fin"] == None:
            self.add_error('date_fin', "Vous devez sélectionner une date de fin")
            return
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"] :
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return

        return self.cleaned_data

EXTRA_HTML = """
<label for="div_table_traitement_lot" class="col-form-label">Unités</label>

<div id="div_table_traitement_lot">
    <table cellspacing="0" id="table_traitement_lot" class="table table-bordered">
        {% for unite in data.liste_unites %}
            <tr>
                <td style="padding: 6px !important;">
                <div class="form-inline">
                
                    {% if unite.type|is_in_list:"Multihoraires;Evenement" %}
                        <input type="checkbox" value="0" disabled/>
                        <span style="margin-right:20px;padding-left: 5px;color: #dbdbdb;">{{ unite.nom }} (Unité incompatible avec le traitement par lot)</span>
                        
                    {% else %}
                        <input name="unite_{{ unite.pk }}" type="checkbox" value="0"/>
                        <span style="margin-right:20px;padding-left: 5px;">{{ unite.nom }}</span>

                        {% if unite.type == "Quantite" %}
                            
                            <div class="input-group input-group-sm">
                                <div class="input-group-prepend">
                                    <span class="input-group-text">Quantité</span>
                                </div>
                                <input name="unite_{{ unite.pk }}_quantite" type="number" class="numberinput form-control" min="1" value="1" style="width: 100px;">
                            </div>

                        {% endif %}

                        {% if unite.type == "Horaire" %}
                        
                            <div class="input-group input-group-sm">
                                <div class="input-group-prepend">
                                    <span class="input-group-text">Début</span>
                                </div>
                                <input name="unite_{{ unite.pk }}_debut" type="time" value="{{ unite.heure_debut }}" class="form-control"/>
                            </div>
                            
                            <div class="input-group input-group-sm ml-2">
                                <div class="input-group-prepend">
                                    <span class="input-group-text">Fin</span>
                                </div>
                                <input name="unite_{{ unite.pk }}_fin" type="time" value="{{ unite.heure_fin }}" class="form-control"/>
                            </div>

                        {% endif %}
                    
                    {% endif %}

                </div>
                </td>
            </tr>
        {% endfor %}
    </table>
</div>

"""