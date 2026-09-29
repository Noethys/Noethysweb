# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Activite
from core.forms.base import FormulaireBase
from core.widgets import DatePickerWidget
from core.utils import utils_export_parametrage


class Formulaire(FormulaireBase, forms.Form):
    activite = forms.ModelChoiceField(label="Activité", queryset=Activite.objects.none(), required=True)
    date_debut = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget(),
                                 help_text="Laissez vide pour utiliser les dates de l'activité (ou 1 an avant aujourd'hui si l'activité est illimitée).")
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget(),
                               help_text="Laissez vide pour utiliser les dates de l'activité (ou 1 an après aujourd'hui si l'activité est illimitée).")
    tous_les_tarifs = forms.BooleanField(label="Inclure les tarifs terminés avant la période analysée", required=False, initial=False)
    noms_responsables = forms.BooleanField(label="Inclure les noms des responsables de l'activité", required=False, initial=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_controle_ia"
        self.helper.form_method = "post"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Uniquement les activités des structures de l'utilisateur
        self.fields["activite"].queryset = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom")

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'activites_liste' %}", ajouter=False,
                      enregistrer_label="<i class='fa fa-download margin-r-5'></i>Générer le fichier"),
            Fieldset("Activité",
                Field("activite"),
            ),
            Fieldset("Période analysée",
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset("Options",
                Field("tous_les_tarifs"),
                Field("noms_responsables"),
            ),
            Fieldset("Prompt à utiliser",
                HTML(EXTRA_HTML),
            ),
        )

    def clean(self):
        date_debut, date_fin = self.cleaned_data.get("date_debut"), self.cleaned_data.get("date_fin")
        if date_debut and date_fin and date_debut > date_fin:
            self.add_error("date_fin", "La date de fin doit être postérieure à la date de début.")
        return self.cleaned_data


EXTRA_HTML = """
<p>
    <span class="badge badge-primary margin-r-5">1</span>Générez le fichier
    <span class="badge badge-primary margin-r-5 ml-3">2</span>Copiez le prompt
    <span class="badge badge-primary margin-r-5 ml-3">3</span>Collez-le dans l'IA en joignant le fichier
</p>
<textarea id="prompt_ia" class="form-control mb-2" rows="8" readonly aria-label="Prompt à utiliser">{{ prompt_ia }}</textarea>
<button type="button" class="btn btn-default" onclick="copier_prompt()" title="Copier le prompt"><i class="fa fa-copy margin-r-5"></i>Copier le prompt</button>
<script>
    function copier_prompt() {
        var texte = $("#prompt_ia").val();
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(texte).then(function() { toastr.success("Le prompt a été copié dans le presse-papiers"); });
        } else {
            $("#prompt_ia").select();
            document.execCommand("copy");
            toastr.success("Le prompt a été copié dans le presse-papiers");
        }
    }
</script>
"""
