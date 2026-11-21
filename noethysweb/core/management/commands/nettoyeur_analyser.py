# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Analyse du Nettoyeur en ligne de commande, sans aucune modification des données.

Exemples :
    python manage.py nettoyeur_analyser
    python manage.py nettoyeur_analyser --operations familles_supprimer,pieces_expirees
    python manage.py nettoyeur_analyser --delai 24
    python manage.py nettoyeur_analyser --format json
    python manage.py nettoyeur_analyser --operations familles_supprimer --details
"""

import datetime, json
from django.core.management.base import BaseCommand, CommandError
from outils.utils import nettoyeur
from outils.utils.nettoyeur import utils_delais
from outils.utils.nettoyeur.base import CATEGORIES, CHOIX_DELAIS, Get_date_limite, Formate_taille, Formate_nombre


class Command(BaseCommand):
    help = "Affiche les résultats de l'analyse du Nettoyeur (lecture seule, aucune donnée n'est modifiée)"

    def add_arguments(self, parser):
        parser.add_argument("--operations", type=str, default="",
                            help="Codes des opérations à analyser, séparés par des virgules (toutes par défaut). Utilisez --liste pour les connaître.")
        parser.add_argument("--delai", type=int, default=None, choices=[mois for mois, label in CHOIX_DELAIS],
                            help="Délai en mois appliqué à toutes les opérations (par défaut : délais enregistrés dans le Nettoyeur, sinon délais conseillés)")
        parser.add_argument("--format", type=str, default="texte", choices=["texte", "json"], help="Format de sortie")
        parser.add_argument("--details", action="store_true",
                            help="Affiche aussi la liste des éléments concernés. Attention : elle peut contenir des données personnelles.")
        parser.add_argument("--suggestions", action="store_true", help="N'affiche que les opérations conseillées")
        parser.add_argument("--liste", action="store_true", help="Affiche la liste des opérations disponibles")

    def handle(self, *args, **kwargs):
        operations = nettoyeur.Get_operations(cache={})

        if kwargs["liste"]:
            for operation in operations:
                self.stdout.write("%-24s %s" % (operation.code, operation.titre))
            return

        # Sélection des opérations
        if kwargs["operations"]:
            codes = [code.strip() for code in kwargs["operations"].split(",") if code.strip()]
            inconnus = [code for code in codes if code not in [operation.code for operation in operations]]
            if inconnus:
                raise CommandError("Opération(s) inconnue(s) : %s. Utilisez --liste pour connaître les codes." % ", ".join(inconnus))
            operations = [operation for operation in operations if operation.code in codes]

        # Analyse
        delais = utils_delais.Get_delais()
        resultats = []
        for operation in operations:
            if operation.delai_defaut is None:
                date_limite = None
            elif kwargs["delai"]:
                date_limite = Get_date_limite(kwargs["delai"])
                erreur = operation.Check_date_limite(date_limite)
                if erreur:
                    resultats.append({"operation": operation, "erreur": erreur})
                    continue
            else:
                date_limite = utils_delais.Get_date_limite_operation(operation, delais)
            try:
                resultat = operation.Analyser(date_limite=date_limite)
            except Exception as err:
                resultats.append({"operation": operation, "erreur": str(err)})
                continue
            suggestion = operation.Is_suggestion(resultat)
            if kwargs["suggestions"] and not suggestion:
                continue
            resultats.append({"operation": operation, "date_limite": date_limite, "resultat": resultat, "suggestion": suggestion})

        if kwargs["format"] == "json":
            self.Afficher_json(resultats, details=kwargs["details"])
        else:
            self.Afficher_texte(resultats, details=kwargs["details"])

    def Afficher_json(self, resultats=[], details=False):
        donnees = {"date_analyse": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "operations": []}
        for item in resultats:
            operation = item["operation"]
            ligne = {"code": operation.code, "titre": operation.titre, "categorie": operation.categorie}
            if "erreur" in item:
                ligne["erreur"] = item["erreur"]
            else:
                resultat = item["resultat"]
                ligne.update({
                    "date_limite": item["date_limite"].strftime("%Y-%m-%d") if item["date_limite"] else None,
                    "nbre": resultat.nbre, "octets": resultat.octets, "octets_estimes": resultat.octets_estimes,
                    "nbre_exclus": resultat.nbre_exclus, "message_exclus": resultat.message_exclus or None,
                    "detail": resultat.detail or None, "suggestion": item["suggestion"],
                })
                if details and resultat.elements is not None:
                    ligne["elements"] = [element.To_dict() for element in resultat.elements]
            donnees["operations"].append(ligne)
        donnees["total"] = {
            "nbre": sum([item["resultat"].nbre for item in resultats if "resultat" in item]),
            "octets": sum([item["resultat"].octets for item in resultats if "resultat" in item]),
        }
        self.stdout.write(json.dumps(donnees, ensure_ascii=False, indent=2))

    def Afficher_texte(self, resultats=[], details=False):
        self.stdout.write("Analyse du Nettoyeur du %s (aucune donnée modifiée)" % datetime.datetime.now().strftime("%d/%m/%Y à %H:%M"))
        total_nbre, total_octets = 0, 0
        for code_categorie, label_categorie, icone in CATEGORIES:
            items = [item for item in resultats if item["operation"].categorie == code_categorie]
            if not items:
                continue
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(label_categorie))
            for item in items:
                operation = item["operation"]
                if "erreur" in item:
                    self.stdout.write("  %-58s %s" % (operation.titre[:58], self.style.ERROR("Erreur : %s" % item["erreur"])))
                    continue
                resultat = item["resultat"]
                total_nbre += resultat.nbre
                total_octets += resultat.octets
                valeur = Formate_nombre(resultat.nbre)
                if resultat.octets:
                    valeur += " - %s%s" % ("env. " if resultat.octets_estimes else "", Formate_taille(resultat.octets))
                date = " (avant le %s)" % item["date_limite"].strftime("%d/%m/%Y") if item["date_limite"] else ""
                ligne = "  %-58s %20s%s" % (operation.titre[:58], valeur, date)
                if item["suggestion"]:
                    ligne = self.style.WARNING(ligne + "  [conseillé]")
                self.stdout.write(ligne)
                if resultat.message_exclus:
                    self.stdout.write("      %s" % resultat.message_exclus)
                if resultat.detail:
                    self.stdout.write("      %s" % resultat.detail)
                if details and resultat.elements:
                    for element in resultat.elements:
                        texte = "      - %s" % element.label
                        if element.info:
                            texte += " (%s)" % element.info
                        if element.octets:
                            texte += " - %s" % Formate_taille(element.octets)
                        self.stdout.write(texte)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Total : %s élément(s)%s" % (Formate_nombre(total_nbre), " - %s" % Formate_taille(total_octets) if total_octets else "")))
