# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import Produit, Tarif, QuestionnaireQuestion, QuestionnaireReponse
from core.utils.utils_commandes import Commandes
from core.widgets import Crop_image, ColorPickerWidget
from core.utils import utils_images
from parametrage.forms import questionnaires


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)
    couleur = forms.CharField(label="Couleur", required=True, widget=ColorPickerWidget(), initial="#3c8dbc")

    # Tarification
    choix_tarification = [
        ("GRATUIT", "Gratuit"),
        ("SIMPLE", "Tarif simple"),
        ("AVANCE", "Tarification avancée"),
    ]
    texte_aide = "Pour créer, modifier ou supprimer des tarifs avancés, sélectionnez 'Tarification avancée', cliquez sur Enregistrer puis cliquez sur le bouton <i class='fa fa-gear'></i> sur la ligne du produit dans la liste des produits."
    type_tarification = forms.TypedChoiceField(label="Tarification", choices=choix_tarification, initial="GRATUIT", required=False, help_text=texte_aide)

    class Meta:
        model = Produit
        fields = "__all__"
        widgets = {
            "image": Crop_image(attrs={"largeur_min": 200, "hauteur_min": 200, "ratio": "1/1"}),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }


    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'produits_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Tarification
        if self.instance.pk:
            if self.instance.montant:
                self.fields['type_tarification'].initial = "SIMPLE"
            else:
                liste_tarifs = Tarif.objects.filter(produit=self.instance)
                if len(liste_tarifs):
                    self.fields['type_tarification'].initial = "AVANCE"
                    self.fields['type_tarification'].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'produits_liste' %}"),
            Field("cropper_data"),
            Fieldset("Généralités",
                Field("nom"),
                Field("categorie"),
                Field("image"),
                Field("couleur"),
                Field("observations"),
            ),
            Fieldset("Stock",
                Field("quantite"),
            ),
            Fieldset("Tarification",
                Field("type_tarification"),
                Field("montant"),
            ),
            HTML(EXTRA_SCRIPT),
        )

        # Création des champs des questionnaires
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        questions = QuestionnaireQuestion.objects.filter(condition_structure, categorie="produit", visible=True).order_by("ordre")
        if questions:
            liste_fields = []
            for question in questions:
                nom_controle, ctrl = questionnaires.Get_controle(question)
                if ctrl:
                    self.fields[nom_controle] = ctrl
                    liste_fields.append(Field(nom_controle))
            self.helper.layout.append(Fieldset("Questionnaire", *liste_fields))

            # Importation des réponses
            for reponse in QuestionnaireReponse.objects.filter(donnee=self.instance.pk, question__categorie="produit"):
                key = "question_%d" % reponse.question_id
                if key in self.fields:
                    self.fields[key].initial = reponse.Get_reponse_for_ctrl()

    def clean(self):
        # Questionnaires
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)

        # Tarification
        if self.cleaned_data["type_tarification"] == "SIMPLE" and self.cleaned_data["montant"] in (None, 0.0):
                self.add_error('montant', "Vous devez saisir un montant")
                return

        if self.cleaned_data["type_tarification"] in ("GRATUIT", "AVANCE"):
            self.cleaned_data["montant"] = None

        return self.cleaned_data

    def save(self):
        """ Recadrage de l'image """
        instance = super(Formulaire, self).save()

        # Recadrage de l'image
        cropper_data = self.cleaned_data.get('cropper_data')
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, instance.image)

        # Enregistrement des réponses du questionnaire
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                idquestion = int(key.split("_")[1])
                QuestionnaireReponse.objects.update_or_create(donnee=instance.pk, question_id=idquestion, defaults={'reponse': valeur})

        return instance


EXTRA_SCRIPT = """
<script>

// type_tarification
function On_change_type_tarification() {
    $('#div_id_montant').hide();
    if($(this).val() == 'SIMPLE') {
        $('#div_id_montant').show();
    }
}
$(document).ready(function() {
    $('#id_type_tarification').change(On_change_type_tarification);
    On_change_type_tarification.call($('#id_type_tarification').get(0));
});

</script>
"""
