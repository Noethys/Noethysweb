# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, zipfile, os, shutil
logger = logging.getLogger(__name__)
from core.models import Individu, Rattachement, Mandat
from core.utils import utils_dates, utils_fichiers, utils_import_excel


def Importer(nom_fichier=""):
    importation = Import()
    importation.Start(nom_fichier_zip=nom_fichier)


class Import(utils_import_excel.Importer):
    def Start(self, nom_fichier_zip=""):
        # Dézippage des csv dans le répertoire temp
        rep_zip = os.path.join(utils_fichiers.GetTempRep(), "import_enfance_bl")
        with zipfile.ZipFile(nom_fichier_zip, "r") as zip:
            zip.extractall(path=rep_zip)

        # Analyse du csv des familles
        data_familles = self.Get_data_csv(nom_fichier=os.path.join(rep_zip, "famille.csv"))
        data_enfants = self.Get_data_csv(nom_fichier=os.path.join(rep_zip, "enfant.csv"))
        data_enfants_familles = self.Get_data_csv(nom_fichier=os.path.join(rep_zip, "enfantFamille.csv"))
        data_mandats = self.Get_data_csv(nom_fichier=os.path.join(rep_zip, "mandat.csv"))

        # Création d'un dict des enfants selon l'id enfant
        dict_enfants = {enfant.Id: enfant for enfant in data_enfants}

        # Recherche les rattachements enfants/familles
        dict_enfants_familles = {}
        for lien in data_enfants_familles:
            dict_enfants_familles.setdefault(lien.famille_id, [])
            dict_enfants_familles[lien.famille_id].append(dict_enfants[lien.enfant_id])

        # Création d'un dict des mandats selon l'id famille
        dict_mandats = {}
        for mandat in data_mandats:
            dict_mandats.setdefault(mandat.titulaire_id, [])
            dict_mandats[mandat.titulaire_id].append(mandat)

        # Traitement de chaque famille
        for ligne_famille in data_familles:

            # Création de la famille
            famille = self.Creer_famille()

            # Code compta famille
            famille.code_compta = ligne_famille.aliasTiers
            famille.save()

            # Création du titulaire du dossier
            responsable1 = Individu.objects.create(
                civilite=1 if ligne_famille.sexeResp1 == "MASCULIN" else 3,
                nom=ligne_famille.nomResp1.strip().upper(),
                prenom=ligne_famille.prenomResp1.strip().title(),
                date_naiss=utils_dates.ConvertDateFRtoDate(ligne_famille.dateNaisResp1),
                rue_resid=ligne_famille.adrNumeroVoie.strip().title() if ligne_famille.adrNumeroVoie.strip() else None,
                cp_resid=str(ligne_famille.adrcodePostal) if ligne_famille.adrcodePostal else None,
                ville_resid=ligne_famille.adrLocalite.strip().upper() if ligne_famille.adrLocalite else None,
                tel_domicile=self.Formate_telephone(ligne_famille.telephoneResp1.strip()),
                tel_mobile=self.Formate_telephone(ligne_famille.portableResp1.strip()),
                travail_tel=self.Formate_telephone(ligne_famille.telephoneProResp1.strip()),
                mail=ligne_famille.emailResp1.strip() if ligne_famille.emailResp1 else None,
            )
            Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=responsable1)
            logger.debug("Création responsable 1 : %s" % responsable1)

            # Création du responsable 2
            if ligne_famille.nomResp2:
                responsable2 = Individu.objects.create(
                    civilite=1 if ligne_famille.sexeResp2 == "MASCULIN" else 3,
                    nom=ligne_famille.nomResp2.strip().upper(),
                    prenom=ligne_famille.prenomResp2.strip().title(),
                    date_naiss=utils_dates.ConvertDateFRtoDate(ligne_famille.dateNaisResp2),
                    tel_domicile=self.Formate_telephone(ligne_famille.telephoneResp2.strip()),
                    tel_mobile=self.Formate_telephone(ligne_famille.portableResp2.strip()),
                    travail_tel=self.Formate_telephone(ligne_famille.telephoneProResp2.strip()),
                    mail=ligne_famille.emailResp2.strip() if ligne_famille.emailResp2 else None,
                    adresse_auto=responsable1.pk if responsable1.rue_resid else None,
                )
                Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=responsable2)
                logger.debug("Création responsable 2 : %s" % responsable2)

            # Enregistrement des enfants de la famille
            for ligne_individu in dict_enfants_familles.get(ligne_famille.id, []):
                enfant = Individu.objects.create(
                    civilite=4 if ligne_individu.sexe == "MASCULIN" else 5,
                    nom=ligne_individu.nom.strip(),
                    prenom=ligne_individu.prenom.title().strip(),
                    date_naiss=utils_dates.ConvertDateFRtoDate(ligne_individu.dateNaissance),
                    adresse_auto=responsable1.pk,
                )
                Rattachement.objects.create(categorie=2, titulaire=False, famille=famille, individu=enfant)
                logger.debug("Création enfant : %s" % enfant)

            # Enregistrement des mandats
            for ligne_mandat in dict_mandats.get(ligne_famille.id, []):
                mandat = Mandat.objects.create(
                    famille=famille,
                    rum=ligne_mandat.rum.strip(),
                    date=utils_dates.ConvertDateFRtoDate(ligne_mandat.dateSignature),
                    iban=ligne_mandat.iban.strip(),
                    bic=ligne_mandat.bic.strip(),
                    individu=responsable1,
                    actif=ligne_famille.typeModeReglementResp1 == "PRELEVEMENT",
                )
                logger.debug("Création mandat : %s" % mandat)

        # Maj des infos familles
        self.Maj_infos()

        # Nettoyage du répertoire temporaire
        shutil.rmtree(rep_zip)
