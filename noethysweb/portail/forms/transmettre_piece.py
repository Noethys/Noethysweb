# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.core.validators import FileExtensionValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.models import Piece, Rattachement, Individu
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from individus.utils import utils_pieces_manquantes


class Formulaire(FormulaireBase, ModelForm):
    # Type de pièce
    selection_piece = forms.TypedChoiceField(label="Type de document", choices=[], required=True, help_text="Sélectionnez un type de document dans la liste. Sélectionnez 'Autre type' s'il ne s'agit pas d'un document prédéfini.")
    choix_individu = forms.TypedChoiceField(label="Individu concerné", choices=[], required=False, help_text="Sélectionnez le nom de l'individu concerné ou la famille s'il s'agit d'un document qui concerne toute la famille.")
    document = forms.FileField(label="Document", help_text="Sélectionnez un document à joindre (pdf, jpg ou png).", required=True, validators=[FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg'])])

    class Meta:
        model = Piece
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            "titre": "Titre du document*",
        }
        help_texts = {
            "titre": "Saisissez un titre pour ce document. Ex : Certificat médical de Sophie...",
            "observations": "Vous pouvez ajouter des observations si vous le souhaitez.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_transmettre_piece_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Pièces à fournir
        self.liste_pieces_fournir = utils_pieces_manquantes.Get_pieces_manquantes(famille=self.request.user.famille)
        self.fields['selection_piece'].choices = [(index, piece["label"]) for index, piece in enumerate(self.liste_pieces_fournir)] + [(9999, "Un autre type de pièce")]
        self.fields['selection_piece'].initial = None

        # Auteur
        if not self.instance.pk:
            self.fields["auteur"].initial = self.request.user

        # Choix de l'individu
        rattachements = Rattachement.objects.select_related("individu").filter(famille=self.request.user.famille).order_by("categorie")
        self.fields['choix_individu'].choices = [(None, "La famille")] + [(rattachement.individu_id, rattachement.individu.Get_nom()) for rattachement in rattachements]

        # Affichage
        self.helper.layout = Layout(
            Hidden("famille", value=self.request.user.famille.pk),
            Field("auteur", type="hidden"),
            Field('selection_piece'),
            Field('titre'),
            Field('choix_individu'),
            Field('document'),
            Field('observations'),
            HTML(EXTRA_SCRIPT),
            Commandes(enregistrer_label="<i class='fa fa-send margin-r-5'></i>Envoyer", annuler_url="{% url 'portail_documents' %}", ajouter=False, aide=False, css_class="pull-right"),
        )

    def clean(self):
        # Type de pièce
        if int(self.cleaned_data["selection_piece"]) == 9999:
            if self.cleaned_data["titre"] in ("", None):
                self.add_error('titre', "Vous devez saisir un titre pour cette pièce !")
            piece = None
        else:
            piece = self.liste_pieces_fournir[int(self.cleaned_data["selection_piece"])]

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
        self.cleaned_data["date_debut"] = datetime.date.today()
        self.cleaned_data["date_fin"] = piece["type_piece"].Get_date_fin_validite() if piece else datetime.date(2999, 1, 1)

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Sélection pièce
function On_change_selection_piece(event) {
    $('#div_id_titre').hide();
    $('#div_id_choix_individu').hide();
    if (this.value == 9999) {
        $('#div_id_titre').show();
        $('#div_id_choix_individu').show();
    };
}
$(document).ready(function() {
    $('#id_selection_piece').change(On_change_selection_piece);
    On_change_selection_piece.call($('#id_selection_piece').get(0));
});

</script>
"""
