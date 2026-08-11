# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, importlib
logger = logging.getLogger(__name__)
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site


def Get_mentions_legales(context, request):
    # Récupération du texte html de la déclaration
    if context["parametres_portail"].get("mentions_type", "DEFAUT") == "DEFAUT":
        texte = render_to_string("portail/modele_mentions_legales.html")
    else:
        texte = context["parametres_portail"].get("mentions_html", "")

    # Insertion des variables de l'organisateur
    for nom_champ in ("nom", "rue", "cp", "ville"):
        texte = texte.replace("{ORGANISATEUR_%s}" % nom_champ.upper(), getattr(context["organisateur"], nom_champ) or "")

    # Insertion de l'URL principale du portail
    texte = texte.replace("{URL_PORTAIL}", str(get_current_site(request)))

    # Recherche un texte complémentaire dans le répertoire site-packages de python
    try:
        module = importlib.import_module("noethysweb_mentions_legales_custom")
        texte += module.Get_html()
    except:
        pass

    return texte
