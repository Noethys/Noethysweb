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
from core.models import ModeleWord
from core.data import data_modeles_word


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = ModeleWord
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "fichier": "Sélectionnez un fichier Word (extension docx)."
        }

    def __init__(self, *args, **kwargs):
        categorie = kwargs.pop("categorie")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_word_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme modèle par défaut"
        if len(ModeleWord.objects.filter(categorie=categorie)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Récupère la liste des mots-clés
        liste_mots_cles = data_modeles_word.Get_mots_cles(categorie)

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
            Fieldset("Fichier Word",
                Field("fichier"),
            ),
            Fieldset("Mots-clés pour fusion",
                Div(
                    HTML("<label class='col-form-label col-md-2 requiredField'>Mots-clés</label>"),
                        Div(
                            HTML(Get_html_mots_cles(liste_mots_cles)), css_class="col-md-10"),
                            css_class="form-group row",
                        ),
                    ),

        )


def Get_html_mots_cles(liste_mots_cles=[]):
    html_detail = []
    for code, label in liste_mots_cles:
        html_detail.append("""<tr><td class='pr-5'>%s</td><td><b>%s</b></td></tr> """ % (label, code))
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
                <i class='fa fa-lightbulb-o'></i> Recopiez les mots-clés de votre choix dans votre document Word. Pour insérer un mot-clé dans Word : Insertion > QuickPart > Champ. Sélectionner « ChampFusion » dans la liste des noms de champs. Saisir le mot-clé (en conservant les majuscules et les accolades) dans la case « Nom du champ » et cliquer sur OK.
            </div>
            <div>
                <table style="margin-bottom: 2px;">
                    %s
                </table>
            </div>
        </div>
    </div>
    """ % "".join(html_detail)
    return html
