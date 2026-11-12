# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column, Fieldset, Hidden, Div
from crispy_forms.bootstrap import Field, FormActions, PrependedText
from core.utils.utils_commandes import Commandes
from core.models import ModeleDocument
from core.forms.select2 import Select2Widget


class Formulaire(FormulaireBase, ModelForm):
    champs = forms.ModelChoiceField(label="Champs", widget=Select2Widget(), queryset=ModeleDocument.objects.all(), required=False)
    objets = forms.CharField(required=False)

    class Meta:
        model = ModeleDocument
        fields = "__all__"
        widgets = {
            'observations': forms.Textarea(attrs={'rows': 1}),
        }

    def __init__(self, *args, **kwargs):
        nom = kwargs.pop("nom", "")
        categorie = kwargs.pop("categorie", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_documents_form'
        self.helper.form_method = 'post'
        # self.helper.form_show_labels = False

        # Masquage des labels
        self.fields["nom"].label = False
        self.fields["largeur"].label = False
        self.fields["hauteur"].label = False
        self.fields["fond"].label = False
        self.fields["structure"].label = False

        # Liste des fonds disponibles
        self.fields["fond"].choices = [(None, "Aucun fond")] + [(modele.pk, modele.nom) for modele in ModeleDocument.objects.filter(categorie="fond")]

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Modèle par défaut"
        if len(ModeleDocument.objects.filter(categorie=categorie)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Création ou modification
        if not self.instance.idmodele:
            self.fields["nom"].initial = nom
            self.fields["largeur"].initial = 210
            self.fields["hauteur"].initial = 297
        else:
            categorie = self.instance.categorie

        # Affichage compact (le nom sert de titre, format et dimensions sur une ligne)
        self.helper.layout = Layout_editeur(categorie)



class Formulaire_creation(FormulaireBase, ModelForm):

    class Meta:
        model = ModeleDocument
        fields = ["nom", "categorie", "structure"]
        help_texts = {
            "nom": "Saisissez le nom du modèle de document. Exemple : Facture avec logo.",
            "structure": "Sélectionnez la structure associée à ce modèle. Laissez 'Toutes les structures' pour que ce modèle soit disponible dans toutes les structures.",
        }

    def __init__(self, *args, **kwargs):
        nom = kwargs.pop("nom", "")
        categorie = kwargs.pop("categorie")
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Commandes(ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset('Généralités',
                Field('nom'),
            ),
            Fieldset('Structure associée',
                Field('structure'),
            ),
            Hidden('categorie', value=categorie),
        )


# Icône "pivoter la page" (portrait <-> paysage)
ICONE_PIVOTER = """<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="5.5" width="7" height="9.5" rx="1"/><path d="M8 2.5a5.5 5.5 0 0 1 5.5 5.5"/><path d="M11.8 6.6l1.7 1.6 1.6-1.7"/></svg>"""


def Layout_editeur(categorie=None):
    """ Mise en page compacte du formulaire de l'éditeur de modèles de documents """
    return Layout(
        Hidden('categorie', value=categorie),
        Field('objets', type="hidden"),
        # En-tête : nom du modèle
        Div(
            Div(
                Field('nom', wrapper_class="modele-nom", placeholder="Nom du modèle", title="Cliquez pour renommer le modèle", aria_label="Nom du modèle"),
                HTML("""<label for="id_nom" class="modele-nom-crayon" title="Renommer le modèle"><i class="fa fa-pencil" aria-hidden="true"></i><span class="sr-only">Renommer le modèle</span></label>"""),
                css_class="modele-nom-zone",
            ),
            # Les boutons Enregistrer / Annuler sont dans la barre d'outils de l'éditeur (attribut form="modeles_documents_form")
            css_class="card-header modele-entete",
        ),
        Div(
            # Format et dimensions (la liste des formats n'est pas envoyée : elle remplit seulement largeur et hauteur)
            Div(
                HTML("""<select id="modele_format" class="custom-select custom-select-sm" title="Format de la page" aria-label="Format de la page">
                            <option value="A3">A3</option><option value="A4">A4</option><option value="A5">A5</option><option value="A6">A6</option>
                            <option value="">Personnalisé</option></select>"""),
                Field('largeur', wrapper_class="modele-dimension", css_class="form-control-sm", title="Largeur (mm)", aria_label="Largeur en mm"),
                HTML("""<span class="modele-fois">×</span>"""),
                Field('hauteur', wrapper_class="modele-dimension", css_class="form-control-sm", title="Hauteur (mm)", aria_label="Hauteur en mm"),
                HTML("""<span class="modele-unite">mm</span>"""),
                HTML("""<button type="button" id="modele_pivoter" class="btn btn-outil" title="Pivoter la page (portrait / paysage)" aria-label="Pivoter la page">%s</button>""" % ICONE_PIVOTER),
                css_class="modele-ligne",
            ),
            # Fond et structure
            Div(
                Div(
                    HTML("""<i class="fa fa-clone modele-picto" title="Calque de fond" aria-hidden="true"></i>"""),
                    Field('fond', css_class="custom-select-sm", title="Calque de fond", aria_label="Calque de fond"),
                    css_class="modele-paire",
                ),
                Div(
                    HTML("""<i class="fa fa-sitemap modele-picto" title="Structure associée" aria-hidden="true"></i>"""),
                    Field('structure', css_class="custom-select-sm", title="Structure associée", aria_label="Structure associée"),
                    css_class="modele-paire",
                ),
                css_class="modele-ligne modele-ligne-listes",
            ),
            Field('defaut', wrapper_class="modele-defaut"),
            css_class="card-body modele-corps",
        ),
    )
