# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy, json
from django.core.cache import cache
from core.models import PortailChamp, Rattachement, PortailRenseignement


class Champ():
    def __init__(self, *args, **kwargs):
        self.page = kwargs.get("page", None)
        self.code = kwargs.get("code", None)
        self.label = kwargs.get("label", None)
        self.representant = kwargs.get("representant", None)
        self.enfant = kwargs.get("enfant", None)
        self.contact = kwargs.get("contact", None)
        self.famille = kwargs.get("famille", None)
        self.choix_obligatoire = kwargs.get("choix_obligatoire", False)

    def __repr__(self):
        return "<%s:%s>" % (self.page, self.code)


LISTE_CHAMPS = [

    Champ(page="famille_caisse", code="caisse", label="Caisse d'allocation", famille="MODIFIABLE", choix_obligatoire=True),
    Champ(page="famille_caisse", code="num_allocataire", label="N° allocataire", famille="MODIFIABLE", choix_obligatoire=True),
    Champ(page="famille_caisse", code="allocataire", label="Nom de l'allocataire", famille="MODIFIABLE", choix_obligatoire=True),
    Champ(page="famille_caisse", code="autorisation_cafpro", label="Autorisation CAFPRO", famille="MODIFIABLE"),

    Champ(page="famille_questionnaire", code="questionnaire", label="Questionnaire", famille="MODIFIABLE"),

    Champ(page="famille_parametres", code="email_blocage", label="Blocage envois Emails", famille="MODIFIABLE"),
    Champ(page="famille_parametres", code="mobile_blocage", label="Blocage envois SMS", famille="MODIFIABLE"),

    # Champ(page="famille_quotients", code="quotients", label="Quotients", famille="MASQUER"),

    Champ(page="famille_consentements", code="consentements", label="Consentements", famille="MODIFIABLE"),

    Champ(page="individu_identite", code="nom", label="Nom de famille", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="nom_jfille", label="Nom de naissance", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="civilite", label="Civilité", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="prenom", label="Prénom", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="date_naiss", label="Date de naissance", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="cp_naiss", label="CP naissance", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="ville_naiss", label="Ville de naissance", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="pays_naiss_insee", label="Pays de naissance", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_identite", code="type_sieste", label="Type de sieste", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER", choix_obligatoire=True),

    Champ(page="individu_coords", code="type_adresse", label="Type d'adresse", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE"),
    Champ(page="individu_coords", code="adresse_auto", label="Adresse rattachée", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE"),
    Champ(page="individu_coords", code="rue_resid", label="Rue de résidence", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="cp_resid", label="CP de résidence", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="ville_resid", label="Ville de résidence", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="secteur", label="Secteur", representant="MODIFIABLE", enfant="MODIFIABLE", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="tel_domicile", label="Tél fixe", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="tel_mobile", label="Tél portable", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="mail", label="Email", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="categorie_travail", label="Catégorie socio-professionnelle", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="profession", label="Profession", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="employeur", label="Employeur", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="travail_tel", label="Tél pro.", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),
    Champ(page="individu_coords", code="travail_mail", label="Email pro.", representant="MODIFIABLE", enfant="MASQUER", contact="MODIFIABLE", choix_obligatoire=True),

    Champ(page="individu_questionnaire", code="questionnaire", label="Questionnaire", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),

    Champ(page="individu_regimes_alimentaires", code="regimes_alimentaires", label="Régimes alimentaires", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),

    Champ(page="individu_maladies", code="maladies", label="Maladies", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),

    Champ(page="individu_medecin", code="medecin", label="Médecin", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),

    Champ(page="individu_vaccinations", code="vaccinations", label="Vaccinations", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),

    Champ(page="individu_informations", code="informations", label="Informations", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),

    Champ(page="individu_assurances", code="assurances", label="Assurance", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),

    Champ(page="individu_contacts", code="contacts", label="Contact d'urgence", representant="MASQUER", enfant="MODIFIABLE", contact="MASQUER"),
]

def Get_liste_champs():
    dict_champs_db = cache.get('parametres_portail_champs')
    if not dict_champs_db:
        dict_champs_db = {"%s:%s" % (champ_db.page, champ_db.code): champ_db for champ_db in PortailChamp.objects.all()}
        cache.set('parametres_portail_champs', dict_champs_db)

    liste_champs_temp = []
    for champ in copy.copy(LISTE_CHAMPS):
        key = "%s:%s" % (champ.page, champ.code)
        if key in dict_champs_db:
            champ.representant = dict_champs_db[key].representant
            champ.enfant = dict_champs_db[key].enfant
            champ.contact = dict_champs_db[key].contact
            champ.famille = dict_champs_db[key].famille
        liste_champs_temp.append(champ)
    return liste_champs_temp

def Get_champs_page(page=None, categorie="representant", liste_champs=[], etat=None):
    if not liste_champs:
        liste_champs = Get_liste_champs()
    if categorie == 1: categorie = "representant"
    if categorie == 2: categorie = "enfant"
    if categorie == 3: categorie = "contact"
    dict_champs = {}
    for champ in liste_champs:
        if champ.page == page or (not page and getattr(champ, categorie) == etat):
            dict_champs[champ.code] = getattr(champ, categorie)
    return dict_champs

def Get_labels_champs():
    dict_labels = {}
    for champ in LISTE_CHAMPS:
        dict_labels[champ.code] = champ.label
    return dict_labels

def Get_renseignements_manquants(famille=None):
    rattachements = list(Rattachement.objects.prefetch_related("individu").filter(famille=famille, individu__deces=False).exclude(individu__in=famille.individus_masques.all()))

    # Importation des renseignements en attente de validation
    renseignements = PortailRenseignement.objects.filter(famille=famille, etat="ATTENTE", validation_auto=False).order_by("date")
    dict_renseignements = {renseignement.code: json.loads(renseignement.nouvelle_valeur) for renseignement in renseignements}

    # Récupère les noms des champs
    dict_labels = Get_labels_champs()

    dict_renseignements_manquants = {"NBRE": 0, "FICHES": {}}
    for rattachement in [None] + rattachements:
        categorie = rattachement.categorie if rattachement else "famille"
        dict_champs = Get_champs_page(page=None, categorie=categorie, etat="OBLIGATOIRE")

        for code in dict_champs.keys():

            # Recherche la valeur dans la fiche famille ou dans les fiches individuelles
            if rattachement:
                valeur = getattr(rattachement.individu, code, None)
            else:
                valeur = getattr(famille, code, None)

            # Recherche si une valeur existe déjà dans les renseignements modifiés
            if code in dict_renseignements:
                valeur = dict_renseignements[code]

            # Exige le nom de naissance uniquement si la civilité = 3 (Madame)
            if code == "nom_jfille" and rattachement and rattachement.individu.civilite != 3:
                valeur = True

            if not valeur:
                label = dict_labels[code]
                individu = rattachement.individu if rattachement else None
                dict_renseignements_manquants["FICHES"].setdefault(individu, [])
                dict_renseignements_manquants["FICHES"][individu].append(label)
                dict_renseignements_manquants["NBRE"] += 1

    return dict_renseignements_manquants
