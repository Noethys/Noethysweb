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
from django_select2.forms import Select2Widget
from core.widgets import Profil_configuration, DatePickerWidget, Select_activite
from core.models import Parametre, Activite
from core.utils.utils_commandes import Commandes
from core.forms.base import FormulaireBase
from individus.widgets import ColonnesInscritsWidget


class Formulaire(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil", queryset=Parametre.objects.none(), widget=Profil_configuration({"categorie": "imprimer_liste_inscrits", "module": "individus.views.imprimer_liste_inscrits"}), required=False)
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)
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

        # Colonnes
        self.fields["colonnes_perso"].initial = json.dumps([{'nom': 'Nom', 'code': 'nom', 'largeur': 'automatique'}, {'nom': 'Prénom', 'code': 'prenom', 'largeur': 'automatique'}])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'consommations_toc' %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""
                        <div class="btn-group margin-r-5">
                            <a type='button' class="btn btn-primary" onclick="generer_pdf()" title="Générer le PDF"><i class='fa fa-file-pdf-o margin-r-5'></i> Générer le PDF</a>
                            <button type="button" class="btn btn-primary dropdown-toggle dropdown-icon" data-toggle="dropdown">
                                <span class="sr-only">Ouvrir le menu</span>
                            </button>
                            <div class="dropdown-menu" role="menu">
                                <a type='button' class="btn" onclick="generer_pdf(telechargement=true)" title="Télécharger le PDF"><i class='fa fa-download margin-r-5'></i> Télécharger le PDF</a>
                            </div>
                        </div>
                    """)
                ]
            ),
            Field("profil"),
            Fieldset("Sélection de l'activité",
                Field("activite"),
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
    
    function get_parametres_profil() {
        return $("#form_parametres").serialize();
    };
    
    function appliquer_profil(idprofil) {
        $("#form_parametres").submit();
    };

</script>
"""
