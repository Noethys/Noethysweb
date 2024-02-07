# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.models import Activite, Famille, Individu, Mail, Destinataire
from core.utils import utils_dates
from outils.utils import utils_email
from consommations.views.liste_attente import Get_resultats
from consommations.utils.utils_grille_virtuelle import Grille_virtuelle


def Traiter_attentes(request=None, selections=None, test=False):
    logger.debug("Recherche de places en attente à réattribuer...")

    if selections:
        condition_activites = Q(pk__in=list({dict_temp["idactivite"]: True for dict_temp in selections}.keys()))
    else:
        condition_activites = Q(reattribution_auto=True)

    for activite in Activite.objects.filter(condition_activites):
        if selections:
            liste_resultats = [dict_temp for dict_temp in selections if dict_temp["idactivite"] == activite.pk]
        else:
            # Recherche les places disponibles
            date_min = datetime.date.today() + datetime.timedelta(activite.reattribution_delai)
            date_max = date_min + datetime.timedelta(365)
            liste_resultats = Get_resultats(parametres={
                "donnees": "traitement_attente",
                "date_min": date_min,
                "date_max": date_max,
                "activites": [activite,],
            })

        # Regroupement des résultats par famille, individu, date
        dict_resultats_familles = {}
        for resultat in liste_resultats:
            if resultat.get("place_dispo", False) == True or selections:
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
            continue

        # Recherche de l'adresse d'expédition du mail
        if not activite.reattribution_adresse_exp:
            logger.error("Aucune adresse d'expédition paramétrée pour l'envoi des places disponibles.")
            continue
        if not activite.reattribution_adresse_exp.actif:
            logger.error("L'adresse d'expédition paramétrée n'est pas activée.")
            continue

        # Création du mail
        logger.debug("Création du mail des places en attente à réattribuer...")
        if not activite.reattribution_modele_email:
            logger.error("Erreur : Aucun modèle d'email de catégorie 'portail_places_disponibles' n'a été paramétré !")
            continue

        mail = Mail.objects.create(
            categorie="portail_places_disponibles",
            objet=activite.reattribution_modele_email.objet if activite.reattribution_modele_email else "",
            html=activite.reattribution_modele_email.html if activite.reattribution_modele_email else "",
            adresse_exp=activite.reattribution_adresse_exp,
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
                    texte_detail += "<b>%s</b> :<br>" % utils_dates.DateComplete(date)
                    for dict_temp in dict_dates[date]:
                        texte_detail += " - %s (%s)<br>" % (dict_temp["nom_unites"], dict_temp["nom_activite"])
                logger.debug("Détail = %s" % texte_detail)

                valeurs_fusion = {"{DETAIL_PLACES}": texte_detail, "{INDIVIDU_NOM}": individu.nom, "{INDIVIDU_PRENOM}": individu.prenom, "{INDIVIDU_NOM_COMPLET}": individu.Get_nom()}
                destinataire = Destinataire.objects.create(categorie="famille", famille=famille, adresse=famille.mail, valeurs=json.dumps(valeurs_fusion))
                mail.destinataires.add(destinataire)

        # Envoi du mail
        logger.debug("Envoi du mail de réattribution des places en attente.")
        if not test:
            utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)

        # Transformation des consommations Attente en Réservation
        logger.debug("Transformation des consommations attente en réservation...")
        for idfamille, dict_individus in dict_resultats_familles.items():
            for idindividu, dict_dates in dict_individus.items():
                for date, liste_temp in dict_dates.items():
                    for dict_temp in liste_temp:
                        grille = Grille_virtuelle(request=request, idfamille=idfamille, idindividu=idindividu, idactivite=dict_temp["idactivite"], date_min=date, date_max=date)
                        logger.debug("Transformation des consommations : %s..." % str(dict_temp["consommations"]))
                        for idconso in dict_temp["consommations"]:
                            grille.Modifier(criteres={"idconso": idconso, "etat": "attente"}, modifications={"etat": "reservation"})
                        if not test:
                            grille.Enregistrer()

    logger.debug("Fin de la procédure de réattribution des places en attente.")
