# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Famille, Piece, TypePiece, Rattachement, Individu
from core.widgets import DatePickerWidget
from core.utils import utils_dates
from individus.utils import utils_pieces_manquantes


class Formulaire(FormulaireBase, ModelForm):
    # Type de pièce
    mode_piece = forms.ChoiceField(label="Type de pièce", choices=[("AFOURNIR", "Une pièce à fournir"), ("TOUTES", "Une pièce prédéfinie"), ("AUTRE", "Autre type de pièce")], initial="AFOURNIR", required=False)
    pieces_fournir = forms.TypedChoiceField(label="Choix de la pièce", choices=[], required=False, help_text="Sélectionnez un type de pièce dans la liste.")
    pieces_toutes = forms.TypedChoiceField(label="Choix de la pièce", choices=[], required=False, help_text="Sélectionnez un type de pièce dans la liste.")
    choix_individu = forms.TypedChoiceField(label="Individu associé", choices=[], required=False, help_text="Sélectionnez le nom de l'individu concerné ou la famille.")

    # Période de validité
    choix_validite = [("ILLIMITEE", "Durée illimitée"), ("LIMITEE", "Durée limitée")]
    validite_type = forms.TypedChoiceField(label="Validité", choices=choix_validite, initial='ILLIMITEE', required=False)
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget())

    class Meta:
        model = Piece
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "titre": "Vous devez obligatoirement saisir un titre pour cette pièce.",
            "document": "Vous pouvez ajouter un document numérisé au format PDF ou image.",
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_pieces_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Définit la famille associée
        famille = Famille.objects.get(pk=idfamille)

        # Pièces à fournir
        self.liste_pieces_fournir = utils_pieces_manquantes.Get_pieces_manquantes(famille=famille)
        self.fields['pieces_fournir'].choices = [(index, piece["label"]) for index, piece in enumerate(self.liste_pieces_fournir)]
        self.fields['pieces_fournir'].choices.insert(0, (None, ""))
        self.fields['pieces_fournir'].initial = None

        # Toutes les pièces possibles
        rattachements = Rattachement.objects.select_related("individu").filter(famille=famille).order_by("categorie")
        self.liste_pieces_toutes = []
        for type_piece in TypePiece.objects.all().order_by("nom"):
            if type_piece.public == "famille":
                self.liste_pieces_toutes.append({"label": type_piece.Get_nom(), "type_piece": type_piece})
            if type_piece.public == "individu":
                for rattachement in rattachements:
                    self.liste_pieces_toutes.append({"label": type_piece.Get_nom(rattachement.individu), "type_piece": type_piece, "individu": rattachement.individu})
        self.fields['pieces_toutes'].choices = [(index, piece["label"]) for index, piece in enumerate(self.liste_pieces_toutes)]
        self.fields['pieces_toutes'].choices.insert(0, (None, ""))
        self.fields['pieces_toutes'].initial = None

        # Auteur
        if not self.instance.pk:
            self.fields["auteur"].initial = self.request.user

        # Importation de la pièce
        if self.instance.idpiece != None:
            # Recherche si la pièce est présente dans les pièces à fournir
            found = False
            for index, piece in enumerate(self.liste_pieces_fournir):
                if piece["type_piece"] == self.instance.type_piece and piece.get("individu", None) == self.instance.individu:
                    self.fields['mode_piece'].initial = "AFOURNIR"
                    self.fields['pieces_fournir'].initial = index
                    found = True

            # Recherche si la pièce est présente dans les pièces à fournir
            if not found:
                for index, piece in enumerate(self.liste_pieces_toutes):
                    if piece["type_piece"] == self.instance.type_piece and piece.get("individu", None) == self.instance.individu:
                        self.fields['mode_piece'].initial = "TOUTES"
                        self.fields['pieces_toutes'].initial = index

            # Recherche s'il s'agit d'une pièce libre
            if not self.instance.type_piece:
                self.fields['mode_piece'].initial = "AUTRE"
                self.fields['choix_individu'].initial = self.instance.individu_id

        # Récupération du mode de pièce (si rechargement de la page)
        if "data" in kwargs:
            self.fields['mode_piece'].initial = kwargs["data"].get("mode_piece", "AFOURNIR")

        # Création de la liste des types de pièces pour javascript
        dict_validite = {
            "AFOURNIR": [utils_dates.ConvertDateToFR(piece["type_piece"].Get_date_fin_validite()) for index, piece in enumerate(self.liste_pieces_fournir)],
            "TOUTES": [utils_dates.ConvertDateToFR(piece["type_piece"].Get_date_fin_validite()) for index, piece in enumerate(self.liste_pieces_toutes)],
        }
        dict_validite = json.dumps(dict_validite)

        # Choix de l'individu
        self.fields['choix_individu'].choices = [(None, "La famille")] + [(rattachement.individu_id, rattachement.individu.Get_nom()) for rattachement in rattachements]

        # Date de début
        if self.instance.idpiece == None:
            self.fields['date_debut'].initial = datetime.date.today()

        # Importe la durée de validité
        if self.instance.date_fin in (None, datetime.date(2999, 1, 1)):
            self.fields['validite_type'].initial = "ILLIMITEE"
            self.fields['date_fin'].initial = None
        else:
            self.fields['validite_type'].initial = "LIMITEE"
            self.fields['date_debut'].initial = self.instance.date_debut
            self.fields['date_fin'].initial = self.instance.date_fin

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('famille', value=idfamille),
            Field("auteur", type="hidden"),
            Fieldset("Type de pièce",
                Field('mode_piece'),
                Field('pieces_fournir'),
                Field('pieces_toutes'),
                Field('titre'),
                Field('choix_individu'),
            ),
            Fieldset("Période de validité",
                Field('date_debut'),
                Field("validite_type"),
                Field('date_fin'),
            ),
            Fieldset("Document numérisé",
                Field('document'),
            ),
            Fieldset("Divers",
                Field('observations'),
            ),
            HTML("<script>var dict_validite=%s</script>" % dict_validite),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Type de pièce
        if self.cleaned_data["mode_piece"] == "AFOURNIR":
            if self.cleaned_data["pieces_fournir"] in ("", None):
                self.add_error('pieces_fournir', "Vous devez sélectionner une pièce dans la liste proposée.")
                return
            piece = self.liste_pieces_fournir[int(self.cleaned_data["pieces_fournir"])]

        if self.cleaned_data["mode_piece"] == "TOUTES":
            if self.cleaned_data["pieces_toutes"] in ("", None):
                self.add_error('pieces_toutes', "Vous devez sélectionner une pièce dans la liste proposée.")
                return
            piece = self.liste_pieces_toutes[int(self.cleaned_data["pieces_toutes"])]

        if self.cleaned_data["mode_piece"] == "AUTRE":
            if self.cleaned_data["titre"] in ("", None):
                self.add_error('titre', "Vous devez saisir un titre pour cette pièce.")
                return
            piece = None

        self.cleaned_data["type_piece"] = piece["type_piece"] if piece else None

        # Individu
        if piece:
            # Si pièce prédéfinie
            self.cleaned_data["individu"] = None if piece["type_piece"].public == "famille" else piece["individu"]
        else:
            # Si pièce libre
            self.cleaned_data["individu"] = Individu.objects.get(pk=self.cleaned_data["choix_individu"]) if self.cleaned_data["choix_individu"] else None

        # Famille
        if piece and piece["type_piece"].public == "individu" and piece["type_piece"].valide_rattachement:
            self.cleaned_data["famille"] = None

        # Durée de validité
        if self.cleaned_data["validite_type"] == "LIMITEE":
            if self.cleaned_data["date_fin"] == None:
                self.add_error('date_fin', "Vous devez sélectionner une date de fin")
                return
            if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"] :
                self.add_error('date_debut', "La date de fin doit être supérieure à la date de début")
                return
        else:
            self.cleaned_data["date_fin"] = datetime.date(2999, 1, 1)

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// validite_type
function On_change_validite_type() {
    $('#div_id_date_fin').hide();
    if ($('#id_validite_type').val() == 'LIMITEE') {
        $('#div_id_date_fin').show();
    }
}
$(document).ready(function() {
    $('#id_validite_type').change(On_change_validite_type);
    On_change_validite_type.call($('#id_validite_type').get(0));
});

// mode_piece
function On_change_mode_piece(event) {
    $('#div_id_pieces_fournir').hide();
    $('#div_id_pieces_toutes').hide();
    $('#div_id_titre').hide();
    $('#div_id_choix_individu').hide();
    if (this.value == 'AFOURNIR') {
        $('#div_id_pieces_fournir').show();
    };
    if (this.value == 'TOUTES') {
        $('#div_id_pieces_toutes').show();
    };
    if (this.value == 'AUTRE') {
        $('#div_id_titre').show();
        $('#div_id_choix_individu').show();
    };
}
$(document).ready(function() {
    $('#id_mode_piece').change(On_change_mode_piece);
    On_change_mode_piece.call($('#id_mode_piece').get(0));
});

// piece
function On_change_piece() {
    index = $(this).val();
    if (this.id == 'id_pieces_fournir') {
        date_fin = dict_validite.AFOURNIR[index];
    } else {
        date_fin = dict_validite.TOUTES[index];
    };
    if ((date_fin == null) || (date_fin == "01/01/2999")) {
        $('#id_validite_type').val('ILLIMITEE');
        $('#id_date_fin').datepicker("setDate", null);
    } else {
        $('#id_validite_type').val('LIMITEE');
        $('#id_date_fin').datepicker("setDate", date_fin);
    };
    On_change_validite_type();
}
$(document).ready(function() {
    $('#id_pieces_fournir').change(On_change_piece);
    $('#id_pieces_toutes').change(On_change_piece);
});

</script>
"""