# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import csv, os.path, operator
from django import forms
from django.forms import ModelForm
from django.conf import settings
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Hidden
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils import utils_images, utils_adresse
from core.models import Individu
from core.widgets import DatePickerWidget, CodePostal, Ville, Crop_image


class Formulaire(FormulaireBase, ModelForm):
    # Photo
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    # Naissance
    date_naiss = forms.DateField(label="Date", required=False, widget=DatePickerWidget(), help_text="Au format JJ/MM/AAAA. Elle permet de calculer l'âge de l'individu.")
    pays_naiss_insee = forms.ChoiceField(label="Pays", choices=[], required=False, help_text="Pays de naissance. Par défaut, la France.")

    class Meta:
        model = Individu
        fields = ["civilite", "nom", "nom_jfille", "prenom", "deces", "annee_deces", "date_naiss", "type_sieste", "memo", "photo",
                  "cp_naiss", "ville_naiss", "ville_naiss_insee", "pays_naiss_insee", "situation_familiale", "type_garde", "info_garde"]
        widgets = {
            'memo': forms.Textarea(attrs={'rows': 3}),
            'info_garde': forms.Textarea(attrs={'rows': 3}),
            'cp_naiss': CodePostal(attrs={"id_ville": "id_ville_naiss"}),
            'ville_naiss': Ville(attrs={"id_codepostal": "id_cp_naiss"}),
            'photo': Crop_image(attrs={"largeur_min": 200, "hauteur_min": 200, "ratio": "1/1"}),
        }
        help_texts = {
            "nom_jfille": "Facultatif : nom de naissance, s'il est différent du nom d'usage.",
            "deces": "Cochez si l'individu est décédé.",
            "type_sieste": "Type de sieste de l'enfant. Les types se créent dans Paramétrage > Types de sieste.",
            "memo": "Note libre affichée sur la fiche individuelle.",
            "photo": "Photo d'identité de l'individu (format image).",
            "situation_familiale": "Situation des parents de l'enfant (mariés, séparés...).",
            "type_garde": "Mode de garde de l'enfant, en cas de séparation des parents.",
            "info_garde": "Précisions sur la garde. Exemple : semaines paires chez le père.",
            "civilite": "Pour un enfant, choisissez Fille ou Garçon : la civilité détermine s'il est traité comme un enfant ou un adulte.",
            "nom": "Nom de famille en majuscules. Exemple : DUPOND.",
            "prenom": "Prénom avec une majuscule initiale. Exemple : Kévin.",
            "cp_naiss": "Tapez le code postal puis choisissez la ville dans la liste proposée.",
            "ville_naiss": "Tapez le début du nom puis choisissez la ville dans la liste proposée.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_identite_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Pays de naissance
        with open(os.path.join(settings.BASE_DIR, "core/data/pays.csv"), "r", encoding="utf-8-sig") as fichier:
            choix_pays = sorted([ligne for ligne in csv.reader(fichier, delimiter=";")], key=operator.itemgetter(1))
        self.fields["pays_naiss_insee"].choices = choix_pays
        self.initial["pays_naiss_insee"] = self.instance.pays_naiss_insee or "99100"

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="individu_identite_modifier", modifier_args="idfamille=idfamille idindividu=idindividu",
                                  modifier=self.request.user.has_perm("core.individu_identite_modifier"), enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'individu_identite' idfamille=idfamille idindividu=idindividu %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Hidden("ville_naiss_insee", value=self.instance.ville_naiss_insee),
            Field("cropper_data"),
            Fieldset("Etat-civil",
                Field("civilite"),
                Field("nom"),
                Field("nom_jfille"),
                Field("prenom"),
                Field("deces"),
                Field("annee_deces"),
            ),
            Fieldset("Naissance",
                Field("date_naiss"),
                Field("cp_naiss"),
                Field("ville_naiss"),
                Field("pays_naiss_insee"),
            ),
            Fieldset("Situation familiale",
                Field("situation_familiale"),
                Field("type_garde"),
                Field("info_garde"),
            ),
            Fieldset("Divers",
                Field("type_sieste"),
                Field("memo"),
            ),
            Fieldset("Photo",
                Field("photo"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Si modification de la ville de naissance, on recherche le code INSEE de la ville de naissance
        if self.cleaned_data["ville_naiss_insee"] == "None":
            self.cleaned_data["ville_naiss_insee"] = None
        if "cp_naiss" in self.changed_data or "ville_naiss" in self.changed_data or not self.cleaned_data["ville_naiss_insee"]:
            self.cleaned_data["ville_naiss_insee"] = utils_adresse.Get_code_insee_ville(cp=self.cleaned_data.get("cp_naiss", None), ville=self.cleaned_data.get("ville_naiss", None))
        return self.cleaned_data

    def save(self):
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get('cropper_data')
        # Recadrage de l'image
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.photo)
        return form


EXTRA_SCRIPT = """
<script>

// civilite
function On_change_civilite() {
    $('#div_id_nom_jfille').hide();
    $('#div_id_prenom').hide();
    if($(this).val() == 3) {
        $('#div_id_nom_jfille').show();
    };
    if($(this).val() < 6) {
        $('#div_id_prenom').show();
    }
}
$(document).ready(function() {
    $('#id_civilite').change(On_change_civilite);
    On_change_civilite.call($('#id_civilite').get(0));
});


// deces
function On_change_deces() {
    $('#div_id_annee_deces').hide();
    if ($(this).prop("checked")) {
        $('#div_id_annee_deces').show();
    }
}
$(document).ready(function() {
    $('#id_deces').on('change', On_change_deces);
    On_change_deces.call($('#id_deces').get(0));
});

</script>
"""
