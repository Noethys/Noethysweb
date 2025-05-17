# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, ButtonHolder, Fieldset, Div
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import ModeleEmail
from django_summernote.widgets import SummernoteInplaceWidget
from core.data import data_modeles_emails


class Formulaire(FormulaireBase, ModelForm):
    html = forms.CharField(label="Texte", widget=SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '300px'}}))

    class Meta:
        model = ModeleEmail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        categorie = kwargs.pop("categorie")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_emails_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Objet
        self.fields["objet"].required = True

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme modèle par défaut"
        if len(ModeleEmail.objects.filter(categorie=categorie)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            # self.fields['defaut'].disabled = True

        # Récupère la liste des mots-clés
        liste_mots_cles = data_modeles_emails.Get_mots_cles(categorie)

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('categorie', value=categorie),
            Fieldset("Généralités",
                Field('nom'),
                Field('description'),
                Field('structure'),
                Field('defaut'),
            ),
            Fieldset("Email",
                Field('objet'),
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

