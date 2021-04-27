# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, ButtonHolder, Fieldset, Div
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import ModeleRappel
from core.widgets import ColorPickerWidget
from django_summernote.widgets import SummernoteInplaceWidget


class Formulaire(ModelForm):
    couleur = forms.CharField(label="Couleur", required=False, widget=ColorPickerWidget(), initial="#FFFFFF")
    html = forms.CharField(label="Texte", widget=SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '400px', 'toolbar': [
            # ['style', ['style']],
            ['font', ['bold', 'underline', 'clear']],
            # ['fontname', ['fontname']],
            # ['color', ['color']],
            # ['para', ['ul', 'ol', 'paragraph']],
            # ['table', ['table']],
            # ['insert', ['link', 'picture', 'video']],
            # ['view', ['fullscreen', 'codeview', 'help']],
        ]}}))

    class Meta:
        model = ModeleRappel
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_rappels_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Récupère la liste des mots-clés
        liste_mots_cles = [
            ("{ID_FAMILLE}", "IDfamille"), ("{NOM_AVEC_CIVILITE}", "{FAMILLE_NOM}"),
            ("{NOM_SANS_CIVILITE}", "nomSansCivilite"), ("{ADRESSE_RUE}", "{FAMILLE_RUE}"),
            ("{ADRESSE_CP}", "{FAMILLE_CP}"), ("{ADRESSE_VILLE}", "{FAMILLE_VILLE}"), ("{SOLDE_CHIFFRES}", "solde"),
            ("{SOLDE_LETTRES}", "solde_lettres"), ("{DATE_MIN}", "date_min"), ("{DATE_MAX}", "date_max"),
            ("{NUM_DOCUMENT}", "num_rappel"),
        ]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Fieldset("Généralités",
                Field('label'),
                Field('couleur'),
                Field('retard_min'),
                Field('retard_max'),
            ),
            Fieldset("Texte",
                Field('titre'),
                Field('html'),
                Div(
                    HTML("<label class='col-form-label col-md-2 requiredField'>Mots-clés</label>"),
                    Div(
                        HTML(Get_html_mots_cles(liste_mots_cles)),
                        css_class="col-md-10"
                    ),
                    css_class="form-group row"
                ),
            ),
        )


def Get_html_mots_cles(liste_mots_cles=[]):
    html_detail = []
    for code, label in liste_mots_cles:
        html_detail.append("""<li><a href='#' title="%s" name="%s" class="mot_cle"><i class='fa fa-tag'></i> %s</a></li> """ % (label, code, code))
    html = """
    <style>
        .liste_mots_cles {
            background: #f4f4f4;
            padding: 10px;
            margin-bottom: 10px;
        }
        .liste_mots_cles li {
            display: inline;
            white-space: nowrap;
            margin-right: 20px;
        }
        #div_id_html {
            margin-bottom: 0px;
        }
    </style>
    <div class='card'>
        <div class='card-body liste_mots_cles m-0'>
            <div style='color: #b4b4b4;margin-bottom: 5px;'>
                <i class='fa fa-lightbulb-o'></i> Cliquez sur un mot-clé pour l'insérer dans le texte
            </div>
            <div>
                <ul class='list-unstyled' style="margin-bottom: 2px;">
                    %s
                </ul>
            </div>
        </div>
    </div>
    <script>
        $(".mot_cle").on('click', function(event) {
            event.preventDefault();
            $('#id_html').summernote('pasteHTML', this.name);
        });
    </script>
    """ % "".join(html_detail)
    return html

