# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import Famille, Individu, Rattachement, Inscription, Consommation, Evenement, Ouverture, MemoJournee, Prestation
import datetime

# Exemple d'utilisation dans la console python : from core.utils.utils_fake_data import Generate_ouvertures

def Generate_evenements():
    """ Génération d'événements """
    Evenement.objects.create(date="2019-02-14", nom="1", heure_debut="10:00", heure_fin="12:00", activite_id=1, groupe_id=1, unite_id=15)

def Generate_ouvertures():
    """ Génération d'événements """
    Ouverture.objects.create(date="2019-02-12", activite_id=1, groupe_id=1, unite_id=14)
    Ouverture.objects.create(date="2019-02-13", activite_id=1, groupe_id=1, unite_id=14)
    Ouverture.objects.create(date="2019-02-14", activite_id=1, groupe_id=1, unite_id=14)
    Ouverture.objects.create(date="2019-02-15", activite_id=1, groupe_id=1, unite_id=14)

def Generate_memos():
    """ Génération de mémos journaliers """
    MemoJournee.objects.create(date="2019-02-12", individu_id=3, texte="Ceci est un test")

def Generate_prestations():
    """ Génération de mémos journaliers """
    Prestation.objects.create(date="2019-02-12", categorie="consommation", label="Journée sans repas", montant_initial="22.00", montant="22.00",
                              activite_id=1, tarif_id=4, famille_id=1, individu_id=58, categorie_tarif_id=1)

def Generate_familles():
    """ Génération de familles, individus, inscriptions et consommations"""
    for index in range(100, 200):
        famille = Famille.objects.create()
        parent = Individu.objects.create(civilite=1, nom="PERE%d" % index, prenom="Père%d" % index)
        enfant = Individu.objects.create(civilite=4, nom="ENFANT%d" % index, prenom="Enfant%d" % index)
        Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=parent)
        Rattachement.objects.create(categorie=2, titulaire=False, famille=famille, individu=enfant)
        inscription = Inscription.objects.create(activite_id=1, categorie_tarif_id=1, famille=famille, groupe_id=1, individu=enfant)
        for jour in (11, 12, 13, 14, 15):
            Consommation.objects.create(date=datetime.date(2019, 2, jour), activite_id=1, etat="reservation", groupe_id=1, individu=enfant, inscription=inscription, unite_id=1)
            Consommation.objects.create(date=datetime.date(2019, 2, jour), activite_id=1, etat="reservation", groupe_id=1, individu=enfant, inscription=inscription, unite_id=2)
        print("Famille %d ok" % index)
