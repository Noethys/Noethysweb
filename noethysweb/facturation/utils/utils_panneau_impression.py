# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from core.models import ModeleImpression
from core.utils import utils_preferences


def Get_contexte(titre="Impression", categorie="facture", singulier="facture", pluriel="factures", colonnes_resume=[], avec_messages=False,
                 bouton_label="Aperçu PDF", bouton_icone="fa-file-pdf-o", bouton_onclick="impression_pdf()", bouton_title="",
                 annuler_label="Annuler"):
    """ Contexte du panneau d'impression commun aux pages d'impression et d'envoi par email (factures, rappels, attestations fiscales) """
    modeles_impression = {
        str(modele.pk): {"nom": modele.nom, "idmodele_document": modele.modele_document_id,
                         "modele_document": modele.modele_document.nom if modele.modele_document else "",
                         "options": json.loads(modele.options or "{}")}
        for modele in ModeleImpression.objects.select_related("modele_document").filter(categorie=categorie)}
    return {
        "titre": titre,
        "singulier": singulier,
        "pluriel": pluriel,
        "colonnes_resume": json.dumps(colonnes_resume),
        "avec_messages": avec_messages,
        "bouton_label": bouton_label,
        "bouton_icone": bouton_icone,
        "bouton_onclick": bouton_onclick,
        "bouton_title": bouton_title or bouton_label,
        "annuler_label": annuler_label,
        "symbole_monnaie": utils_preferences.Get_symbole_monnaie(),
        "modeles_impression_json": json.dumps(modeles_impression),
    }
