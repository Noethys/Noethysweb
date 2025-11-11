# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Individu, Rattachement, Caisse, ContactUrgence
from core.utils import utils_dates, utils_import_excel


def Importer(nom_fichier_enfants="", nom_fichier_responsables=""):
    importation = Import()
    importation.Start(nom_fichier_enfants=nom_fichier_enfants, nom_fichier_responsables=nom_fichier_responsables)


class Import(utils_import_excel.Importer):
    def Start(self, nom_fichier_enfants="", nom_fichier_responsables=""):
        data_enfants = self.Get_data_xlsx(nom_fichier_enfants, num_ligne_entete=3)
        data_responsables = self.Get_data_xlsx(nom_fichier_responsables, num_ligne_entete=3)

        def Formate_telephone_international(tel=""):
            if tel:
                tel = tel.replace("'", "")
                return self.Formate_telephone(tel.replace("+33", "0"))
            return None

        # Récupération des caisses paramétrées
        dict_caisses = {caisse.nom: caisse for caisse in Caisse.objects.all()}

        # Création d'un dict des responsables
        dict_responsables = {}
        for responsable in data_responsables["Adultes"]:
            individu = Individu(
                civilite=1 if responsable["Civilité"] == "M" else 3,
                nom=responsable["Nom"].upper(),
                prenom=responsable["Prénom"].strip().title(),
                rue_resid=responsable["Adresse"].title() if responsable["Adresse"].strip() else None,
                cp_resid=str(responsable["Code postal"]) if responsable["Code postal"] else None,
                ville_resid=responsable["Commune"].strip().upper() if responsable["Commune"] else None,
                tel_domicile=Formate_telephone_international(responsable["Tel"].strip()),
                tel_mobile=Formate_telephone_international(responsable["Portable"].strip()),
                mail=responsable["Courriel"].strip() if responsable["Courriel"] else None,
            )
            individu.caisse = responsable["Organisme"].strip()
            individu.num_alloc = responsable["Num.Alloc."].strip()
            individu.enfants = responsable["Enfant(s) de l’entourage proche"].strip()
            dict_responsables["%s %s" % (responsable["Nom"], responsable["Prénom"])] = individu

        # Regroupement des enfants par responsable principal
        dict_familles = {}
        for enfant in data_enfants["Enfants"]:
            dict_familles.setdefault(enfant["Adulte chez qui réside l’enfant"], [])
            dict_familles[enfant["Adulte chez qui réside l’enfant"]].append(enfant)

        # Création des familles
        for nom_adulte, enfants in dict_familles.items():
            if nom_adulte in dict_responsables:
                responsable = dict_responsables[nom_adulte]

                # Création de la famille
                famille = self.Creer_famille()

                if responsable.num_alloc:
                    famille.num_allocataire = responsable.num_alloc
                if responsable.caisse and responsable.caisse in dict_caisses:
                    famille.caisse = dict_caisses[responsable.caisse]
                famille.save()

                # Enregistrement du responsable
                responsable.save()
                Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=responsable)
                logger.debug("Création responsable titulaire : %s" % responsable)

                # Enregistrement des enfants
                liste_noms_enfants = []
                for enfant in enfants:
                    individu = Individu.objects.create(
                        civilite=4 if enfant["Sexe"] == "M" else 5,
                        nom=enfant["Nom enfant"].strip(),
                        prenom=enfant["Prénom enfant"].title().strip(),
                        date_naiss=utils_dates.ConvertDateFRtoDate(enfant["Date de naissance"]) if enfant["Date de naissance"] else None,
                        adresse_auto=responsable.pk,
                        mail=enfant["Courriel enfant"].strip() if enfant["Courriel enfant"] else None,
                    )
                    Rattachement.objects.create(categorie=2, titulaire=False, famille=famille, individu=individu)
                    logger.debug("Création enfant : %s" % individu)
                    liste_noms_enfants.append("%s %s" % (enfant["Nom enfant"], enfant["Prénom enfant"]))

                    # Enregistrement des contacts d'urgence et de sortie
                    for ligne_contact in enfant["Adultes habilités"].split("\n"):
                        nom_complet, tel = None, None
                        if len(ligne_contact) > 8:
                            pos = ligne_contact.find("+")
                            if pos > 0:
                                tel = Formate_telephone_international(ligne_contact[pos:])
                                nom_complet = ligne_contact[:pos]
                            else:
                                pos = ligne_contact.find(" 0")
                                if pos > 0:
                                    tel = Formate_telephone_international(ligne_contact[pos:])
                                    nom_complet = ligne_contact[:pos]
                        if nom_complet:
                            parties_nom = nom_complet.strip().split(" ")
                            contact = ContactUrgence.objects.create(nom=" ".join(parties_nom[:-1]), prenom=parties_nom[-1],
                                                          tel_mobile=tel, lien="?", individu=individu, famille=famille)
                            logger.debug("  Création contact : %s %s" % (contact.Get_nom(), contact.tel_mobile))

                # Recherche du conjoint
                for nom_conjoint, conjoint in dict_responsables.items():
                    trouve = True
                    for nom_enfant in liste_noms_enfants:
                        if nom_enfant not in conjoint.enfants:
                            trouve = False
                    if trouve and conjoint != responsable:
                        if conjoint.rue_resid == responsable.rue_resid:
                            conjoint.adresse_auto = responsable.pk
                        conjoint.save()
                        Rattachement.objects.create(categorie=1, titulaire=True if conjoint.rue_resid == responsable.rue_resid else False, famille=famille, individu=conjoint)
                        logger.debug("Création conjoint : %s" % conjoint)

        # Maj des infos familles
        self.Maj_infos()
