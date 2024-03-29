# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML
from crispy_forms.bootstrap import Field
from django_summernote.widgets import SummernoteInplaceWidget
from core.forms.base import FormulaireBase
from core.models import Article, ImageArticle, Album, Activite, Groupe, Sondage
from core.utils.utils_commandes import Commandes
from core.widgets import DateTimePickerWidget, DateRangePickerWidget
from core.widgets import Crop_image
from core.utils import utils_images, utils_dates
from portail.widgets import Selection_image_article
from core.forms.select2 import Select2MultipleWidget, Select2Widget


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)
    type_image = forms.ChoiceField(label="Image", choices=[("aucune", "Aucune image"), ("importer", "Importation d'une image"), ("banque_images", "Sélection dans la banque d'images")], initial="aucune", required=False)
    periode = forms.CharField(label="Période", required=False, widget=DateRangePickerWidget(), help_text="Renseignez une période de présence.")

    class Meta:
        model = Article
        fields = "__all__"
        widgets = {
            "date_debut": DateTimePickerWidget(),
            "date_fin": DateTimePickerWidget(),
            "texte": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '220px'}}),
            "image": Crop_image(attrs={"largeur_min": 447, "hauteur_min": 167, "ratio": "447/167"}),
            "image_article": Selection_image_article(),
            "activites": Select2MultipleWidget(),
            "groupes": Select2MultipleWidget({"data-minimum-input-length": 0}),
            "album": Select2Widget({"lang": "fr", "data-width": "100%"}),
            "sondage": Select2Widget({"lang": "fr", "data-width": "100%"}),
            "texte_popup": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '180px'}}),
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

        # Activité
        self.fields["activites"].queryset = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom")

        # Groupe
        groupes = Groupe.objects.select_related("activite").filter(activite__structure__in=self.request.user.structures.all()).order_by("activite", "ordre")
        self.fields["groupes"].choices = [(groupe.pk, "%s : %s" % (groupe.activite.nom, groupe.nom)) for groupe in groupes]

        # Période de présence
        if self.instance.present_debut:
            self.fields["periode"].initial = "%s - %s" % (utils_dates.ConvertDateToFR(self.instance.present_debut), utils_dates.ConvertDateToFR(self.instance.present_fin))

        # Album
        condition = (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        self.fields["album"].queryset = Album.objects.filter(condition).order_by("date_creation")

        # Sondage
        condition = (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        self.fields["sondage"].queryset = Sondage.objects.filter(condition).order_by("titre")

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
            Fieldset("Album photos joint",
                Field("album"),
            ),
            Fieldset("Formulaire joint",
                Field("sondage"),
            ),
            Fieldset("Fenêtre popup",
                Field("texte_popup"),
            ),
            Fieldset("Public destinataire",
                Field("public"),
                Field("activites"),
                Field("groupes"),
                Field("periode"),
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

        if self.cleaned_data.get("public") == "presents_groupes" and not self.cleaned_data["groupes"]:
            self.add_error("public", "Vous devez sélectionner au moins un groupe ci-dessous")

        # Présents sur une période
        if self.cleaned_data.get("public") in ("presents", "presents_groupes"):
            self.cleaned_data["present_debut"] = self.cleaned_data["periode"].split(";")[0]
            self.cleaned_data["present_fin"] = self.cleaned_data["periode"].split(";")[1]

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
    $('#div_id_groupes').hide();
    $('#div_id_periode').hide();
    if ($("#id_public").val() == 'inscrits') {
        $('#div_id_activites').show();
    };
    if ($("#id_public").val() == 'presents') {
        $('#div_id_activites').show();
        $('#div_id_periode').show();
    };
    if ($("#id_public").val() == 'presents_groupes') {
        $('#div_id_groupes').show();
        $('#div_id_periode').show();
    };
}
$(document).ready(function() {
    $('#id_public').on('change', On_selection_public);
    On_selection_public.call($('#id_public').get(0));
});

</script>
"""
