# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Fonctions d'anonymisation des familles et des individus (RGPD).
Utilisées par "Effacer des fiches familles" (menu Individus) et par le Nettoyeur (menu Outils).

Principe : la fiche est conservée pour que les statistiques et la comptabilité restent justes
(inscriptions, consommations, prestations, factures et règlements sont conservés), mais toutes les
données permettant d'identifier les personnes sont supprimées.
Sont volontairement conservés pour les statistiques : civilité, mois et année de naissance,
code postal et ville de résidence, secteur géographique et catégorie socio-professionnelle.
"""

import datetime, logging
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.models import Individu, Rattachement, Note, Piece, QuestionnaireReponse, Information, Vaccin, Mandat, Payeur, \
                        Historique, Lien, Destinataire, DestinataireSMS, ContactUrgence, Assurance, PortailMessage, PortailRenseignement, \
                        Scolarite, Inscription, Quotient, Consentement, Lecture, SondageRepondant

ETAT_ANONYME = "efface"


def Effacer_attributs(objet=None, attributs=[]):
    for attribut in attributs:
        setattr(objet, attribut, None)


def Is_famille_anonyme(famille=None):
    return famille.etat == ETAT_ANONYME or famille.nom in ("Famille effacée",)


def Conditions_familles_anonymes(prefixe=""):
    """ Renvoie un Q() qui sélectionne les familles déjà anonymisées """
    return Q(**{"%setat" % prefixe: ETAT_ANONYME}) | Q(**{"%snom" % prefixe: "Famille effacée"})


def Conditions_individus_anonymes(prefixe=""):
    return Q(**{"%setat" % prefixe: ETAT_ANONYME}) | Q(**{"%snom" % prefixe: "Individu effacé"})


def Effacer_donnees_medicales(individu=None):
    """ Efface les données de santé d'un individu (article 9 du RGPD). Renvoie True si des données ont été effacées. """
    modification = False
    nbre, temp = Information.objects.filter(individu=individu).delete()
    modification = modification or bool(nbre)
    nbre, temp = Vaccin.objects.filter(individu=individu).delete()
    modification = modification or bool(nbre)
    if individu.maladies.exists():
        individu.maladies.clear()
        modification = True
    if individu.regimes_alimentaires.exists():
        individu.regimes_alimentaires.clear()
        modification = True
    if individu.medecin_id:
        Individu.objects.filter(pk=individu.pk).update(medecin=None)
        individu.medecin = None
        modification = True
    return modification


def Anonymiser_individu(individu=None, date_jour=None):
    """ Anonymise un individu """
    if not date_jour:
        date_jour = datetime.date.today()

    # Conservation du mois et de l'année de naissance uniquement (statistiques par âge)
    date_naiss = individu.date_naiss
    individu.date_naiss = datetime.date(date_naiss.year, date_naiss.month, 1) if date_naiss else None

    individu.nom = "Individu anonyme"
    individu.prenom = "n°%d" % individu.pk
    individu.etat = ETAT_ANONYME
    Effacer_attributs(individu, [
        "nom_jfille", "cp_naiss", "ville_naiss", "ville_naiss_insee", "idnationalite", "annee_deces", "adresse_auto",
        "rue_resid", "profession", "employeur", "travail_tel", "travail_fax", "travail_mail",
        "tel_domicile", "tel_mobile", "tel_fax", "mail", "medecin", "memo", "type_sieste", "situation_familiale",
        "type_garde", "info_garde",
    ])
    individu.travail_tel_sms = False
    individu.tel_domicile_sms = False
    individu.tel_mobile_sms = False
    # La photo est supprimée du disque par django-cleanup une fois la transaction validée
    individu.photo = None
    individu.save()
    individu.listes_diffusion.clear()

    # Données de santé
    Effacer_donnees_medicales(individu=individu)

    # Clôture des inscriptions encore ouvertes
    Inscription.objects.filter(individu=individu, date_fin__isnull=True).update(date_fin=date_jour)

    # Autres tables liées à l'individu
    Note.objects.filter(individu=individu).delete()
    for piece in Piece.objects.filter(individu=individu):
        piece.delete()
    QuestionnaireReponse.objects.filter(individu=individu).delete()
    Scolarite.objects.filter(individu=individu).delete()
    ContactUrgence.objects.filter(individu=individu).delete()
    Lien.objects.filter(Q(individu_sujet=individu) | Q(individu_objet=individu)).delete()
    for assurance in Assurance.objects.filter(individu=individu):
        assurance.delete()
    PortailRenseignement.objects.filter(individu=individu).delete()
    SondageRepondant.objects.filter(individu=individu).delete()
    Destinataire.objects.filter(individu=individu).update(adresse=None)
    DestinataireSMS.objects.filter(individu=individu).update(mobile=None)
    Historique.objects.filter(individu=individu).delete()


def Anonymiser_famille(famille=None, individus_exclus=set(), date_jour=None):
    """ Anonymise une famille et ses individus rattachés.
        individus_exclus : ID des individus à ne pas anonymiser (par exemple rattachés à une autre famille encore active) """
    if not date_jour:
        date_jour = datetime.date.today()

    # Fiche famille
    famille.nom = "Famille anonyme n°%d" % famille.pk
    famille.etat = ETAT_ANONYME
    famille.internet_actif = False
    Effacer_attributs(famille, [
        "num_allocataire", "allocataire", "memo", "email_factures_adresses", "email_recus_adresses", "email_depots_adresses",
        "rue_resid", "mail", "mobile", "code_compta", "internet_mdp", "internet_secquest",
        "facturation_nom", "facturation_rue_resid", "facturation_cp_resid", "facturation_ville_resid",
        "idtiers_helios", "reftiers_helios", "titulaire_helios", "tiers_solidaire",
    ])
    famille.email_factures = False
    famille.email_recus = False
    famille.email_depots = False
    famille.save()
    famille.individus_masques.clear()

    # Compte internet
    if famille.utilisateur:
        utilisateur = famille.utilisateur
        utilisateur.is_active = False
        utilisateur.first_name = ""
        utilisateur.last_name = ""
        utilisateur.email = ""
        utilisateur.set_unusable_password()
        utilisateur.save()

    Note.objects.filter(famille=famille).delete()
    for piece in Piece.objects.filter(famille=famille).exclude(individu_id__in=individus_exclus):
        piece.delete()
    QuestionnaireReponse.objects.filter(famille=famille).delete()
    PortailMessage.objects.filter(famille=famille).delete()
    PortailRenseignement.objects.filter(famille=famille).delete()
    Consentement.objects.filter(famille=famille).delete()
    Lecture.objects.filter(famille=famille).delete()
    SondageRepondant.objects.filter(famille=famille).delete()

    # Quotients : le montant est conservé pour les tarifs et les statistiques, le justificatif est supprimé
    for quotient in Quotient.objects.filter(famille=famille):
        quotient.document = None
        quotient.revenu = None
        quotient.observations = None
        quotient.save()

    # Mandats
    for mandat in Mandat.objects.filter(famille=famille):
        Effacer_attributs(mandat, ["individu", "individu_nom", "individu_rue", "individu_cp", "individu_ville", "individu_service",
                                   "individu_numero", "individu_batiment", "individu_etage", "individu_boite", "memo"])
        mandat.iban = "XXX"
        mandat.bic = "XXX"
        mandat.save()

    # Autres tables liées à la famille
    Payeur.objects.filter(famille=famille).update(nom="Payeur anonyme")
    Historique.objects.filter(famille=famille).delete()
    if famille.utilisateur_id:
        Historique.objects.filter(utilisateur_id=famille.utilisateur_id).delete()
    Lien.objects.filter(famille=famille).delete()
    Destinataire.objects.filter(famille=famille).update(adresse=None)
    DestinataireSMS.objects.filter(famille=famille).update(mobile=None)
    ContactUrgence.objects.filter(famille=famille).exclude(individu_id__in=individus_exclus).delete()
    for assurance in Assurance.objects.filter(famille=famille).exclude(individu_id__in=individus_exclus):
        assurance.delete()

    # Individus rattachés
    nbre_individus = 0
    for rattachement in Rattachement.objects.select_related("individu").filter(famille=famille, individu__isnull=False):
        if rattachement.individu_id in individus_exclus or rattachement.individu.etat == ETAT_ANONYME:
            continue
        Anonymiser_individu(individu=rattachement.individu, date_jour=date_jour)
        nbre_individus += 1

    return nbre_individus
