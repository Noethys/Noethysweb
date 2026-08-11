# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.utils.translation import gettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field


CHOIX_CONTRASTE = [
    ("standard", "Standard"),
    ("eleve",    "Élevé"),
    ("maximum",  "Maximum"),
]

CHOIX_DALTONISME = [
    ("aucun",        "Aucun"),
    ("deuteranopie", "Deutéranopie (daltonisme vert)"),
    ("protanopie",   "Protanopie (daltonisme rouge)"),
    ("tritanopie",   "Tritanopie (daltonisme bleu)"),
]

CHOIX_TAILLE_TEXTE = [
    ("petite",      "Petite"),
    ("normale",     "Normale"),
    ("grande",      "Grande"),
    ("tres_grande", "Très grande"),
]

CHOIX_INTERLIGNAGE = [
    ("normal",   "Normal"),
    ("augmente", "Augmenté (×1,5)"),
    ("large",    "Large (×2)"),
]

CHOIX_AGRANDIR_CURSEUR = [
    ("normal",     "Normal"),
    ("grand",      "Grand"),
    ("tres_grand", "Très grand"),
]


class FormulaireAccessibilite(forms.Form):

    # ── Vision ───────────────────────────────────────────────────────────────

    contraste = forms.ChoiceField(
        label=_("Niveau de contraste"),
        choices=CHOIX_CONTRASTE,
        required=True,
        initial="standard",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        help_text=_("Augmente le contraste texte/fond."),
    )

    daltonisme = forms.ChoiceField(
        label=_("Mode daltonisme"),
        choices=CHOIX_DALTONISME,
        required=True,
        initial="aucun",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        help_text=_("Filtre de simulation pour adapter les couleurs de l'interface."),
    )

    taille_texte = forms.ChoiceField(
        label=_("Taille du texte"),
        choices=CHOIX_TAILLE_TEXTE,
        required=True,
        initial="normale",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        help_text=_("Ajuste la taille de base du texte sur l'ensemble de l'interface."),
    )

    souligner_liens = forms.BooleanField(
        label=_("Souligner les liens"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role":  "switch",
        }),
        help_text=_("Utile si vous ne distinguez pas les couleurs pour identifier les liens."),
    )

    masquer_images = forms.BooleanField(
        label=_("Masquer les images"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role":  "switch",
        }),
        help_text=_("Remplace les images décoratives par leur texte alternatif pour réduire la charge visuelle."),
    )

    # ── Lecture ───────────────────────────────────────────────────────────────

    police_dyslexie = forms.BooleanField(
        label=_("Police dyslexie"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role":  "switch",
        }),
        help_text=_("Utilise la police OpenDyslexic pour faciliter la lecture."),
    )

    espacement_lettres = forms.BooleanField(
        label=_("Espacement des lettres"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role":  "switch",
        }),
        help_text=_("Augmente le letter-spacing pour améliorer la lisibilité."),
    )

    interlignage = forms.ChoiceField(
        label=_("Interlignage"),
        choices=CHOIX_INTERLIGNAGE,
        required=True,
        initial="normal",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        help_text=_("Un interlignage plus grand facilite la lecture pour les troubles dys."),
    )

    masque_lecture = forms.BooleanField(
        label=_("Masque de lecture"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role":  "switch",
        }),
        help_text=_("Bande horizontale qui suit le curseur pour faciliter la lecture ligne à ligne."),
    )

    # ── Navigation ────────────────────────────────────────────────────────────

    grandes_zones_clic = forms.BooleanField(
        label=_("Grandes zones de clic"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role":  "switch",
        }),
        help_text=_("Agrandit les boutons et liens pour faciliter le clic."),
    )

    agrandir_curseur = forms.ChoiceField(
        label=_("Agrandir le curseur"),
        choices=CHOIX_AGRANDIR_CURSEUR,
        required=True,
        initial="normal",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        help_text=_("Remplace le curseur par une version agrandie, plus visible pour les malvoyants."),
    )

    # ── Mouvement ─────────────────────────────────────────────────────────────

    reduire_animations = forms.BooleanField(
        label=_("Réduire les animations"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role":  "switch",
        }),
        help_text=_("Désactive ou réduit les animations de l'interface."),
    )

    def __init__(self, *args, **kwargs):
        super(FormulaireAccessibilite, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_errors = False

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-3"
        self.helper.field_class = "col-md-9"

        self.helper.layout = Layout(
            Fieldset("<i class='fa fa-eye ms-2 me-2' aria-hidden='true'></i>Vision",
                Field("taille_texte",   template="portail/crispy/field_select_row.html"),
                Field("contraste",      template="portail/crispy/field_select_row.html"),
                Field("daltonisme",     template="portail/crispy/field_select_row.html"),
                Field("souligner_liens",  template="portail/crispy/field_switch_row.html"),
                Field("masquer_images",   template="portail/crispy/field_switch_row.html"),
            ),
            Fieldset("<i class='fa fa-font ms-2 me-2' aria-hidden='true'></i>Lecture",
                Field("police_dyslexie",    template="portail/crispy/field_switch_row.html"),
                Field("espacement_lettres", template="portail/crispy/field_switch_row.html"),
                Field("interlignage",       template="portail/crispy/field_select_row.html"),
                Field("masque_lecture",     template="portail/crispy/field_switch_row.html"),
            ),
            Fieldset("<i class='fa fa-mouse-pointer ms-2 me-2' aria-hidden='true'></i>Navigation &amp; mouvement",
                Field("grandes_zones_clic",  template="portail/crispy/field_switch_row.html"),
                Field("agrandir_curseur",    template="portail/crispy/field_select_row.html"),
                Field("reduire_animations",  template="portail/crispy/field_switch_row.html"),
            ),
        )
