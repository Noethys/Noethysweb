# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Accordéon pour les formulaires crispy, au style des titres de fieldset de l'application.

Exemple :

    from core.forms.accordeon import Accordeon, Section

    self.helper.layout = Layout(
        Accordeon(
            Section("Identification", Field("nom"), Field("prenom")),
            Section("Coordonnées", Field("rue"), Field("ville"), icone="fa-map-marker"),
            css_id="accordeon_individu",
        ),
        Field("champ_toujours_visible"),
    )

Options de Accordeon :
    - css_id : identifiant unique dans la page (conseillé si plusieurs accordéons sur la même page)
    - sections_independantes : True pour pouvoir ouvrir plusieurs sections en même temps (False par défaut)

Options de Section :
    - active : True pour ouvrir la section au chargement. Par défaut, la première section est ouverte.
               Si le formulaire contient des erreurs, la première section contenant une erreur est ouverte.
    - icone : classe Font Awesome affichée avant le titre (ex : "fa-calendar")
    - css_id : identifiant de la section (généré automatiquement à partir du titre sinon)
"""

from django.template.loader import render_to_string
from django.utils.safestring import SafeString
from django.utils.text import slugify
from crispy_forms.bootstrap import Accordion, AccordionGroup
from crispy_forms.utils import TEMPLATE_PACK, render_field


def Slug_ascii(texte=""):
    """ Identifiant HTML sans accents ni espaces : 'Période et données' -> 'periode_et_donnees' """
    return slugify(texte).replace("-", "_") or "section"


class Section(AccordionGroup):
    template = "core/crispy/accordeon_section.html"

    def __init__(self, name, *fields, css_id=None, icone=None, **kwargs):
        super(Section, self).__init__(name, *fields, css_id=css_id, **kwargs)
        self.icone = icone
        # Si aucun identifiant n'est fourni, il sera préfixé par celui de l'accordéon
        self.css_id_auto = not css_id
        if self.css_id_auto:
            self.css_id = Slug_ascii(name)

    def get_template_name(self, template_pack):
        # Gabarit indépendant du template pack (bootstrap4 ou bootstrap5)
        return self.template


class Accordeon(Accordion):
    template = "core/crispy/accordeon.html"

    def __init__(self, *sections, css_id=None, sections_independantes=False, **kwargs):
        if not css_id:
            css_id = "accordeon_%s" % Slug_ascii(sections[0].name if sections else "")
        super(Accordeon, self).__init__(*sections, css_id=css_id, **kwargs)
        self.sections_independantes = sections_independantes
        for section in sections:
            if getattr(section, "css_id_auto", False):
                section.css_id = "%s_%s" % (self.css_id, section.css_id)

    def get_template_name(self, template_pack):
        return self.template

    def render(self, form, context, template_pack=TEMPLATE_PACK, **kwargs):
        # Ouvre la première section en erreur, ou la première section par défaut
        self.open_target_group_for_form(form)
        content = SafeString("")
        for section in self.fields:
            # Sans data-parent, Bootstrap permet d'ouvrir plusieurs sections simultanément
            section.data_parent = "" if self.sections_independantes else self.css_id
            content += render_field(section, form, context, template_pack=template_pack, **kwargs)
        context.update({"accordion": self, "content": content})
        return render_to_string(self.get_template_name(template_pack), context.flatten())
