#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def hash_depuis_texte(texte):
    """Calcule un hash numérique stable à partir d'un texte."""
    hash_val = 0
    for char in texte:
        hash_val = ord(char) + ((hash_val << 5) - hash_val)
        hash_val = hash_val & 0xFFFFFFFF  # Conversion en entier 32 bits non signé
        if hash_val >= 0x80000000:
            hash_val -= 0x100000000      # Retour en signé comme JS
    return hash_val


def hue_depuis_texte(texte):
    return abs(hash_depuis_texte(texte)) % 360


@register.simple_tag
def couleur_pastel(texte):
    """Retourne la couleur de fond pastel HSL pour un texte donné."""
    hue = hue_depuis_texte(texte)
    return mark_safe('hsl({}, 55%, 90%)'.format(hue))


@register.simple_tag
def couleur_texte(texte):
    """Retourne la couleur de texte sombre HSL pour un texte donné."""
    hue = hue_depuis_texte(texte)
    return mark_safe('hsl({}, 55%, 25%)'.format(hue))


@register.simple_tag
def style_badge_pastel(texte):
    """Retourne l'attribut style complet pour un badge (fond + texte)."""
    hue = hue_depuis_texte(texte)
    return mark_safe('background-color: hsl({hue}, 55%, 90%); color: hsl({hue}, 55%, 25%);'.format(hue=hue))
