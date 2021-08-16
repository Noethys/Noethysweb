# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML
from crispy_forms.bootstrap import Field
from django_summernote.widgets import SummernoteInplaceWidget
from core.forms.base import FormulaireBase
from core.models import Article, ImageArticle
from core.utils.utils_commandes import Commandes
from core.widgets import DateTimePickerWidget
from core.widgets import Crop_image
from core.utils import utils_images
from portail.widgets import Selection_image_article
from django_select2.forms import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)
    type_image = forms.ChoiceField(label="Image", choices=[("aucune", "Aucune image"), ("importer", "Importation d'une image"), ("banque_images", "Sélection dans la banque d'images")], initial="aucune", required=False)

    class Meta:
        model = Article
        fields = "__all__"
        widgets = {
            "date_debut": DateTimePickerWidget(),
            "date_fin": DateTimePickerWidget(),
            "texte": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '220px'}}),
            "image": Crop_image(attrs={"largeur_min": 447, "hauteur_min": 251, "ratio": "16/9"}),
            "image_article": Selection_image_article(),
            "activites": Select2MultipleWidget(),
        }
        labels = {
            "image": "Image à importer",
            "image_article": "Sélection de l'image",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'articles_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date de début de publication
        if not self.instance.pk:
            self.fields["date_debut"].initial = datetime.datetime.now()
            self.fields["auteur"].initial = self.request.user

        # Image prédéfinie
        self.fields["image_article"].choices = [("", "---------")] + [(image.pk, image.titre, image.image.name) for image in ImageArticle.objects.all().order_by("titre")]
        if self.instance.image:
            self.fields["type_image"].initial = "importer"
        if self.instance.image_article:
            self.fields["type_image"].initial = "banque_images"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'articles_liste' %}"),
            Field("cropper_data"),
            Field("auteur", type="hidden"),
            Fieldset("Généralités",
                Field("titre"),
                Field("texte"),
            ),
            Fieldset("Image d'illustration",
                Field("type_image"),
                Field("image"),
                Field("image_article"),
            ),
            Fieldset("Options",
                Field("statut"),
                Field("date_debut"),
                Field("date_fin"),
                Field("couleur_fond"),
            ),
            Fieldset("Document joint",
                Field("document"),
                Field("document_titre"),
            ),
            Fieldset("Public destinataire",
                Field("public"),
                Field("activites"),
            ),
            Fieldset("Structure associée",
                Field("structure"),
            ),
            HTML(EXTRA_HTML),
        )

    def save(self):
        """ Recadrage de l'image """
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get('cropper_data')
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.image)
        return form

    def clean(self):
        # Sélection d'une image
        if self.cleaned_data.get("type_image") == "aucune":
            self.cleaned_data["image"] = None
            self.cleaned_data["image_article"] = None
        if self.cleaned_data.get("type_image") == "importer" and not self.cleaned_data["image"]:
            self.add_error("type_image", "Vous devez sélectionner une image à importer ci-dessous")
        if self.cleaned_data.get("type_image") == "banque_images" and not self.cleaned_data["image_article"]:
            self.add_error("type_image", "Vous devez sélectionner une image dans la liste ci-dessous")

        # Sélection du public
        if self.cleaned_data.get("public") == "inscrits" and not self.cleaned_data["activites"]:
            self.add_error("public", "Vous devez sélectionner au moins une activité ci-dessous")

        return self.cleaned_data


EXTRA_HTML = """
<script>

// Sur sélection du type de l'image
function On_selection_type_image() {
    $('#div_id_image').hide();
    $('#div_id_image_article').hide();
    if ($("#id_type_image").val() == 'importer') {
        $('#div_id_image').show();
    };
    if ($("#id_type_image").val() == 'banque_images') {
        $('#div_id_image_article').show();
    };
}
$(document).ready(function() {
    $('#id_type_image').on('change', On_selection_type_image);
    On_selection_type_image.call($('#id_type_image').get(0));
});

// Sur sélection du public
function On_selection_public() {
    $('#div_id_activites').hide();
    if ($("#id_public").val() == 'inscrits') {
        $('#div_id_activites').show();
    };
}
$(document).ready(function() {
    $('#id_public').on('change', On_selection_public);
    On_selection_public.call($('#id_public').get(0));
});


</script>
"""
