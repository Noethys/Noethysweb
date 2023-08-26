# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, uuid, json, time
logger = logging.getLogger(__name__)
from django.forms.models import model_to_dict
from core.models import Inscription, Activite, Consommation
from consommations.views.grille import Get_periode, Get_generic_data, Save_grille, Facturation


class Grille_virtuelle():
    """ Exemple d'utilisation :
    grille = Grille_virtuelle()
    grille.Recalculer_tout()
    grille.Ajouter(criteres={"unite": 1}, parametres={"etat": "reservation"})
    grille.Modifier(criteres={"date": datetime.date(2021, 7, 8)}, modifications={"etat": "attente"})
    grille.Supprimer(criteres={"unite": 1})
    grille.Enregistrer()
    """
    def __init__(self, request=None, idfamille=None, idindividu=None, idactivite=None, date_min=None, date_max=None):
        self.request = request
        self.chrono = time.time()
        self.conso_supprimees = []

        self.data_initial = {
            "mode": "individu",
            "idfamille": idfamille,
            "memos": {},
            "prestations": {},
            "consommations": {},
            "options": {},
            "periode": {'mode': 'jour', 'selections': {'jour': None}, 'periodes': ['%s;%s' % (date_min, date_max)]},
            "selection_individus": [idindividu,],
            "selection_activite": Activite.objects.get(pk=idactivite),
            "dict_suppressions": {"consommations": [], "prestations": [], "memos": []},
            "liste_inscriptions": Inscription.objects.select_related('individu', 'activite', 'groupe', 'famille', 'categorie_tarif').filter(famille__pk=idfamille, individu__pk=idindividu, activite__pk=idactivite),
        }

        # Récupération de la période
        self.data_initial = Get_periode(self.data_initial)

        # Incorpore les données génériques
        self.data_initial.update(Get_generic_data(self.data_initial))

        # Incorpore les prestations initiales
        self.data_initial["prestations"] = json.loads(self.data_initial["dict_prestations_json"])

        # Incorpore les événements
        dict_evenements = {}
        for evenement in json.loads(self.data_initial["liste_evenements_json"]):
            key_evenement = "%s_%s_%s" % (evenement["fields"]["date"], evenement["fields"]["unite"], evenement["fields"]["groupe"])
            dict_evenements.setdefault(key_evenement, [])
            dict_evenement = evenement["fields"]
            dict_evenement["pk"] = evenement["pk"]
            dict_evenements[key_evenement].append(dict_evenement)

        # Création des cases
        self.dict_cases = {}
        for date in self.data_initial["liste_dates"]:
            for inscription in self.data_initial["liste_inscriptions"]:
                for unite in self.data_initial["liste_unites"]:
                    for dict_evenement in dict_evenements.get("%s_%s_%s" % (date, unite.pk, inscription.groupe_id), [None,]):
                        key_case = "%s_%s_%s" % (date, inscription.pk, unite.pk)
                        if dict_evenement:
                            key_case = "event_%s_%d" % (key_case, dict_evenement["pk"])

                        self.dict_cases[key_case] = {
                            "date": str(date),
                            "inscription": inscription.pk,
                            "activite": inscription.activite_id,
                            "categorie_tarif": inscription.categorie_tarif_id,
                            "famille": inscription.famille_id,
                            "individu": inscription.individu_id,
                            "groupe": inscription.groupe_id,
                            "unite": unite.pk,
                            "evenement": dict_evenement["pk"] if dict_evenement else None,
                            "consommations": [],
                        }

        # Importation des conso initiales
        cases_touchees = {}
        consommations = {}
        for conso in self.data_initial["liste_conso"]:
            key_conso = "%s_%s" % (conso.date, conso.inscription_id)
            key_case = "%s_%s_%s" % (conso.date, conso.inscription_id, conso.unite_id)
            if conso.evenement:
                key_case = "event_%s_%d" % (key_case, conso.evenement_id)

            dict_conso = model_to_dict(conso)
            dict_conso["pk"] = conso.idconso
            dict_conso["key_case"] = key_case
            dict_conso["famille"] = conso.inscription.famille_id
            dict_conso["dirty"] = False

            consommations.setdefault(key_conso, [])
            consommations[key_conso].append(dict_conso)

            self.dict_cases[key_case]["consommations"].append(dict_conso)

        self.data_initial["cases_touchees"] = cases_touchees
        self.data_initial["consommations"] = consommations

    def Recalculer_tout(self):
        """ Recalcule toute les cases de la grille virtuelle """
        self.Modifier(criteres={}, modifications={})

    def Ajouter(self, criteres={}, parametres={}):
        for key_case, dict_case in self.dict_cases.items():
            valide = True
            for champ, valeur in criteres.items():
                if str(dict_case.get(champ, None)) != str(valeur):
                    valide = False

            # Vérifie qu'une conso n'existe pas déjà
            if self.dict_cases[key_case]["consommations"]:
                logger.debug("Impossible de créer une conso le %s car une conso existe déjà." % dict_case["date"])
                valide = False

            if valide:
                # Création d'une nouvelle conso
                key_conso = "%s_%s" % (dict_case["date"], dict_case["inscription"])
                conso = Consommation()
                dict_conso = model_to_dict(conso)
                dict_conso.update(dict_case)
                dict_conso["pk"] = uuid.uuid4()
                dict_conso["key_case"] = key_case
                dict_conso["etat"] = parametres.get("etat", "reservation")
                dict_conso["dirty"] = True
                dict_conso["evenement"] = dict_case["evenement"]
                dict_conso["heure_debut"] = parametres.get("heure_debut", None)
                dict_conso["heure_fin"] = parametres.get("heure_fin", None)

                logger.debug("Ajout d'une nouvelle conso : %s" % dict_conso)

                # Mémorisation de la conso
                self.data_initial["consommations"].setdefault(key_conso, [])
                self.data_initial["consommations"][key_conso].append(dict_conso)
                if key_case not in self.data_initial["cases_touchees"]:
                    self.data_initial["cases_touchees"][key_case] = self.dict_cases[key_case]

    def Modifier(self, criteres={}, modifications={}):
        for key_conso, liste_conso in self.data_initial["consommations"].items():
            for dict_conso in liste_conso:

                # Vérifie que la conso répond aux critères
                valide = True
                for champ, valeur in criteres.items():
                    if str(dict_conso.get(champ, None)) != str(valeur):
                        valide = False

                # Vérifie que la conso n'est pas facturée
                if str(dict_conso["prestation"]) in self.data_initial["prestations"]:
                    if self.data_initial["prestations"][str(dict_conso["prestation"])]["facture"]:
                        logger.debug("La prestation du %s ne peut pas être modifiée car elle est déjà facturée." % dict_conso["date"])
                        valide = False

                if valide:
                    dict_conso["dirty"] = True

                    # Applique les modifications
                    for champ, valeur in modifications.items():
                        dict_conso[champ] = valeur

                    # Mémorise les modifications de la conso
                    key_case = dict_conso["key_case"]
                    if key_case not in self.data_initial["cases_touchees"]:
                        self.data_initial["cases_touchees"][key_case] = self.dict_cases[key_case]

    def Supprimer(self, criteres={}):
        for key_conso, liste_conso in self.data_initial["consommations"].items():
            liste_conso_finale = []
            for dict_conso in liste_conso:

                # Vérifie que la conso répond aux critères
                valide = True
                for champ, valeur in criteres.items():
                    if dict_conso.get(champ, None) != valeur:
                        valide = False

                # Vérifie que la conso n'est pas déjà pointée
                if dict_conso["etat"] in ("present", "absentj", "absenti"):
                    logger.debug("Impossible de supprimer une conso déjà pointée : %s" % dict_conso["date"])
                    valide = False

                # Vérifie que la conso n'est pas facturée
                if str(dict_conso["prestation"]) in self.data_initial["prestations"]:
                    if self.data_initial["prestations"][str(dict_conso["prestation"])]["facture"]:
                        logger.debug("La prestation du %s ne peut pas être supprimée car elle est déjà facturée." % dict_conso["date"])
                        valide = False

                if valide:
                    self.conso_supprimees.append(dict_conso["pk"])

                    # Mémorise la case touchée
                    key_case = dict_conso["key_case"]
                    if key_case not in self.data_initial["cases_touchees"]:
                        self.data_initial["cases_touchees"][key_case] = self.dict_cases[key_case]
                else:
                    liste_conso_finale.append(dict_conso)
            self.data_initial["consommations"][key_conso] = liste_conso_finale

    def Enregistrer(self):
        # Calcul de la facturation
        facturation = Facturation(donnees=self.data_initial)
        donnees_retour = facturation.Facturer()

        # Modifie le IDprestation des consommations
        for key_case, idprestation in donnees_retour["modifications_idprestation"].items():
            for key_conso, liste_conso in self.data_initial["consommations"].items():
                for dict_conso in liste_conso:
                    if dict_conso["key_case"] == key_case:
                        dict_conso["prestation"] = idprestation

        # Ajoute les nouvelles prestations
        self.data_initial["prestations"].update(donnees_retour["nouvelles_prestations"])

        donnees_save = {
            "selection_activite": self.data_initial["selection_activite"],
            "prestations": self.data_initial["prestations"],
            "consommations": self.data_initial["consommations"],
            "suppressions": {
                "consommations": self.conso_supprimees,
                "prestations": [int(idprestation) for idprestation in donnees_retour["anciennes_prestations"]],
                "memos": []
            },
        }
        Save_grille(request=self.request, donnees=donnees_save)
        logger.debug("Temps d'enregistrement de la grille virtuelle : " + str(time.time() - self.chrono))
