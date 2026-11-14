# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Espace collaborateur du portail : comptes d'accès, emails de notification et récapitulatif des changements de planning """

import logging, datetime, random, re, json, html
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Q
from core.models import Collaborateur, Utilisateur, AdresseMail, Mail, Destinataire, Historique
from core.utils import utils_portail

CATEGORIE = "collaborateur"
TITRES_PLANNING = ("Ajout d'un évènement", "Modification d'un évènement", "Suppression d'un évènement")


def Get_parametres():
    return utils_portail.Get_dict_parametres()


def Espace_actif(parametres=None):
    return bool((parametres or Get_parametres()).get("collaborateurs_espace_actif", False))


# ------------------------------------------------- Comptes d'accès -------------------------------------------------

def Creation_identifiant(collaborateur=None):
    """ Identifiant aléatoire préfixé par C (les familles utilisent F) et unique parmi tous les comptes """
    for _ in range(50):
        identifiant = "C%d" % (int("".join(random.choice("123456789") for x in range(4)) + "0" * 5) + collaborateur.pk)
        if not Utilisateur.objects.filter(username__iexact=identifiant).exists():
            return identifiant
    raise Exception("Impossible de générer un identifiant unique")


def Creer_compte(collaborateur=None):
    """ Crée ou recrée les codes d'accès d'un collaborateur (mot de passe provisoire à personnaliser lors de la première connexion) """
    from fiche_famille.utils.utils_internet import CreationMDP
    mdp, date_expiration = CreationMDP()
    utilisateur = collaborateur.utilisateur
    if not utilisateur:
        identifiant = collaborateur.internet_identifiant or Creation_identifiant(collaborateur)
        utilisateur = Utilisateur(username=identifiant, categorie=CATEGORIE)
        collaborateur.internet_identifiant = identifiant
    utilisateur.first_name, utilisateur.last_name = collaborateur.prenom or "", collaborateur.nom
    utilisateur.force_reset_password = True
    utilisateur.date_expiration_mdp = date_expiration
    utilisateur.is_active = collaborateur.internet_actif
    utilisateur.set_password(mdp)
    utilisateur.save()
    collaborateur.utilisateur = utilisateur
    collaborateur.internet_mdp = mdp
    collaborateur.save()
    return utilisateur


def Purge_mdp_expires():
    """ Efface les mots de passe provisoires expirés des collaborateurs (équivalent de la purge des familles) """
    for utilisateur in Utilisateur.objects.filter(categorie=CATEGORIE, date_expiration_mdp__lte=datetime.datetime.now() - datetime.timedelta(days=3)):
        collaborateur = Collaborateur.objects.filter(utilisateur=utilisateur).first()
        if collaborateur:
            utilisateur.set_password(None)
            utilisateur.save()
            collaborateur.internet_mdp = None
            collaborateur.save()


# ------------------------------------------------- Emails -------------------------------------------------

def Adresse_collaborateur(collaborateur=None):
    return collaborateur.travail_mail or collaborateur.mail or None


def Adresses_responsables(collaborateur=None, parametres=None):
    """ Superviseurs des groupes du collaborateur, à défaut les adresses des responsables saisies dans les paramètres du portail """
    adresses = sorted({utilisateur.email for utilisateur in Utilisateur.objects.filter(superviseurs_groupe_collaborateurs__collaborateur_groupes=collaborateur, is_active=True).distinct() if utilisateur.email})
    if not adresses:
        texte = (parametres or Get_parametres()).get("collaborateurs_email_responsables", "") or ""
        adresses = [adresse.strip() for adresse in re.split("[;,]", texte) if "@" in adresse]
    return adresses


def Envoyer_email(destinataires=[], objet="", html_corps="", request=None, parametres=None):
    """ Envoie un email (destinataires : liste de tuples (adresse, collaborateur ou None)). Ne lève jamais d'exception : un échec est journalisé """
    parametres = parametres or Get_parametres()
    destinataires = [(adresse, collaborateur) for adresse, collaborateur in destinataires if adresse]
    if not destinataires or settings.MODE_DEMO:
        return False
    try:
        adresse_exp = AdresseMail.objects.filter(pk=parametres.get("collaborateurs_adresse_exp") or 0, actif=True).first()
        if not adresse_exp:
            logger.debug("Espace collaborateur : aucune adresse d'expédition paramétrée, email non envoyé (%s)." % objet)
            return False
        mail = Mail.objects.create(categorie="saisie_libre", objet=objet, html=html_corps, adresse_exp=adresse_exp, selection="NON_ENVOYE")
        for adresse, collaborateur in destinataires:
            destinataire = Destinataire.objects.create(categorie="collaborateur" if collaborateur else "saisie_libre", collaborateur=collaborateur, adresse=adresse, valeurs=json.dumps({}))
            mail.destinataires.add(destinataire)
        from outils.utils import utils_email
        utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)
        return True
    except Exception as erreur:
        logger.error("Espace collaborateur : erreur lors de l'envoi de l'email '%s' : %s" % (objet, erreur))
        return False


def Html(texte_paragraphes=[]):
    return "".join("<p>%s</p>" % paragraphe for paragraphe in texte_paragraphes if paragraphe)


def Notifier_nouvelle_demande(demande=None, request=None):
    from collaborateurs.utils.utils_conges import Texte_periode_demande, Format_valeur
    collaborateur = demande.collaborateur
    adresses = Adresses_responsables(collaborateur)
    texte = Html(["Bonjour,", "%s a fait une demande d'absence depuis son espace collaborateur :" % html.escape(collaborateur.Get_nom()),
                  "<b>%s</b> %s (%s)%s" % (html.escape(demande.type_conge.nom), html.escape(Texte_periode_demande(demande)), Format_valeur(demande.quantite, demande.type_conge.unite),
                                          "<br>Motif : %s" % html.escape(demande.motif) if demande.motif else ""),
                  "Vous pouvez la traiter dans Noethysweb, menu Collaborateurs > Demandes d'absence."])
    return Envoyer_email([(adresse, None) for adresse in adresses], "Demande d'absence de %s" % collaborateur.Get_nom(), texte, request=request)


def Notifier_decision(demande=None, request=None):
    """ Informe le collaborateur de la décision prise sur sa demande (s'il dispose d'un accès à l'espace collaborateur) """
    from collaborateurs.utils.utils_conges import Texte_periode_demande
    collaborateur = demande.collaborateur
    if not collaborateur.utilisateur_id or not collaborateur.internet_actif or not Espace_actif():
        return False
    decisions = {"VALIDEE": "a été validée", "REFUSEE": "a été refusée", "ANNULEE": "a été annulée"}
    texte = Html(["Bonjour %s," % html.escape(collaborateur.prenom or collaborateur.nom),
                  "Votre demande de %s %s %s." % (html.escape(demande.type_conge.nom.lower()), html.escape(Texte_periode_demande(demande)), decisions.get(demande.etat, "a été traitée")),
                  "Commentaire : %s" % html.escape(demande.commentaire) if demande.commentaire else "",
                  "Vous pouvez consulter vos congés dans votre espace collaborateur."])
    return Envoyer_email([(Adresse_collaborateur(collaborateur), collaborateur)], "Votre demande d'absence %s" % decisions.get(demande.etat, "a été traitée"), texte, request=request)


def Notifier_piece(piece=None, request=None):
    """ Informe le collaborateur de l'acceptation ou du refus d'un document qu'il a transmis """
    collaborateur = piece.collaborateur
    if not collaborateur.utilisateur_id or not collaborateur.internet_actif or not Espace_actif():
        return False
    decision = "a été accepté" if piece.statut == "VALIDE" else "a été refusé"
    texte = Html(["Bonjour %s," % html.escape(collaborateur.prenom or collaborateur.nom), "Le document « %s » que vous avez transmis %s." % (html.escape(piece.Get_nom()), decision),
                  "Vous pouvez consulter vos documents dans votre espace collaborateur."])
    return Envoyer_email([(Adresse_collaborateur(collaborateur), collaborateur)], "Votre document %s" % decision, texte, request=request)


def Notifier_a_verifier(collaborateur=None, objet="", detail="", menu="", request=None):
    """ Prévient les responsables qu'un élément transmis depuis l'espace collaborateur est à vérifier (pièce, heures déclarées) """
    texte = Html(["Bonjour,", "%s %s" % (html.escape(collaborateur.Get_nom()), detail), "Rendez-vous dans Noethysweb, %s." % menu])
    return Envoyer_email([(adresse, None) for adresse in Adresses_responsables(collaborateur)], objet, texte, request=request)


# ------------------------------------------------- Récapitulatif des changements de planning -------------------------------------------------

def Date_historique(detail=""):
    """ Date de l'évènement indiquée au début du détail de l'historique du planning (jj/mm/aaaa) """
    resultat = re.match(r"\s*(\d{2})/(\d{2})/(\d{4})", detail or "")
    if not resultat:
        return None
    try:
        return datetime.date(int(resultat.group(3)), int(resultat.group(2)), int(resultat.group(1)))
    except ValueError:
        return None


def Get_changements(collaborateur=None, depuis=None, maintenant=None, nbre_jours=14):
    """ Changements du planning enregistrés depuis une date et portant sur les nbre_jours prochains jours """
    maintenant = maintenant or datetime.datetime.now()
    debut, fin = maintenant.date(), maintenant.date() + datetime.timedelta(days=nbre_jours)
    changements = []
    for action in Historique.objects.filter(collaborateur=collaborateur, titre__in=TITRES_PLANNING, horodatage__gt=depuis, horodatage__lte=maintenant).order_by("horodatage"):
        date = Date_historique(action.detail)
        if date and debut <= date <= fin:
            changements.append({"date": date, "titre": action.titre.replace(" d'un évènement", ""), "detail": action.detail})
    return sorted(changements, key=lambda changement: changement["date"])


def Envoyer_recapitulatifs_planning(maintenant=None):
    """ Tâche planifiée quotidienne : un email par collaborateur dont le planning des 14 prochains jours a changé depuis le dernier récapitulatif """
    parametres = Get_parametres()
    if not Espace_actif(parametres) or not parametres.get("collaborateurs_notifier_planning", False):
        return 0
    maintenant = maintenant or datetime.datetime.now()
    nbre_envois = 0
    for collaborateur in Collaborateur.objects.filter(notifier_planning=True, internet_actif=True, utilisateur__isnull=False, utilisateur__is_active=True):
        depuis = collaborateur.notifier_planning_date or (maintenant - datetime.timedelta(days=1))
        changements = Get_changements(collaborateur, depuis, maintenant)
        if changements and Adresse_collaborateur(collaborateur):
            lignes = "".join("<li><b>%s</b> : %s</li>" % (changement["titre"], html.escape(changement["detail"])) for changement in changements)
            texte = Html(["Bonjour %s," % html.escape(collaborateur.prenom or collaborateur.nom), "Votre planning des prochains jours a été modifié :"]) + "<ul>%s</ul>" % lignes + \
                    Html(["Consultez votre planning à jour dans votre espace collaborateur."])
            if Envoyer_email([(Adresse_collaborateur(collaborateur), collaborateur)], "Votre planning a été modifié", texte, parametres=parametres):
                nbre_envois += 1
        collaborateur.notifier_planning_date = maintenant
        collaborateur.save(update_fields=["notifier_planning_date"])
    return nbre_envois
