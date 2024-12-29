# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.models import Secteur, Famille, Utilisateur, Individu, Rattachement
from core.utils import utils_db
from individus.forms.importer_individus import DICT_TYPE_DONNEE
from fiche_famille.utils import utils_internet


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
        if "IDFAMILLE" in self.code and not self.valeur:
            return Anomalie(donnee=self, texte_erreur="La référence ID Famille n'est pas valide.")
        if "CIVILITE" in self.code and self.valeur.strip().lower() not in ("m", "monsieur", "mr", "m.", "h", "homme", "père", "mère", "melle", "mademoiselle",
               "mme", "madame", "femme", "garçon", "garcon", "g", "fille", "f", "collectivité", "association", "organisme", "entreprise"):
            return Anomalie(donnee=self, texte_erreur="Cette valeur ne fait pas partie des choix disponibles.")
        if "DATE" in self.code and self.valeur:
            try:
                test = datetime.datetime.strptime(self.valeur,"%d/%m/%Y")
            except:
                return Anomalie(donnee=self, texte_erreur="Cette date ne semble pas cohérente.")
        if "SECTEUR" in self.code and self.valeur:
            if self.valeur.lower() not in self.classe_importer.dict_secteurs:
                return Anomalie(donnee=self, texte_erreur="Ce secteur ne fait pas partie des choix disponibles. Il est nécessaire de la paramétrer au préalable dans Menu Paramétrage > Secteurs.")
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
            if self.valeur.lower() in ("m", "monsieur", "mr", "m.", "h", "homme", "père"): return 1
            if self.valeur.lower() in ("melle", "mademoiselle", "mère"): return 2
            if self.valeur.lower() in ("mme", "madame", "femme", "mère"): return 3
            if self.valeur.lower() in ("garçon", "garcon", "g"): return 4
            if self.valeur.lower() in ("fille", "f"): return 5
            if self.valeur.lower() in ("collectivité"): return 6
            if self.valeur.lower() in ("association"): return 7
            if self.valeur.lower() in ("organisme"): return 8
            if self.valeur.lower() in ("entreprise"): return 9
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
        if "SECTEUR" in self.code:
            return self.classe_importer.dict_secteurs.get(self.valeur, None)
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
        self.type_import = kwargs.get("type_import", "INDIVIDUS")
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
        if self.type_import == "INDIVIDUS":
            # Vérifie qu'il y a au moins une civilité et un nom dans la ligne
            if "CIVILITE" not in self.donnees:
                self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Une ligne doit comporter obligatoirement une civilité."))
            if "NOM" not in self.donnees:
                self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Une ligne doit comporter obligatoirement un nom de famille."))

        if self.type_import == "FAMILLES":
            # Regroupement des champs par numéro d'individu
            dict_individus = {}
            for code in self.donnees.keys():
                champ, num_individu = code.split("_INDIVIDU")
                dict_individus.setdefault(num_individu, [])
                if champ in dict_individus[num_individu]:
                    self.classe_importer.anomalies.append(Anomalie(ligne=self,texte_erreur="La colonne %s est en double pour l'individu %s" % (self.classe_importer.dict_type_donnee[champ], num_individu)))
                dict_individus[num_individu].append(champ)

            # Vérifie que chaque individu possède au minimum une civilité et un nom de famille
            for num_individu, liste_champs in dict_individus.items():
                if "CIVILITE" not in liste_champs:
                    self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Une civilité doit être obligatoirement renseignée pour l'individu %s." % num_individu))
                if "NOM" not in liste_champs:
                    self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Un nom de famille doit être obligatoirement renseigné pour l'individu %s." % num_individu))

            # Vérifie qu'il y a au moins un représentant par ligne
            liste_civilites = []
            for code, donnee in self.donnees.items():
                if code.startswith("CIVILITE") and donnee.Verifier():
                    liste_civilites.append(donnee.Get_valeur_finale())
            if 1 not in liste_civilites and 2 not in liste_civilites and 3 not in liste_civilites:
                self.classe_importer.anomalies.append(Anomalie(ligne=self, texte_erreur="Il doit y avoir au moins un représentant dans la famille."))


class Importer:
    def __init__(self, type_import="INDIVIDUS", donnees_tableau=[], colonnes_affectees={}):
        self.type_import = type_import
        self.colonnes_affectees = colonnes_affectees
        self.anomalies = []
        self.avertissements = []

        # Importation des données générales
        self.dict_type_donnee = {item["code"]: item for item in DICT_TYPE_DONNEE[type_import]}
        self.dict_secteurs = {secteur.nom.lower(): secteur for secteur in Secteur.objects.all()}

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

        # Pour le mode "Un individu par ligne", si un IDFAMILLE a été indiqué, vérifie qu'il y a un représentant par famille
        if self.type_import == "INDIVIDUS" and "IDFAMILLE" in self.colonnes_affectees.values():
            dict_familles = {}
            for ligne in self.lignes:
                IDfamille = getattr(ligne, "IDFAMILLE", None)
                dict_familles.setdefault(IDfamille, {"lignes": [], "civilites": []})
                dict_familles[IDfamille]["lignes"].append(ligne)
                for code, donnee in ligne.donnees.items():
                    if code.startswith("CIVILITE") and donnee.Verifier():
                        dict_familles[IDfamille]["civilites"].append(donnee.Get_valeur_finale())
            for IDfamille, dict_famille in dict_familles.items():
                if 1 not in dict_famille["civilites"] and 2 not in dict_famille["civilites"] and 3 not in dict_famille["civilites"]:
                    for ligne in dict_famille["lignes"]:
                        self.anomalies.append(Anomalie(ligne=ligne, texte_erreur="Il doit y avoir au moins un représentant dans la famille (IDfamille=%s)." % IDfamille))

        # Avertissement : Si mode 'Une ligne par individu' mais pas de colonne IDFAMILLE indiquée
        if self.type_import == "INDIVIDUS" and "IDFAMILLE" not in self.colonnes_affectees.values():
            self.avertissements.append("""Vous avez sélectionné le mode 'Une ligne par individu' sans définir de colonne 'ID Famille'. Il sera donc impossible de 
                                        créer des fiches familles : Des fiches individuelles non rattachées seront créées, mais ce sera à vous de les rattacher 
                                        manuellement à des fiches familles.""")

        return self.anomalies, self.avertissements

    def Creer_famille(self):
        """ Créer une fiche famille """
        famille = Famille.objects.create()
        logger.debug("Création de la famille ID%d" % famille.pk)
        internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=famille.pk)
        internet_mdp, date_expiration_mdp = utils_internet.CreationMDP()
        famille.internet_identifiant = internet_identifiant
        famille.internet_mdp = internet_mdp
        utilisateur = Utilisateur(username=internet_identifiant, categorie="famille", force_reset_password=True, date_expiration_mdp=date_expiration_mdp)
        utilisateur.save()
        utilisateur.set_password(internet_mdp)
        utilisateur.save()
        famille.utilisateur = utilisateur
        famille.save()
        return famille

    def Creer_individu(self, ligne=None, famille=None, suffixe=""):
        """ Créé un individu """
        if suffixe: suffixe = "_%s" % suffixe

        # Si aucune civilité ni nom renseignés, on passe
        if not getattr(ligne, "CIVILITE" + suffixe, None) or not getattr(ligne, "NOM" + suffixe, None):
            return None

        # Individu
        liste_champs = [
            ("civilite", "CIVILITE"), ("nom", "NOM"), ("nom_jfille", "NOM_JFILLE"), ("prenom", "PRENOM"), ("date_naiss", "DATE_NAISS"), ("cp_naiss", "CP_NAISS"),
            ("ville_naiss", "VILLE_NAISS"), ("rue_resid", "RUE_RESID"), ("cp_resid", "CP_RESID"), ("ville_resid", "VILLE_RESID"), ("secteur", "SECTEUR_RESID"),
            ("tel_domicile", "TELEPHONE_DOMICILE"), ("tel_mobile", "TELEPHONE_PORTABLE"), ("travail_tel", "TELEPHONE_PRO"), ("mail", "EMAIL_PERSONNEL"),
            ("travail_mail", "EMAIL_PRO"), ("memo", "MEMO"),
        ]
        valeurs = {champ: getattr(ligne, code + suffixe) for champ, code in liste_champs if getattr(ligne, code + suffixe, None)}
        individu = Individu.objects.create(**valeurs)

        # Rattachement
        if famille:
            valeurs = {"categorie": 1, "titulaire": True} if getattr(ligne, "CIVILITE" + suffixe) in (1, 2, 3, 6, 7, 8, 9) else {"categorie": 2, "titulaire": False}
            Rattachement.objects.create(**valeurs, famille=famille, individu=individu)

        return individu

    def Enregistrer_individus(self):
        """ Enregistrement pour le mode INDIVIDUS """
        dict_familles = {}
        nbre_individus = 0
        for ligne in self.lignes:

            # Création de la famille si besoin
            famille = None
            IDfamille = getattr(ligne, "IDFAMILLE", None)
            if IDfamille:
                # Récupère une famille créée précédemment
                if IDfamille in dict_familles:
                    famille = dict_familles[IDfamille]
                else:
                    # Création d'une nouvelle famille
                    famille = self.Creer_famille()
                    dict_familles[IDfamille] = famille

            # Création de l'individu
            individu = self.Creer_individu(ligne=ligne, famille=famille)
            nbre_individus += 1

        # Rapport de succès
        return "%d individus et %d familles ont été créées avec succès" % (nbre_individus, len(dict_familles))

    def Enregistrer_familles(self):
        """ Enregistrement pour le mode FAMILLES """
        nbre_individus = 0
        for ligne in self.lignes:
            # Création de la famille
            famille = self.Creer_famille()

            # Création de chaque individu
            for index in range(1, 7):
                individu = self.Creer_individu(ligne=ligne, famille=famille, suffixe="INDIVIDU%d" % index)
                if individu:
                    nbre_individus += 1

        # Rapport de succès
        return "%d individus et %d familles ont été créées avec succès" % (nbre_individus, len(self.lignes))

    def Enregistrer(self):
        """ Enregistrement des données dans la base """
        if self.type_import == "INDIVIDUS":
            rapport_succes = self.Enregistrer_individus()
        if self.type_import == "FAMILLES":
            rapport_succes = self.Enregistrer_familles()

        # Mise à jour de toutes les infos familles et individus
        utils_db.Maj_infos()

        # Rapport de succès
        return rapport_succes
