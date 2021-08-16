# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import PortailChamp


class Champ():
    def __init__(self, *args, **kwargs):
        self.page = kwargs.get("page", None)
        self.code = kwargs.get("code", None)
        self.representant = kwargs.get("representant", None)
        self.enfant = kwargs.get("enfant", None)
        self.contact = kwargs.get("contact", None)
        self.famille = kwargs.get("famille", None)

    def __repr__(self):
        return "<%s:%s>" % (self.page, self.code)


LISTE_CHAMPS = [

    Champ(page="famille_caisse", code="caisse", famille="AFFICHER"),
    Champ(page="famille_caisse", code="num_allocataire", famille="AFFICHER"),
    Champ(page="famille_caisse", code="allocataire", famille="AFFICHER"),
    Champ(page="famille_caisse", code="autorisation_cafpro", famille="AFFICHER"),

    Champ(page="famille_consentements", code="consentements", famille="AFFICHER"),

    Champ(page="individu_identite", code="nom", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="civilite", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="prenom", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="date_naiss", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="cp_naiss", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="ville_naiss", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="type_sieste", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_coords", code="type_adresse", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="adresse_auto", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="rue_resid", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="cp_resid", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="ville_resid", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="secteur", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="tel_domicile", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="tel_mobile", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="mail", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="categorie_travail", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="profession", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="employeur", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="travail_tel", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="travail_mail", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),

    Champ(page="individu_questionnaire", code="questionnaire", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_regimes_alimentaires", code="regimes_alimentaires", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_maladies", code="maladies", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_medecin", code="medecin", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_infos_medicales", code="infos_medicales", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_assurances", code="assurances", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_contacts", code="contacts", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),
]

def Get_liste_champs():
    dict_champs_db = {"%s:%s" % (champ_db.page, champ_db.code): champ_db for champ_db in PortailChamp.objects.all()}
    liste_champs_temp = []
    for champ in LISTE_CHAMPS:
        key = "%s:%s" % (champ.page, champ.code)
        if key in dict_champs_db:
            champ.representant = dict_champs_db[key].representant
            champ.enfant = dict_champs_db[key].enfant
            champ.contact = dict_champs_db[key].contact
        liste_champs_temp.append(champ)
    return liste_champs_temp

def Get_codes_champs_page(page="identite", categorie="representant", liste_champs=[]):
    if not liste_champs:
        liste_champs = Get_liste_champs()
    if categorie == 1: categorie = "representant"
    if categorie == 2: categorie = "enfant"
    if categorie == 3: categorie = "contact"
    liste_champs_temp = []
    for champ in liste_champs:
        if champ.page == page and getattr(champ, categorie) != "MASQUER":
            liste_champs_temp.append(champ.code)
    return liste_champs_temp
