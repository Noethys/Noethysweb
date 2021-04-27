# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from crispy_forms.layout import HTML, ButtonHolder
from crispy_forms.bootstrap import StrictButton


def Commandes(enregistrer=True, enregistrer_label="<i class='fa fa-check margin-r-5'></i>Enregistrer", enregistrer_id=None, enregistrer_name="submit",
              commandes_principales=[],
              ajouter=True,
              annuler=True, annuler_url=None,
              aide=True, aide_url="{% url 'aide_toc' %}",
              autres_commandes=[], css_class="commandes"):

    liste_commandes = []

    # Enregistrer
    if enregistrer:
        liste_commandes.append(StrictButton(enregistrer_label, title="Enregistrer", name=enregistrer_name, type="submit", css_class="btn-primary", id=enregistrer_id))

    # Autres commandes principales
    if commandes_principales:
        [liste_commandes.append(commande) for commande in commandes_principales]

    # Enregistrer et ajouter
    if ajouter:
        liste_commandes.append(StrictButton("<i class='fa fa-plus margin-r-5'></i>Enregistrer & Ajouter", title="Enregistrer & Ajouter", name="SaveAndNew", type="submit", css_class="btn-primary"))

    # Annuler
    if annuler:
        liste_commandes.append(HTML("""<a class="btn btn-danger" href='""" + annuler_url + """' title="Annuler"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """))

    # Autres commandes
    if autres_commandes:
        [liste_commandes.append(commande) for commande in autres_commandes]

    # Aide
    if aide:
        liste_commandes.append(HTML("""<a class="btn btn-default" href='""" + aide_url + """' target="_blank" title="Consulter l'aide"><i class="fa fa-life-saver margin-r-5"></i>Aide</a> """))

    return ButtonHolder(*liste_commandes, css_class=css_class)
