# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site


def Get_declaration_accessibilite(context, request):
    # Récupération du texte html de la déclaration
    if context["parametres_portail"].get("declaration_accessibilite_type", "DEFAUT") == "DEFAUT":
        texte = render_to_string("portail/modele_declaration_accessibilite.html")
    else:
        texte = context["parametres_portail"].get("declaration_accessibilite_html", "")

    # Insertion des variables de l'organisateur
    for nom_champ in ("nom", "rue", "cp", "ville"):
        texte = texte.replace("{ORGANISATEUR_%s}" % nom_champ.upper(), getattr(context["organisateur"], nom_champ) or "")

    # Insertion de l'URL principale du portail
    texte = texte.replace("{URL_PORTAIL}", str(get_current_site(request)))

    return texte
