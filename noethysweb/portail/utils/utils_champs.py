# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import PortailChamp


class Champ():
    def __init__(self, *args, **kwargs):
        self.page = kwargs.get("page", None)
        self.code = kwargs.get("code", None)
        self.label = kwargs.get("label", None)
        self.representant = kwargs.get("representant", None)
        self.enfant = kwargs.get("enfant", None)
        self.contact = kwargs.get("contact", None)
        self.famille = kwargs.get("famille", None)

    def __repr__(self):
        return "<%s:%s>" % (self.page, self.code)


LISTE_CHAMPS = [

    Champ(page="famille_caisse", code="caisse", label="Caisse", famille="AFFICHER"),
    Champ(page="famille_caisse", code="num_allocataire", label="N° allocataire", famille="AFFICHER"),
    Champ(page="famille_caisse", code="allocataire", label="Nom de l'allocataire", famille="AFFICHER"),
    Champ(page="famille_caisse", code="autorisation_cafpro", label="Autorisation CAFPRO", famille="AFFICHER"),

    Champ(page="famille_consentements", code="consentements", label="Consentements", famille="AFFICHER"),

    Champ(page="individu_identite", code="nom", label="Nom de famille", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="civilite", label="Civilité", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="prenom", label="Prénom", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="date_naiss", label="Date de naissance", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="cp_naiss", label="CP naissance", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="ville_naiss", label="Ville de naissance", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_identite", code="type_sieste", label="Type de sieste", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_coords", code="type_adresse", label="Type d'adresse", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="adresse_auto", label="Adresse rattachée", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="rue_resid", label="Rue de résidence", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="cp_resid", label="CP de résidence", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="ville_resid", label="Ville de résidence", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="secteur", label="Secteur", representant="AFFICHER", enfant="AFFICHER", contact="AFFICHER"),
    Champ(page="individu_coords", code="tel_domicile", label="Tél fixe", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="tel_mobile", label="Tél portable", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="mail", label="Email", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="categorie_travail", label="Catégorie socio-professionnelle", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="profession", label="Profession", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="employeur", label="Employeur", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="travail_tel", label="Tél pro.", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),
    Champ(page="individu_coords", code="travail_mail", label="Email pro.", representant="AFFICHER", enfant="MASQUER", contact="AFFICHER"),

    Champ(page="individu_questionnaire", code="questionnaire", label="Questionnaire", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_regimes_alimentaires", code="regimes_alimentaires", label="Régimes alimentaires", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_maladies", code="maladies", label="Maladies", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_medecin", code="medecin", label="Médecin", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_vaccinations", code="vaccinations", label="Vaccinations", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_infos_medicales", code="infos_medicales", label="Information médicale", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_assurances", code="assurances", label="Assurance", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),

    Champ(page="individu_contacts", code="contacts", label="Contact", representant="MASQUER", enfant="AFFICHER", contact="MASQUER"),
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

def Get_labels_champs():
    dict_labels = {}
    for champ in LISTE_CHAMPS:
        dict_labels[champ.code] = champ.label
    return dict_labels
