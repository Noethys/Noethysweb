# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.db.models import Max
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Hidden
from crispy_forms.bootstrap import Field
from django_summernote.widgets import SummernoteInplaceWidget
from core.forms.select2 import Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Sondage, SondagePage, SondageQuestion


class Formulaire_sondage(FormulaireBase, ModelForm):

    class Meta:
        model = Sondage
        fields = ["titre", "description", "conclusion", "public", "categories_rattachements", "modifiable", "structure"]
        widgets = {
            "description": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '200px'}}),
            "conclusion": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '200px'}}),
            "categories_rattachements": Select2MultipleWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire_sondage, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'sondages_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Catégories de rattachements
        self.fields["categories_rattachements"].initial = [1, 2, 3]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'sondages_liste' %}", ajouter=False),
            Fieldset("Généralités",
                Field("titre"),
                Field("description"),
                Field("conclusion"),
                Field("public"),
                Field("categories_rattachements"),
                Field("modifiable"),
            ),
            Fieldset("Structure associée",
                Field("structure"),
            ),
            HTML(EXTRA_SCRIPT_SONDAGE),
        )

    def clean(self):
        if self.cleaned_data["public"] == "individu" and not self.cleaned_data["categories_rattachements"]:
            self.add_error("categories_rattachements", "Vous devez sélectionner au moins une catégorie de rattachement")
            return
        return self.cleaned_data

EXTRA_SCRIPT_SONDAGE = """
<script>

function On_change_public() {
    $('#div_id_categories_rattachements').hide();
    if ($("#id_public").val() == 'individu') {
        $('#div_id_categories_rattachements').show();
    };
}
$(document).ready(function() {
    $('#id_public').on('change', On_change_public);
    On_change_public.call($('#id_public').get(0));
});

</script>
"""


class Formulaire_page(FormulaireBase, ModelForm):

    class Meta:
        model = SondagePage
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        idsondage = kwargs.pop("idsondage")
        super(Formulaire_page, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'pages_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Ordre
        if self.instance.ordre == None:
            max = SondagePage.objects.filter(sondage_id=idsondage).aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Nom de la page par défaut
        if not self.instance.pk:
            self.fields["titre"].initial = "Page %d" % (SondagePage.objects.filter(sondage_id=idsondage).count() + 1)

        # Affichage
        self.helper.layout = Layout(
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False, autres_commandes=[
                HTML("""<button type="submit" name="enregistrer" title="Enregistrer" class="btn btn-primary"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """),
                HTML("""<a class="btn btn-danger" title="Annuler" onclick="$('#modal_formulaire').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """),
            ], ),
            Hidden("sondage", value=idsondage),
            Hidden("ordre", value=self.fields['ordre'].initial),
            Hidden("idpage", value=self.instance.pk),
            Field("titre"),
            Field("description"),
        )


class Formulaire_question(FormulaireBase, ModelForm):

    class Meta:
        model = SondageQuestion
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idpage = kwargs.pop("idpage")
        super(Formulaire_question, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'questions_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Ordre
        if self.instance.ordre == None:
            max = SondageQuestion.objects.filter(page_id=idpage).aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Empêche la modification de contrôle
        if self.instance.pk:
            self.fields["controle"].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False, autres_commandes=[
                HTML("""<button type="submit" name="enregistrer" title="Enregistrer" class="btn btn-primary"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """),
                HTML("""<a class="btn btn-danger" title="Annuler" onclick="$('#modal_formulaire').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """),
            ], ),
            Hidden("page", value=idpage),
            Hidden("ordre", value=self.fields['ordre'].initial),
            Hidden("idquestion", value=self.instance.pk),
            Field("label"),
            Field("controle"),
            Field("choix"),
            Field("texte_aide"),
            Field("obligatoire"),
            HTML(EXTRA_SCRIPT_QUESTION),
        )

    def clean(self):
        if self.cleaned_data["controle"] in ("liste_deroulante", "liste_coches") and not self.cleaned_data["choix"]:
            self.add_error("choix", "Vous devez saisir au moins un choix")
            return

        return self.cleaned_data


EXTRA_SCRIPT_QUESTION = """
<script>

// Lors de la sélection du type de contrôle
function On_change_controle() {
    $("div[id^='div_id_ctrl']").hide();
    $('#div_id_ctrl_' + $(this).val()).show();
    $("#div_id_choix").hide();
    if (jQuery.inArray($('#id_controle').val(), ['liste_deroulante', 'liste_coches']) !== -1 ) {
        $("#div_id_choix").show();
    };
}
$(document).ready(function() {
    $('#id_controle').change(On_change_controle);
    On_change_controle.call($('#id_controle').get(0));
});

</script>
"""
