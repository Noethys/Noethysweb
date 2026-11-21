# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, logging
logger = logging.getLogger(__name__)
from django.db import transaction
from django.utils import timezone
from outils.utils.nettoyeur.base import Operation, Element, Resultat_analyse, Resultat_execution, Url_famille, Get_taille_fichier, \
                                        Formate_nombre, Decoupe


def Debut_journee(date_limite=None):
    """ Renvoie un datetime au début de la journée (pour les champs DateTimeField) """
    valeur = datetime.datetime.combine(date_limite, datetime.time.min)
    if timezone.is_aware(timezone.now()):
        valeur = timezone.make_aware(valeur)
    return valeur


def Supprimer_par_lots(queryset=None, taille=5000):
    """ Supprime un queryset par lots pour ne pas bloquer la base trop longtemps. Renvoie le nombre de lignes supprimées. """
    total = 0
    while True:
        ids = list(queryset.values_list("pk", flat=True)[:taille])
        if not ids:
            break
        with transaction.atomic():
            queryset.model.objects.filter(pk__in=ids).delete()
        total += len(ids)
    return total


# ------------------------------------------------------------------------------------------------
# Historique
# ------------------------------------------------------------------------------------------------

class Purger_historique(Operation):
    code = "historique"
    titre = "Purger l'historique"
    description = ("Supprime les lignes de l'historique (actions des utilisateurs et des familles sur le portail) antérieures à la date limite. "
                   "L'historique contient des données personnelles et alourdit fortement la base de données.")
    categorie = "base"
    icone = "fa-history"
    delai_defaut = 12
    delai_minimum_jours = 30
    label_date = "Lignes antérieures au"
    selection_individuelle = False
    alerte_accueil = True
    label_alerte = "Historique"
    seuil_suggestion_nbre = 50000

    def Get_queryset(self, date_limite=None):
        from core.models import Historique
        return Historique.objects.filter(horodatage__lt=Debut_journee(date_limite))

    def Analyser(self, date_limite=None):
        return Resultat_analyse(nbre=self.Get_queryset(date_limite).count())

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        resultat = Resultat_execution()
        resultat.nbre = Supprimer_par_lots(self.Get_queryset(date_limite))
        return resultat


# ------------------------------------------------------------------------------------------------
# Portail
# ------------------------------------------------------------------------------------------------

class Purger_portail(Operation):
    code = "portail"
    titre = "Purger les échanges traités du portail"
    description = ("Supprime les messages du portail déjà lus, les demandes de modification de renseignements déjà validées ou refusées "
                   "et les accusés de lecture des articles, antérieurs à la date limite.")
    categorie = "base"
    icone = "fa-comments-o"
    delai_defaut = 12
    delai_minimum_jours = 30
    label_date = "Echanges antérieurs au"
    selection_individuelle = False
    seuil_suggestion_nbre = 1000

    def Get_querysets(self, date_limite=None):
        from core.models import PortailMessage, PortailRenseignement, Lecture
        debut = Debut_journee(date_limite)
        return [
            ("messages lus", PortailMessage.objects.filter(date_creation__lt=debut, date_lecture__isnull=False)),
            ("renseignements traités", PortailRenseignement.objects.filter(date__lt=debut).exclude(etat="ATTENTE")),
            ("accusés de lecture", Lecture.objects.filter(horodatage__lt=debut)),
        ]

    def Analyser(self, date_limite=None):
        total, details = 0, []
        for label, qs in self.Get_querysets(date_limite):
            nbre = qs.count()
            total += nbre
            details.append("%s %s" % (Formate_nombre(nbre), label))
        return Resultat_analyse(nbre=total, detail=", ".join(details))

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        resultat = Resultat_execution()
        for label, qs in self.Get_querysets(date_limite):
            nbre = Supprimer_par_lots(qs)
            resultat.nbre += nbre
            resultat.lignes_detail.append("%d %s" % (nbre, label))
        return resultat


# ------------------------------------------------------------------------------------------------
# Emails et SMS envoyés
# ------------------------------------------------------------------------------------------------

class Purger_emails_sms(Operation):
    code = "emails_sms"
    titre = "Purger les emails et SMS envoyés"
    description = ("Supprime les emails et SMS créés avant la date limite avec leurs destinataires (adresses, numéros), "
                   "les résultats d'envoi et les pièces jointes (factures, attestations...).")
    categorie = "base"
    icone = "fa-envelope-o"
    delai_defaut = 24
    delai_minimum_jours = 30
    label_date = "Envois antérieurs au"
    seuil_suggestion_nbre = 200

    def Get_mails(self, date_limite=None):
        from core.models import Mail
        return Mail.objects.filter(date_creation__lt=Debut_journee(date_limite))

    def Get_sms(self, date_limite=None):
        from core.models import SMS
        return SMS.objects.filter(date_creation__lt=Debut_journee(date_limite))

    def Get_taille_mail(self, mail=None):
        from core.models import DocumentJoint
        octets = sum([Get_taille_fichier(piece.fichier) for piece in mail.pieces_jointes.all()])
        octets += sum([Get_taille_fichier(document.fichier) for document in DocumentJoint.objects.filter(destinataire__mail=mail).distinct()])
        return octets

    def Analyser(self, date_limite=None):
        from django.db.models import Count
        elements = []
        for mail in self.Get_mails(date_limite).annotate(nbre_destinataires=Count("destinataires")).order_by("date_creation"):
            elements.append(Element(id="mail:%d" % mail.pk, label="Email : %s" % (mail.objet or "Sans objet"),
                                    info="Créé le %s - %d destinataire(s)" % (mail.date_creation.strftime("%d/%m/%Y"), mail.nbre_destinataires),
                                    octets=self.Get_taille_mail(mail)))
        for sms in self.Get_sms(date_limite).annotate(nbre_destinataires=Count("destinataires")).order_by("date_creation"):
            elements.append(Element(id="sms:%d" % sms.pk, label="SMS : %s" % (sms.objet or "Sans objet"),
                                    info="Créé le %s - %d destinataire(s)" % (sms.date_creation.strftime("%d/%m/%Y"), sms.nbre_destinataires)))
        return Resultat_analyse(nbre=len(elements), elements=elements, octets=sum([element.octets for element in elements]))

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Mail, Destinataire, SMS
        resultat = Resultat_execution()
        for mail in self.Get_mails(date_limite):
            if "mail:%d" % mail.pk in exclusions:
                resultat.nbre_exclus += 1
                continue
            with transaction.atomic():
                resultat.octets += self.Get_taille_mail(mail)
                for destinataire in mail.destinataires.all():
                    # Un destinataire ou un document partagé avec un autre email est conservé
                    if Mail.objects.filter(destinataires=destinataire).exclude(pk=mail.pk).exists():
                        continue
                    for document in destinataire.documents.all():
                        if not Destinataire.objects.filter(documents=document).exclude(pk=destinataire.pk).exists():
                            document.delete()
                    destinataire.delete()
                for piece in mail.pieces_jointes.all():
                    if not Mail.objects.filter(pieces_jointes=piece).exclude(pk=mail.pk).exists():
                        piece.delete()
                mail.delete()
            resultat.nbre += 1
        for sms in self.Get_sms(date_limite):
            if "sms:%d" % sms.pk in exclusions:
                resultat.nbre_exclus += 1
                continue
            with transaction.atomic():
                for destinataire in sms.destinataires.all():
                    if not SMS.objects.filter(destinataires=destinataire).exclude(pk=sms.pk).exists():
                        destinataire.delete()
                sms.delete()
            resultat.nbre += 1
        return resultat


# ------------------------------------------------------------------------------------------------
# Paiements en ligne abandonnés
# ------------------------------------------------------------------------------------------------

class Supprimer_paiements_abandonnes(Operation):
    code = "paiements_abandonnes"
    titre = "Supprimer les paiements en ligne annulés ou refusés"
    description = ("Supprime les transactions de paiement en ligne (PayFiP, Payzen, HelloAsso...) annulées par la famille ou refusées "
                   "par la banque, sans règlement associé, antérieures à la date limite. Les transactions sans réponse de la banque "
                   "ou en erreur sont conservées car elles peuvent correspondre à un paiement encaissé.")
    categorie = "base"
    icone = "fa-credit-card"
    delai_defaut = 12
    delai_minimum_jours = 30
    label_date = "Transactions antérieures au"
    seuil_suggestion_nbre = 100

    def Get_queryset(self, date_limite=None):
        from core.models import Paiement
        # Seuls les échecs certains sont supprimés. Sont conservés : les paiements sans résultat ou en attente (la notification
        # de la banque a pu être perdue alors que la famille a payé) et les paiements en erreur (ERROR peut signifier
        # un paiement encaissé mais incohérent) car ils servent au rapprochement bancaire.
        return Paiement.objects.select_related("famille").filter(horodatage__lt=Debut_journee(date_limite), reglements__isnull=True,
                                                                  resultat__in=("CANCELLED", "DENIED", "EXPIRED"))

    def Analyser(self, date_limite=None):
        elements = [Element(id=paiement.pk, label="%s - %s €" % (paiement.famille.nom, paiement.montant),
                            info="%s du %s - %s" % ((paiement.systeme_paiement or "").capitalize(), paiement.horodatage.strftime("%d/%m/%Y"), paiement.resultat or "abandonné"),
                            url=Url_famille(paiement.famille_id)) for paiement in self.Get_queryset(date_limite).order_by("horodatage")]
        return Resultat_analyse(nbre=len(elements), elements=elements)

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Paiement
        resultat = Resultat_execution()
        ids = [pk for pk in self.Get_queryset(date_limite).values_list("pk", flat=True) if str(pk) not in exclusions]
        for lot in Decoupe(ids):
            Paiement.objects.filter(pk__in=lot).delete()
        resultat.nbre = len(ids)
        resultat.nbre_exclus = len(exclusions)
        return resultat
