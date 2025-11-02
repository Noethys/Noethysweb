# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.models import Collaborateur, GroupeCollaborateurs
from collaborateurs.forms.importer_collaborateurs import DICT_TYPE_DONNEE


class Anomalie:
    def __init__(self, *args, **kwargs):
        """ Indiquer la ligne OU la donnée """
        self.donnee = kwargs.get("donnee", None)
        self.ligne = kwargs.get("ligne", None)
        self.texte_erreur = kwargs.get("texte_erreur", None)
        self.nom_colonne = self.donnee.classe_importer.dict_type_donnee[self.donnee.code]["titre"] if self.donnee else None

    def Get_texte_rapport(self):
        """ Renvoie un texte pour l'anomalie sur cette donnée """
        if self.donnee:
            return "Ligne %d - Colonne %s : %s" % (self.donnee.num_ligne+1, self.nom_colonne, self.texte_erreur)
        return "Ligne %d : %s" % (self.ligne.num_ligne+1, self.texte_erreur)


class Donnee:
    def __init__(self, *args, **kwargs):
        self.classe_importer = kwargs.get("classe_importer", None)
        self.code = kwargs.get("code", None)
        self.valeur = kwargs.get("valeur", None)
        self.num_ligne = int(kwargs.get("num_ligne", 0))
        self.num_colonne = int(kwargs.get("num_colonne", 0))

    def Verifier(self):
        """ Vérifie la cohérence de cette donnée """
        if "CIVILITE" in self.code and self.valeur.strip().lower() not in ("m", "monsieur", "mr", "m.", "h", "homme", "melle", "mademoiselle", "mme", "madame", "femme", "f"):
            return Anomalie(donnee=self, texte_erreur="Cette valeur ne fait pas partie des choix disponibles.")
        if "DATE" in self.code and self.valeur:
            try:
                test = datetime.datetime.strptime(self.valeur,"%d/%m/%Y")
            except:
                return Anomalie(donnee=self, texte_erreur="Cette date ne semble pas cohérente.")
        if "TELEPHONE" in self.code and self.valeur:
            if not self.Formate_telephone(self.valeur):
                return Anomalie(donnee=self, texte_erreur="Ce numéro de téléphone ne semble pas cohérent.")
        if "EMAIL" in self.code and self.valeur:
            if "@" not in self.valeur:
                return Anomalie(donnee=self, texte_erreur="Cette adresse Email ne semble pas cohérente.")
        return True

    def Get_valeur_finale(self):
        """ Formate la donnée correctement pour la base """
        if self.valeur:
            self.valeur = self.valeur.strip()
        if "CIVILITE" in self.code and self.valeur:
            if self.valeur.lower() in ("m", "monsieur", "mr", "m.", "h", "homme"): return "M"
            if self.valeur.lower() in ("mme", "madame", "femme", "melle", "mademoiselle", "f"): return "MME"
            return self.valeur.upper()
        if self.code.startswith("NOM") and self.valeur:
            return self.valeur.upper()
        if self.code.startswith("NOMJFILLE") and self.valeur:
            return self.valeur.upper()
        if self.code.startswith("PRENOM") and self.valeur:
            return self.valeur.title()
        if "DATE" in self.code:
            return datetime.datetime.strptime(self.valeur,"%d/%m/%Y")
        if "VILLE" in self.code:
            return self.valeur.upper()
        if "RUE" in self.code:
            return self.valeur.title()
        if "TELEPHONE" in self.code:
            return self.Formate_telephone(self.valeur)
        return self.valeur

    def Formate_telephone(self, tel=""):
        try:
            return "{0}{1}.{2}{3}.{4}{5}.{6}{7}.{8}{9}.".format(*[x for x in tel if x in "0123456789"])
        except:
            return None


class Ligne:
    def __init__(self, *args, **kwargs):
        self.classe_importer = kwargs.get("classe_importer", None)
        self.type_import = kwargs.get("type_import", "COLLABORATEURS")
        self.num_ligne = int(kwargs.get("num_ligne", 0))
        self.donnees = kwargs.get("donnees", {})
        [setattr(self, code, donnee.Get_valeur_finale()) for code, donnee in self.donnees.items()]

    def Verifier(self):
        """ Vérifier la cohérence des données de la ligne """
        # Vérification des données une par une
        for donnee in self.donnees.values():
            resultat = donnee.Verifier()
            if resultat != True:
                self.classe_importer.anomalies.append(resultat)

        # Vérification de la cohérence globale de la ligne
        if self.type_import == "COLLABORATEURS":
            # Vérifie qu'il y a au moins une civilité et un nom dans la ligne
            if "CIVILITE" not in self.donnees:
                self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Une ligne doit comporter obligatoirement une civilité."))
            if "NOM" not in self.donnees:
                self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Une ligne doit comporter obligatoirement un nom de famille."))
            if "PRENOM" not in self.donnees:
                self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Une ligne doit comporter obligatoirement un prénom."))

class Importer:
    def __init__(self, type_import="COLLABORATEURS", donnees_tableau=[], colonnes_affectees={}, groupes=[]):
        self.type_import = type_import
        self.colonnes_affectees = colonnes_affectees
        self.groupes = groupes
        self.anomalies = []
        self.avertissements = []

        # Importation des données générales
        self.dict_type_donnee = {item["code"]: item for item in DICT_TYPE_DONNEE[type_import]}

        # Importation des lignes
        self.lignes = []
        for num_ligne, item in enumerate(donnees_tableau):
            self.lignes.append(Ligne(classe_importer=self, type_import=type_import, num_ligne=num_ligne,
                                     donnees={code: Donnee(classe_importer=self, code=code, valeur=item[int(num_colonne)], num_ligne=num_ligne, num_colonne=num_colonne) for num_colonne, code in colonnes_affectees.items()}))

    def Verifier(self):
        """ Vérifier la cohérence de toutes les lignes. Renvoie une liste d'anomalies """
        # Vérifie chaque ligne
        self.anomalies = []
        self.avertissements = []

        # Vérification de chaque ligne
        for ligne in self.lignes:
            ligne.Verifier()

        return self.anomalies, self.avertissements

    def Creer_collaborateur(self, ligne=None, suffixe=""):
        """ Créé un individu """
        if suffixe: suffixe = "_%s" % suffixe

        # Si aucune civilité ni nom renseignés, on passe
        if not getattr(ligne, "CIVILITE" + suffixe, None) or not getattr(ligne, "NOM" + suffixe, None):
            return None

        # Individu
        liste_champs = [
            ("civilite", "CIVILITE"), ("nom", "NOM"), ("prenom", "PRENOM"), ("memo", "MEMO"),
            # ("nom_jfille", "NOM_JFILLE"), ("date_naiss", "DATE_NAISS"), ("cp_naiss", "CP_NAISS"), ("ville_naiss", "VILLE_NAISS"),
            ("rue_resid", "RUE_RESID"), ("cp_resid", "CP_RESID"), ("ville_resid", "VILLE_RESID"),
            ("tel_domicile", "TELEPHONE_DOMICILE"), ("tel_mobile", "TELEPHONE_PORTABLE"), ("mail", "EMAIL_PERSONNEL"),
            ("travail_tel", "TELEPHONE_PRO"), ("travail_mail", "EMAIL_PRO"),
        ]
        valeurs = {champ: getattr(ligne, code + suffixe) for champ, code in liste_champs if getattr(ligne, code + suffixe, None)}
        collaborateur = Collaborateur.objects.create(**valeurs)
        if self.groupes:
            collaborateur.groupes.set(GroupeCollaborateurs.objects.filter(pk__in=self.groupes))

        return collaborateur

    def Enregistrer_collaborateurs(self):
        """ Enregistrement pour le mode COLLABORATEURS """
        nbre_collaborateurs = 0
        for ligne in self.lignes:
            collaborateur = self.Creer_collaborateur(ligne=ligne)
            nbre_collaborateurs += 1

        # Rapport de succès
        return "%d collaborateurs ont été créés avec succès" % nbre_collaborateurs

    def Enregistrer(self):
        """ Enregistrement des données dans la base """
        if self.type_import == "COLLABORATEURS":
            rapport_succes = self.Enregistrer_collaborateurs()

        # Rapport de succès
        return rapport_succes
