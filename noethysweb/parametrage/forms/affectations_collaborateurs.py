# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
import json
from crispy_forms.layout import Layout, Hidden, Fieldset, Div, HTML
from crispy_forms.bootstrap import Field, InlineCheckboxes, PrependedText
from django.utils.html import escape
from core.forms.base import FormulaireBase
from core.models import AffectationCollaborateur, Activite, Groupe, UniteRemplissage
from collaborateurs.utils.utils_affectations import Arbre


class Formulaire(FormulaireBase, ModelForm):
    parent = forms.TypedChoiceField(label="Affectation parente", required=False, coerce=int, empty_value=None)
    avec_couleur = forms.BooleanField(label="Couleur", required=False)
    couleur = forms.CharField(label="Couleur", required=False, widget=forms.TextInput(attrs={"type": "color", "title": "Couleur des en-têtes de regroupement du planning", "aria-label": "Couleur"}))
    activite = forms.ModelChoiceField(label="Activité", queryset=Activite.objects.all().order_by("nom"), required=False, empty_label="Aucune")
    groupe = forms.TypedChoiceField(label="Groupe", required=False, coerce=int, empty_value=None)
    unites_remplissage = forms.TypedMultipleChoiceField(label="Unités affichées", required=False, coerce=int, widget=forms.CheckboxSelectMultiple,
                                                        help_text="Aucune cochée : toutes les unités.")

    class Meta:
        model = AffectationCollaborateur
        fields = ["nom", "abrege", "parent", "couleur", "actif", "observations", "seuil_encadrement"]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Ex : ALSH Les Lutins, Maternelles..."}),
            "abrege": forms.TextInput(attrs={"placeholder": "Ex : Mat.", "title": "Nom court affiché sur les barres du planning"}),
            "seuil_encadrement": forms.NumberInput(attrs={"placeholder": "8", "min": 1, "title": "Nombre maximal de consommations par collaborateur affecté"}),
            "observations": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "abrege": "Abréviation",
            "seuil_encadrement": "Encadrement max.",
            "actif": "Active (proposée lors de la saisie)",
        }
        help_texts = {
            "seuil_encadrement": "Vide : celui du parent.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "affectations_collaborateurs_form"
        self.helper.form_method = "post"
        self.helper.form_tag = True
        self.helper.form_class = "form-vertical"

        # Liste des parents possibles (on exclut l'affectation elle-même et ses descendants)
        arbre = Arbre()
        exclure = []
        if self.instance.pk:
            exclure = [self.instance.pk] + arbre.Get_descendants(self.instance.pk)
        self.fields["parent"].choices = [("", "Aucune (premier niveau)")] + arbre.Get_choix(exclure=exclure)
        if self.instance.pk:
            self.fields["parent"].initial = self.instance.parent_id
        self.fields["avec_couleur"].initial = bool(self.instance.couleur)
        if not self.instance.couleur:
            self.initial["couleur"] = "#3c8dbc"

        # Lien avec les consommations : groupes et unités de toutes les activités (filtrés côté navigateur)
        liens = {}
        for groupe in Groupe.objects.all().order_by("ordre"):
            liens.setdefault(groupe.activite_id, {"groupes": [], "unites": []})["groupes"].append([groupe.pk, groupe.nom])
        for unite in UniteRemplissage.objects.all().order_by("ordre"):
            liens.setdefault(unite.activite_id, {"groupes": [], "unites": []})["unites"].append([unite.pk, unite.abrege, unite.nom])
        self.fields["groupe"].choices = [("", "Tous les groupes")] + [(groupe.pk, groupe.nom) for groupe in Groupe.objects.all().order_by("ordre")]
        self.fields["unites_remplissage"].choices = [(unite.pk, "%s - %s" % (unite.abrege, unite.nom)) for unite in UniteRemplissage.objects.all().order_by("ordre")]
        if self.instance.pk:
            self.fields["activite"].initial = self.instance.activite_id
            self.fields["groupe"].initial = self.instance.groupe_id
            self.fields["unites_remplissage"].initial = list(self.instance.unites_remplissage.values_list("pk", flat=True))

        self.helper.layout = Layout(
            Hidden("idaffectation", value=self.instance.pk or ""),
            Div(
                Div(Field("nom"), css_class="col-md-8"),
                Div(Field("abrege"), css_class="col-md-4"),
                Div(Field("parent"), css_class="col-md-8"),
                Div(HTML("<label class='aff-label-couleur'>Couleur</label>"),
                    Div(Field("avec_couleur", template="parametrage/affectations_collaborateurs_case.html"), Field("couleur", wrapper_class="mb-0"), css_class="aff-ligne-couleur"),
                    css_class="col-md-4 form-group"),
                css_class="form-row",
            ),
            Fieldset("Lien avec les consommations",
                Div(
                    Div(Field("activite"), css_class="col-md-5"),
                    Div(Field("groupe"), css_class="col-md-4"),
                    Div(PrependedText("seuil_encadrement", "1 pour"), css_class="col-md-3"),
                    css_class="form-row",
                ),
                Div(InlineCheckboxes("unites_remplissage"), css_id="aff_bloc_unites"),
                HTML("<div id='aff_liens_activites' hidden data-liens='%s'></div>" % escape(json.dumps(liens))),
                css_class="aff-fieldset-lien",
            ),
            Field("observations"),
            Field("actif", wrapper_class="mb-0"),
        )

    def clean_parent(self):
        idparent = self.cleaned_data.get("parent")
        if not idparent:
            return None
        if self.instance.pk and idparent in [self.instance.pk] + Arbre().Get_descendants(self.instance.pk):
            raise forms.ValidationError("Une affectation ne peut pas être placée sous elle-même ou sous l'une de ses sous-affectations.")
        return AffectationCollaborateur.objects.filter(pk=idparent).first()

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("avec_couleur"):
            cleaned_data["couleur"] = None
        # Le groupe et les unités doivent appartenir à l'activité choisie
        activite = cleaned_data.get("activite")
        idgroupe = cleaned_data.get("groupe")
        cleaned_data["groupe"] = Groupe.objects.filter(pk=idgroupe, activite=activite).first() if activite and idgroupe else None
        cleaned_data["unites_remplissage"] = list(UniteRemplissage.objects.filter(pk__in=cleaned_data.get("unites_remplissage") or [], activite=activite)) if activite else []
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.activite = self.cleaned_data.get("activite")
        instance.groupe = self.cleaned_data.get("groupe")
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def _save_m2m(self):
        super()._save_m2m()
        self.instance.unites_remplissage.set(self.cleaned_data.get("unites_remplissage", []))
