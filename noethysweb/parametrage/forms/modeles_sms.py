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
from core.models import ModeleSMS
from core.data import data_modeles_sms
from outils.widgets import Texte_SMS


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = ModeleSMS
        fields = "__all__"
        widgets = {
            "texte": Texte_SMS(),
        }

    def __init__(self, *args, **kwargs):
        categorie = kwargs.pop("categorie")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_sms_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme modèle par défaut"
        if len(ModeleSMS.objects.filter(categorie=categorie)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Définit la taille max du texte
        configuration_sms_defaut = self.request.user.Get_configuration_sms_defaut()
        if configuration_sms_defaut:
            self.fields['texte'].widget.attrs['maxlength'] = configuration_sms_defaut.nbre_caracteres

        # Récupère la liste des mots-clés
        liste_mots_cles = data_modeles_sms.Get_mots_cles(categorie)

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
            Fieldset("SMS",
                Field('objet'),
                Field('texte'),
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
            var tav = $('#id_texte').val(),
            strPos = $('#id_texte')[0].selectionStart;
            texte_avant = (tav).substring(0, strPos),
            texte_apres = (tav).substring(strPos, tav.length); 
            $('#id_texte').val(texte_avant + this.name + texte_apres);
        });
    </script>
    """ % "".join(html_detail)
    return html
