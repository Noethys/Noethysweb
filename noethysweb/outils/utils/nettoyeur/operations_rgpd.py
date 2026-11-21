# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, logging
logger = logging.getLogger(__name__)
from django.db import transaction
from django.db.models import Q, Count, ProtectedError
from outils.utils.nettoyeur.base import Operation, Element, Resultat_analyse, Resultat_execution, Url_famille, Url_individu, \
                                        Get_taille_fichier, Decoupe, Is_individu_supprimable
from individus.utils import utils_anonymisation


def Label_individu(individu):
    return ("%s %s" % (individu.nom or "", individu.prenom or "")).strip() or "Individu ID%d" % individu.pk


# ------------------------------------------------------------------------------------------------
# Suppression des familles jamais utilisées
# ------------------------------------------------------------------------------------------------

def Get_familles_utilisees():
    """ Renvoie les ID des familles qui ont déjà été utilisées, quelle que soit la date : inscription, consommation,
        prestation, adhésion, location, aide, facture, règlement, paiement en ligne, devis, rappel, reçu, attestation... """
    from core.models import Inscription, Consommation, Prestation, Cotisation, Location, Aide, Deduction, Facture, Reglement, Ventilation, \
                            Paiement, Devis, Rappel, Recu, Attestation, AttestationFiscale, PesPiece, Prelevements, Rattachement
    utilisees = set()
    for modele in (Inscription, Prestation, Cotisation, Location, Aide, Deduction, Facture, Reglement, Ventilation, Paiement,
                   Devis, Rappel, Recu, Attestation, AttestationFiscale, PesPiece, Prelevements):
        utilisees.update(modele.objects.filter(famille__isnull=False).values_list("famille_id", flat=True).distinct())
    utilisees.update(Consommation.objects.values_list("inscription__famille_id", flat=True).distinct())
    # Adhésions individuelles : la famille de l'individu est considérée comme utilisée
    individus = set(Cotisation.objects.filter(famille__isnull=True, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    individus.update(Consommation.objects.values_list("individu_id", flat=True).distinct())
    individus.update(Prestation.objects.filter(individu__isnull=False).values_list("individu_id", flat=True).distinct())
    if individus:
        utilisees.update(Rattachement.objects.filter(individu_id__in=individus).values_list("famille_id", flat=True).distinct())
    utilisees.discard(None)
    return utilisees


def Get_familles_recemment_actives(date_limite=None):
    """ Familles jamais utilisées mais qui montrent un signe de vie depuis la date limite (connexion au portail,
        pièce déposée, modification de la fiche...) : elles se préparent sans doute à une inscription. """
    from core.models import Famille, Piece, Historique, Note, PortailMessage, PortailRenseignement, Quotient, Rattachement, Individu, Mandat, Assurance
    actives = set()
    actives.update(Famille.objects.filter(utilisateur__last_login__date__gte=date_limite).values_list("pk", flat=True))
    actives.update(Piece.objects.filter(date_debut__gte=date_limite, famille__isnull=False).values_list("famille_id", flat=True).distinct())
    actives.update(Historique.objects.filter(horodatage__date__gte=date_limite, famille__isnull=False).values_list("famille_id", flat=True).distinct())
    actives.update(Note.objects.filter(date_saisie__date__gte=date_limite, famille__isnull=False).values_list("famille_id", flat=True).distinct())
    actives.update(PortailMessage.objects.filter(date_creation__date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(PortailRenseignement.objects.filter(date__date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Quotient.objects.filter(date_fin__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Mandat.objects.filter(date__gte=date_limite).values_list("famille_id", flat=True).distinct())
    actives.update(Assurance.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_limite)).values_list("famille_id", flat=True).distinct())
    individus = set(Individu.objects.filter(date_creation__date__gte=date_limite).values_list("pk", flat=True))
    individus.update(Piece.objects.filter(date_debut__gte=date_limite, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    individus.update(Historique.objects.filter(horodatage__date__gte=date_limite, individu__isnull=False).values_list("individu_id", flat=True).distinct())
    actives.update(Rattachement.objects.filter(individu_id__in=individus).values_list("famille_id", flat=True).distinct())
    actives.discard(None)
    return actives


class Supprimer_familles(Operation):
    code = "familles_supprimer"
    titre = "Supprimer les familles jamais utilisées"
    description = ("Supprime définitivement les fiches familles créées avant la date choisie et qui n'ont jamais été utilisées : "
                   "aucune inscription, consommation, prestation, adhésion, location, aide, facture ni règlement. "
                   "Leurs individus, pièces et fichiers sont aussi supprimés. Les fiches qui montrent une activité récente "
                   "(connexion au portail, pièce déposée, modification...) sont conservées.")
    categorie = "rgpd"
    icone = "fa-user-times"
    delai_defaut = 12
    delai_minimum_jours = 28
    label_date = "Fiches créées avant"
    nature = "Suppression"
    alerte_accueil = True
    label_alerte = "Familles jamais utilisées"

    def Get_candidats(self, date_limite=None):
        from core.models import Famille
        anciennes = set(Famille.objects.filter(date_creation__date__lt=date_limite).values_list("pk", flat=True))
        jamais_utilisees = anciennes - Get_familles_utilisees()
        candidats = jamais_utilisees - Get_familles_recemment_actives(date_limite)
        return candidats, len(jamais_utilisees) - len(candidats)

    def Analyser(self, date_limite=None):
        from core.models import Famille
        candidats, nbre_exclus = self.Get_candidats(date_limite)
        elements = []
        for lot in Decoupe(candidats):
            for famille in Famille.objects.filter(pk__in=lot).annotate(nbre_individus=Count("rattachement")):
                info = "Créée le %s - %d individu(s)" % (famille.date_creation.strftime("%d/%m/%Y"), famille.nbre_individus)
                elements.append(Element(id=famille.pk, label=famille.nom or "Famille ID%d" % famille.pk, info=info, url=Url_famille(famille.pk)))
        elements.sort(key=lambda element: element.label.lower())
        message_exclus = ""
        if nbre_exclus:
            message_exclus = "%d fiche(s) jamais utilisée(s) sont conservées car elles montrent une activité récente (connexion au portail, pièce déposée, modification de la fiche...)." % nbre_exclus
        return Resultat_analyse(nbre=len(elements), elements=elements, nbre_exclus=nbre_exclus, message_exclus=message_exclus)

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Famille
        resultat = Resultat_execution()
        candidats, resultat.nbre_exclus = self.Get_candidats(date_limite)
        for famille in Famille.objects.filter(pk__in=[pk for pk in candidats if str(pk) not in exclusions]):
            nom = famille.nom
            try:
                with transaction.atomic():
                    Supprimer_famille(famille)
                resultat.nbre += 1
            except ProtectedError:
                # Sécurité : une donnée d'activité ou comptable est apparue entre-temps, la famille est conservée
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s (ID%d) conservée : des données d'activité y sont rattachées" % (nom, famille.pk))
            except Exception as err:
                logger.exception("Nettoyeur : erreur lors de la suppression de la famille ID%d" % famille.pk)
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s (ID%d) non supprimée : %s" % (nom, famille.pk, err))
        resultat.nbre_exclus += len(exclusions)
        return resultat


def Supprimer_famille(famille=None):
    """ Supprime une famille jamais utilisée. A appeler dans une transaction.
        Aucune donnée d'activité ni comptable n'est supprimée ici : si la famille en possède, les protections de la base
        (on_delete=PROTECT) lèvent une ProtectedError et la transaction est annulée. """
    from core.models import Famille, Individu, Quotient, Assurance, Mandat, Historique, Piece, Information, Transport

    # Individus qui ne sont utilisés par aucune autre famille
    individus = [individu for individu in Individu.objects.filter(rattachement__famille=famille).distinct()
                 if Is_individu_supprimable(individu=individu, famille_exclue=famille)]

    # Données administratives sans valeur d'activité (justificatifs, mandats jamais utilisés...)
    for quotient in Quotient.objects.filter(famille=famille):
        quotient.delete()
    for assurance in Assurance.objects.filter(famille=famille):
        assurance.delete()
    Mandat.objects.filter(famille=famille).delete()
    for piece in Piece.objects.filter(famille=famille):
        piece.delete()

    # Fiche famille
    utilisateur = famille.utilisateur
    if utilisateur:
        Historique.objects.filter(utilisateur=utilisateur).delete()
    Famille.objects.filter(pk=famille.pk).update(allocataire=None, titulaire_helios=None, tiers_solidaire=None)
    famille.allocataire = None
    famille.delete()

    # Individus
    for individu in individus:
        try:
            with transaction.atomic():
                Transport.objects.filter(individu=individu).delete()
                for piece in Piece.objects.filter(individu=individu):
                    piece.delete()
                for information in Information.objects.filter(individu=individu):
                    information.delete()
                # La photo est supprimée par django-cleanup une fois la transaction validée
                individu.delete()
        except ProtectedError:
            # L'individu a des données ailleurs (inscription dans une autre famille par exemple) : il est conservé
            logger.debug("Nettoyeur : individu ID%d conservé car protégé" % individu.pk)

    # Compte internet
    if utilisateur:
        try:
            with transaction.atomic():
                utilisateur.delete()
        except ProtectedError:
            utilisateur.is_active = False
            utilisateur.save()


# ------------------------------------------------------------------------------------------------
# Anonymisation des familles inactives
# ------------------------------------------------------------------------------------------------

class Anonymiser_familles(Operation):
    code = "familles_anonymiser"
    titre = "Anonymiser les familles inactives"
    description = ("Efface les données personnelles des familles sans activité depuis la date limite et de leurs individus : noms, adresses, "
                   "téléphones, emails, IBAN, notes, pièces, photos et données de santé. La fiche est conservée pour que les statistiques "
                   "et la facturation restent justes (les ventes, factures et règlements sont conservés). "
                   "Le délai de conservation est à définir par le référent RGPD de l'organisateur.")
    categorie = "rgpd"
    icone = "fa-user-secret"
    delai_defaut = 120
    delai_minimum_jours = 180
    label_date = "Aucune activité depuis le"
    nature = "Anonymisation"
    alerte_accueil = True
    label_alerte = "Familles à anonymiser"

    def Get_candidats(self, date_limite=None):
        from core.models import Famille
        actives = self.Get_familles_actives(date_limite)
        qs = Famille.objects.filter(date_creation__date__lt=date_limite).exclude(utils_anonymisation.Conditions_familles_anonymes())
        return set(qs.values_list("pk", flat=True)) - actives

    def Analyser(self, date_limite=None):
        from core.models import Famille
        elements = []
        for lot in Decoupe(self.Get_candidats(date_limite)):
            for famille in Famille.objects.filter(pk__in=lot).annotate(nbre_individus=Count("rattachement")):
                elements.append(Element(id=famille.pk, label=famille.nom or "Famille ID%d" % famille.pk, info="%d individu(s)" % famille.nbre_individus, url=Url_famille(famille.pk)))
        elements.sort(key=lambda element: element.label.lower())
        return Resultat_analyse(nbre=len(elements), elements=elements)

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Famille, Rattachement
        resultat = Resultat_execution()
        candidats = self.Get_candidats(date_limite)
        # Les individus rattachés à une famille active ne sont pas anonymisés
        individus_exclus = set(Rattachement.objects.filter(famille_id__in=self.Get_familles_actives(date_limite)).values_list("individu_id", flat=True))
        date_jour = datetime.date.today()
        for famille in Famille.objects.filter(pk__in=[pk for pk in candidats if str(pk) not in exclusions]):
            nom = famille.nom
            try:
                with transaction.atomic():
                    utils_anonymisation.Anonymiser_famille(famille=famille, individus_exclus=individus_exclus, date_jour=date_jour)
                resultat.nbre += 1
            except Exception as err:
                logger.exception("Nettoyeur : erreur lors de l'anonymisation de la famille ID%d" % famille.pk)
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s (ID%d) non anonymisée : %s" % (nom, famille.pk, err))
        resultat.nbre_exclus = len(exclusions)
        return resultat


# ------------------------------------------------------------------------------------------------
# Données de santé des individus inactifs
# ------------------------------------------------------------------------------------------------

class Effacer_donnees_sante(Operation):
    code = "individus_sante"
    titre = "Effacer les données de santé des individus inactifs"
    description = ("Supprime les informations médicales (maladies, allergies, traitements, PAI et leurs documents), les vaccinations, "
                   "les régimes alimentaires et le médecin traitant des individus sans activité depuis la date limite. "
                   "Ce sont des données sensibles au sens de l'article 9 du RGPD.")
    categorie = "rgpd"
    icone = "fa-medkit"
    delai_defaut = 36
    delai_minimum_jours = 90
    label_date = "Individus sans activité depuis le"
    nature = "Effacement"

    def Get_candidats(self, date_limite=None):
        from core.models import Individu
        avec_donnees = set(Individu.objects.filter(
            Q(information__isnull=False) | Q(vaccin__isnull=False) | Q(maladies__isnull=False) |
            Q(regimes_alimentaires__isnull=False) | Q(medecin__isnull=False)).values_list("pk", flat=True).distinct())
        return avec_donnees - self.Get_individus_actifs(date_limite)

    def Analyser(self, date_limite=None):
        from core.models import Individu, Information, Rattachement
        candidats = self.Get_candidats(date_limite)
        tailles = {}
        familles = {}
        for lot in Decoupe(candidats):
            for information in Information.objects.filter(individu_id__in=lot).exclude(document="").exclude(document__isnull=True):
                tailles[information.individu_id] = tailles.get(information.individu_id, 0) + Get_taille_fichier(information.document)
            for rattachement in Rattachement.objects.filter(individu_id__in=lot):
                familles.setdefault(rattachement.individu_id, rattachement.famille_id)
        elements = []
        for lot in Decoupe(candidats):
            for individu in Individu.objects.filter(pk__in=lot).annotate(nbre_infos=Count("information", distinct=True), nbre_vaccins=Count("vaccin", distinct=True)):
                elements.append(Element(id=individu.pk, label=Label_individu(individu), info="%d information(s) médicale(s), %d vaccin(s)" % (individu.nbre_infos, individu.nbre_vaccins),
                                        octets=tailles.get(individu.pk, 0), url=Url_individu(familles.get(individu.pk), individu.pk)))
        elements.sort(key=lambda element: element.label.lower())
        return Resultat_analyse(nbre=len(elements), elements=elements, octets=sum(tailles.values()))

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Individu, Information
        resultat = Resultat_execution()
        for individu in Individu.objects.filter(pk__in=[pk for pk in self.Get_candidats(date_limite) if str(pk) not in exclusions]):
            try:
                with transaction.atomic():
                    resultat.octets += sum([Get_taille_fichier(information.document) for information in Information.objects.filter(individu=individu)])
                    utils_anonymisation.Effacer_donnees_medicales(individu=individu)
                resultat.nbre += 1
            except Exception as err:
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s (ID%d) : %s" % (Label_individu(individu), individu.pk, err))
        resultat.nbre_exclus = len(exclusions)
        return resultat


# ------------------------------------------------------------------------------------------------
# Comptes du portail des familles inactives
# ------------------------------------------------------------------------------------------------

class Desactiver_comptes_portail(Operation):
    code = "comptes_portail"
    titre = "Désactiver les comptes du portail des familles inactives"
    description = ("Désactive l'accès au portail des familles sans activité ni connexion depuis la date limite. "
                   "Le compte peut être réactivé à tout moment depuis la fiche famille (rubrique Portail).")
    categorie = "rgpd"
    icone = "fa-lock"
    delai_defaut = 24
    delai_minimum_jours = 90
    label_date = "Aucune activité ni connexion depuis le"
    nature = "Désactivation"
    irreversible = False

    def Get_candidats(self, date_limite=None):
        from core.models import Famille
        qs = Famille.objects.filter(Q(internet_actif=True) | Q(utilisateur__is_active=True)).exclude(utils_anonymisation.Conditions_familles_anonymes())
        return set(qs.values_list("pk", flat=True)) - self.Get_familles_actives(date_limite)

    def Analyser(self, date_limite=None):
        from core.models import Famille
        elements = []
        for lot in Decoupe(self.Get_candidats(date_limite)):
            for famille in Famille.objects.select_related("utilisateur").filter(pk__in=lot):
                derniere_connexion = famille.utilisateur.last_login if famille.utilisateur else None
                info = "Dernière connexion le %s" % derniere_connexion.strftime("%d/%m/%Y") if derniere_connexion else "Jamais connecté"
                elements.append(Element(id=famille.pk, label=famille.nom or "Famille ID%d" % famille.pk, info=info, url=Url_famille(famille.pk)))
        elements.sort(key=lambda element: element.label.lower())
        return Resultat_analyse(nbre=len(elements), elements=elements)

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Famille, Utilisateur
        resultat = Resultat_execution()
        ids = [pk for pk in self.Get_candidats(date_limite) if str(pk) not in exclusions]
        for lot in Decoupe(ids):
            with transaction.atomic():
                Utilisateur.objects.filter(famille__pk__in=lot).update(is_active=False)
                resultat.nbre += Famille.objects.filter(pk__in=lot).update(internet_actif=False)
        resultat.nbre_exclus = len(exclusions)
        return resultat


# ------------------------------------------------------------------------------------------------
# Contacts des individus inactifs
# ------------------------------------------------------------------------------------------------

class Supprimer_contacts(Operation):
    code = "contacts_inactifs"
    titre = "Supprimer les contacts des individus inactifs"
    description = ("Supprime les contacts d'urgence et les personnes autorisées à récupérer les individus sans activité depuis la date limite "
                   "(ce sont des données personnelles de tiers).")
    categorie = "rgpd"
    icone = "fa-address-book-o"
    delai_defaut = 36
    delai_minimum_jours = 90
    label_date = "Individus sans activité depuis le"

    def Get_queryset(self, date_limite=None):
        from core.models import ContactUrgence
        ids = set(ContactUrgence.objects.values_list("individu_id", flat=True).distinct()) - self.Get_individus_actifs(date_limite)
        return ContactUrgence.objects.select_related("individu").filter(individu_id__in=ids)

    def Analyser(self, date_limite=None):
        elements = [Element(id=contact.pk, label="%s %s" % (contact.nom, contact.prenom),
                            info="Contact de %s" % Label_individu(contact.individu), url=Url_individu(contact.famille_id, contact.individu_id))
                    for contact in self.Get_queryset(date_limite).order_by("nom", "prenom")]
        return Resultat_analyse(nbre=len(elements), elements=elements)

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        resultat = Resultat_execution()
        ids = [contact.pk for contact in self.Get_queryset(date_limite) if str(contact.pk) not in exclusions]
        from core.models import ContactUrgence
        for lot in Decoupe(ids):
            resultat.nbre += ContactUrgence.objects.filter(pk__in=lot).delete()[0]
        resultat.nbre_exclus = len(exclusions)
        return resultat


# ------------------------------------------------------------------------------------------------
# Individus détachés inutilisés
# ------------------------------------------------------------------------------------------------

class Supprimer_individus_detaches(Operation):
    code = "individus_detaches"
    titre = "Supprimer les individus détachés inutilisés"
    description = ("Supprime les individus qui ne sont rattachés à aucune famille et n'ont aucune activité depuis la date limite "
                   "(fiches restées orphelines après un détachement ou une fusion).")
    categorie = "rgpd"
    icone = "fa-user-o"
    delai_defaut = 12
    delai_minimum_jours = 90
    label_date = "Aucune activité depuis le"

    def Get_candidats(self, date_limite=None):
        from core.models import Individu
        from core.models import Famille
        ids = set(Individu.objects.filter(rattachement__isnull=True, date_creation__date__lt=date_limite).values_list("pk", flat=True))
        ids -= set(Famille.objects.filter(allocataire__isnull=False).values_list("allocataire_id", flat=True))
        ids -= set(Famille.objects.filter(titulaire_helios__isnull=False).values_list("titulaire_helios_id", flat=True))
        ids -= set(Famille.objects.filter(tiers_solidaire__isnull=False).values_list("tiers_solidaire_id", flat=True))
        return ids - self.Get_individus_actifs(date_limite)

    def Analyser(self, date_limite=None):
        from core.models import Individu
        elements = []
        for lot in Decoupe(self.Get_candidats(date_limite)):
            for individu in Individu.objects.filter(pk__in=lot):
                elements.append(Element(id=individu.pk, label=Label_individu(individu), info="Créé le %s" % individu.date_creation.strftime("%d/%m/%Y")))
        elements.sort(key=lambda element: element.label.lower())
        return Resultat_analyse(nbre=len(elements), elements=elements)

    def Executer(self, date_limite=None, exclusions=set(), request=None):
        from core.models import Individu, Transport, Piece, Information
        resultat = Resultat_execution()
        for individu in Individu.objects.filter(pk__in=[pk for pk in self.Get_candidats(date_limite) if str(pk) not in exclusions]):
            if not Is_individu_supprimable(individu=individu):
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s (ID%d) conservé : il est allocataire, titulaire Hélios ou tiers solidaire d'une famille" % (Label_individu(individu), individu.pk))
                continue
            try:
                with transaction.atomic():
                    Transport.objects.filter(individu=individu).delete()
                    for piece in Piece.objects.filter(individu=individu):
                        piece.delete()
                    for information in Information.objects.filter(individu=individu):
                        information.delete()
                    individu.delete()
                resultat.nbre += 1
            except ProtectedError:
                resultat.nbre_echecs += 1
                resultat.lignes_detail.append("%s (ID%d) conservé : des données y sont rattachées (inscription, prestation...)" % (Label_individu(individu), individu.pk))
        resultat.nbre_exclus = len(exclusions)
        return resultat
