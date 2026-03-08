# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, datetime, uuid, json, csv
from django.conf import settings
from django.db.models import Q
from core.models import Activite, Consommation, Vacance, LISTE_ETATS_CONSO
from core.utils import utils_dates
from facturation.utils.utils_export_ecritures import BaseExporter


COLONNES_EXPORTS = [
    {"code": "idconso", "titre": "ID Consommation", "description": "N° d'identification de la consommation."},
    {"code": "idindividu", "titre": "ID Individu", "description": "N° d'identification aléatoire attribué à l'individu."},
    {"code": "age", "titre": "Age de l'individu", "description": "Age de l'individu à la date de la consommation."},
    {"code": "sexe", "titre": "Sexe de l'individu", "description": "Sexe de l'individu."},
    {"code": "idfamille", "titre": "ID famille", "description": "N° d'identification aléatoire attribué à la famille."},
    {"code": "nom_activite", "titre": "Nom de l'activité", "description": "Nom de l'activité."},
    {"code": "date", "titre": "Date", "description": "Date de la consommation."},
    {"code": "periode", "titre": "Période", "description": "Nom de la période. Ex : Vacances de février 2026, Hors vacances janvier-février 2026..."},
    {"code": "nom_unite", "titre": "Nom de l'unité", "description": "Nom de l'unité de consommation. Ex : Journée, Repas, Sortie..."},
    {"code": "nom_groupe", "titre": "Nom du groupe", "description": "Nom du groupe. Ex : Maternels, les alouettes, groupe du lundi 18h..."},
    {"code": "heure_debut", "titre": "Heure début", "description": "Heure de début de la consommation."},
    {"code": "heure_fin", "titre": "Heure fin", "description": "Heure de fin de la consommation."},
    {"code": "etat", "titre": "Etat", "description": "Etat de la consommation. Ex : Réservation, attente, demande, présence, absence injustifiée, absence justifiée."},
    {"code": "date_saisie", "titre": "Date de saisie", "description": "Date de saisie de la consommation"},
    {"code": "categorie_tarif", "titre": "Catégorie de tarif", "description": "Catégorie de tarif associée à la consommation. Ex : Commune, hors commune..."},
    {"code": "quantite", "titre": "Quantité", "description": "Quantité associée à la consommation. 1 par défaut."},
    {"code": "nom_evenement", "titre": "Nom événement", "description": "Nom de l'évènement. Ex : Patinoire, piscine..."},
]


class Exporter(BaseExporter):
    def __init__(self, request=None, options=None):
        self.options = options
        self.request = request

    def Generer(self):
        self.nom_fichier = "export_analyse_ia_frequentation_%s.csv" % datetime.date.today().strftime("%Y-%m-%d")
        self.Creer_repertoire_sortie(nom_rep="analyse_ia_frequentation")
        if not self.Creation_fichier():
            return False
        return os.path.join(settings.MEDIA_URL, self.rep_base, "analyse_ia_frequentation", self.nom_fichier)

    def Creer_repertoire_sortie(self, nom_rep=""):
        self.rep_base = os.path.join("temp", str(uuid.uuid4()))
        self.rep_destination = os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_rep)
        os.makedirs(self.rep_destination)

    def Creation_fichier(self):
        # Activités
        param_activites = json.loads(self.options["activites"])
        if param_activites["type"] == "groupes_activites":
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

        # Période
        date_debut, date_fin = utils_dates.ConvertDateRangePicker(self.options["periode"])

        # Importation des consommations
        conditions = Q(activite__in=liste_activites, date__gte=date_debut, date__lte=date_fin)
        liste_consommations = Consommation.objects.select_related("individu", "inscription", "activite", "unite",
                                                                  "groupe", "categorie_tarif", "evenement").filter(conditions)

        # Préparation des colonnes
        codes_titres = {item["code"]: item["titre"] for item in COLONNES_EXPORTS}

        # Préparation du dict des ID virtuels
        dict_id_virtuels = {"individu": {}, "famille": {}}

        def Get_id_virtuels(id=None, categorie="individu"):
            if id in dict_id_virtuels[categorie]:
                return dict_id_virtuels[categorie][id]
            else:
                dict_id_virtuels[categorie][id] = len(dict_id_virtuels[categorie]) + 1
                return dict_id_virtuels[categorie][id]

        # Préparation des états de consommations
        dict_etats = {code: label for code, label in LISTE_ETATS_CONSO}

        # Préparation des noms de période
        LISTE_MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        periodes = []
        liste_vacances = Vacance.objects.all().order_by("date_debut")
        for index, vacance in enumerate(liste_vacances):

            # Vacances
            label = "Vacances %s %d" % (vacance.nom, vacance.annee)
            periodes.append({"date_debut": vacance.date_debut, "date_fin": vacance.date_fin, "nom": label})

            # Hors vacances
            date_debut_temp = vacance.date_fin + datetime.timedelta(days=1)
            if len(liste_vacances) > index + 1:
                date_fin_temp = liste_vacances[index + 1].date_debut - + datetime.timedelta(days=1)
                annee = vacance.annee
                if vacance.nom.startswith("N"):
                    annee += 1
                label = "Hors vacances %s-%s %d" % (LISTE_MOIS[date_debut_temp.month - 1], LISTE_MOIS[date_fin_temp.month - 1], annee)
                periodes.append({"date_debut": date_debut_temp, "date_fin": date_fin_temp, "nom": label})
            index += 1

        def Get_periode(date=None):
            for periode in periodes:
                if periode["date_debut"] <= date <= periode["date_fin"]:
                    return periode["nom"]
            return None

        # Création du csv
        with open(os.path.join(self.rep_destination, self.nom_fichier), "w", newline="", encoding="utf-8") as fichier_csv:
            writer = csv.DictWriter(fichier_csv, fieldnames=[item["titre"] for item in COLONNES_EXPORTS], delimiter=";")
            writer.writeheader()

            for conso in liste_consommations:
                ligne = {}
                ligne["idconso"] = conso.pk
                ligne["idindividu"] = Get_id_virtuels(id=conso.individu_id, categorie="individu")
                ligne["age"] = conso.individu.Get_age(today=conso.date)
                ligne["sexe"] = conso.individu.Get_sexe()
                ligne["idfamille"] = Get_id_virtuels(id=conso.inscription.famille_id, categorie="famille")
                ligne["nom_activite"] = conso.activite.nom
                ligne["date"] = conso.date
                ligne["periode"] = Get_periode(conso.date)
                ligne["nom_unite"] = conso.unite.nom
                ligne["nom_groupe"] = conso.groupe.nom
                ligne["heure_debut"] = conso.heure_debut
                ligne["heure_fin"] = conso.heure_fin
                ligne["etat"] = dict_etats[conso.etat]
                ligne["date_saisie"] = conso.date_saisie
                ligne["categorie_tarif"] = conso.categorie_tarif.nom
                ligne["quantite"] = conso.quantite
                ligne["nom_evenement"] = conso.evenement.nom if conso.evenement else None

                # Remplace le code par le titre de la colonne puis mémorise la ligne
                writer.writerow({codes_titres[code]: valeur for code, valeur in ligne.items()})

        return True
