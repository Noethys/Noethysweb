# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Activite, Famille, Individu, Mail, ModeleEmail, Destinataire, AdresseMail, Consommation, Prestation, Vacance
from core.utils import utils_dates
from outils.utils import utils_email
from consommations.views.liste_attente import Get_resultats
from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
import datetime, json


def Traiter_attentes(request=None):
    logger.debug("Recherche de places en attente à réattribuer...")
    date_min = datetime.date.today()
    date_max = date_min + datetime.timedelta(365)

    # Recherche les places dispnoibles
    liste_resultats = Get_resultats(parametres={
        "donnees": "traitement_attente",
        "date_min": date_min,
        "date_max": date_max,
        "activites": Activite.objects.all(),
    })

    # Regroupement des résultats par famille, individu, date
    dict_resultats_familles = {}
    for resultat in liste_resultats:
        if resultat.get("place_dispo", False) == True:
            idfamille = resultat["idfamille"]
            idindividu = resultat["idindividu"]
            date = utils_dates.ConvertDateENGtoDate(resultat["date"])
            dict_resultats_familles.setdefault(idfamille, {})
            dict_resultats_familles[idfamille].setdefault(idindividu, {})
            dict_resultats_familles[idfamille][idindividu].setdefault(date, [])
            dict_resultats_familles[idfamille][idindividu][date].append({
                "nom_unites": resultat["unites"],
                "unites": resultat["liste_IDunite"],
                "consommations": resultat["liste_IDconso"],
                "nom_activite": resultat["nom_activite"],
                "idactivite": resultat["idactivite"],
            })

    logger.debug("Nombre de familles concernées par la réattribution de places en attente : %d." % len(dict_resultats_familles))

    # Si aucune famille concernée, on abandonne la procédure
    if not len(dict_resultats_familles):
        return

    # Création du mail
    logger.debug("Création du mail des places en attente à réattribuer...")
    modele_email = ModeleEmail.objects.filter(categorie="portail_places_disponibles", defaut=True).first()
    mail = Mail.objects.create(
        categorie="portail_places_disponibles",
        objet=modele_email.objet if modele_email else "",
        html=modele_email.html if modele_email else "",
        adresse_exp=AdresseMail.objects.filter(defaut=True).first(),
        selection="NON_ENVOYE",
        utilisateur=request.user if request else None,
    )

    # Préparation de chaque mail à envoyer
    for idfamille, dict_individus in dict_resultats_familles.items():
        famille = Famille.objects.get(pk=idfamille)
        for idindividu, dict_dates in dict_individus.items():
            individu = Individu.objects.get(pk=idindividu)
            logger.debug("Préparation du mail pour %s..." % individu)

            # Préparation du texte de l'email
            liste_dates = list(dict_dates.keys())
            liste_dates.sort()
            texte_detail = ""
            for date in liste_dates:
                texte_detail = "<b>%s</b><br>" % utils_dates.DateComplete(date)
                for dict_temp in dict_dates[date]:
                    texte_detail += " - %s (%s)<br>" % (dict_temp["nom_unites"], dict_temp["nom_activite"])

            valeurs_fusion = {"{DETAIL_PLACES}": texte_detail, "{INDIVIDU_NOM}": individu.nom, "{INDIVIDU_PRENOM}": individu.prenom, "{INDIVIDU_NOM_COMPLET}": individu.Get_nom()}
            destinataire = Destinataire.objects.create(categorie="famille", famille=famille, adresse=famille.mail, valeurs=json.dumps(valeurs_fusion))
            mail.destinataires.add(destinataire)

    # Envoi du mail
    logger.debug("Envoi du mail de réattribution des places en attente.")
    utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)

    # Transormation des consommations attente en Réservation
    logger.debug("Tranformation des consommation attente en réservation...")
    for idfamille, dict_individus in dict_resultats_familles.items():
        for idindividu, dict_dates in dict_individus.items():
            for date, liste_temp in dict_dates.items():
                for dict_temp in liste_temp:
                    grille = Grille_virtuelle(request=request, idfamille=idfamille, idindividu=idindividu, idactivite=dict_temp["idactivite"], date_min=date, date_max=date)
                    for idconso in dict_temp["consommations"]:
                        grille.Modifier(criteres={"idconso": idconso, "etat": "attente"}, modifications={"etat": "reservation"})
                    grille.Enregistrer()

    logger.debug("Fin de la procédure de réattribution des places en attente.")
