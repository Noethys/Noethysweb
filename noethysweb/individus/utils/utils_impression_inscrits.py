# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from django.db.models import Sum, Q
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from core.models import Inscription, Ventilation, Prestation, Rattachement, Cotisation, ContactUrgence, Scolarite
from core.utils import utils_texte, utils_impression, utils_questionnaires


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        kwds["taille_page"] = landscape(A4) if kwds["dict_donnees"]["orientation"] == "paysage" else portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        # Importation des inscriptions
        conditions = Q(activite=self.dict_donnees["activite"]) & (Q(date_fin__isnull=True) | Q(date_fin__gte=self.dict_donnees["date_situation"]))
        inscriptions = Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif", "activite", "activite__structure").filter(conditions).order_by("individu__nom", "individu__prenom")

        # Calcul des soldes
        dict_ventilations = {temp["prestation_id"]: temp["total"] for temp in Ventilation.objects.values("prestation_id").filter(prestation__activite=self.dict_donnees["activite"]).annotate(total=Sum("montant"))}
        dict_soldes = {}
        for prestation in Prestation.objects.values("famille_id", "individu_id", "pk").filter(activite=self.dict_donnees["activite"]).annotate(total=Sum("montant")):
            key = (prestation["famille_id"], prestation["individu_id"])
            dict_soldes.setdefault(key, decimal.Decimal(0))
            dict_soldes[key] += dict_ventilations.get(prestation["pk"], decimal.Decimal(0)) - prestation["total"]
        del dict_ventilations

        # Recherche des parents
        dict_parents = {}
        liste_enfants = []
        for rattachement in Rattachement.objects.select_related("individu").all():
            if rattachement.categorie == 1:
                dict_parents.setdefault(rattachement.famille_id, [])
                dict_parents[rattachement.famille_id].append(rattachement.individu)
            if rattachement.categorie == 2:
                liste_enfants.append((rattachement.famille_id, rattachement.individu_id))

        def Rechercher_tel_parents(inscription=None):
            liste_tel = []
            if (inscription.famille_id, inscription.individu_id) in liste_enfants:
                for individu in dict_parents.get(inscription.famille_id, []):
                    if individu.tel_mobile and individu != inscription.individu:
                        liste_tel.append("%s : %s" % (individu.prenom, individu.tel_mobile))
            return " | ".join(liste_tel)

        def Rechercher_mail_parents(inscription=None):
            liste_mail = []
            if (inscription.famille_id, inscription.individu_id) in liste_enfants:
                for individu in dict_parents.get(inscription.famille_id, []):
                    if individu.mail and individu != inscription.individu:
                        liste_mail.append("%s : %s" % (individu.prenom, individu.mail))
            return " | ".join(liste_mail)

        # Recherche des contacts d'urgence
        contacts = {}
        for contact in ContactUrgence.objects.filter(individu_id__in=[inscription.individu_id for inscription in inscriptions]):
            contacts.setdefault((contact.famille_id, contact.individu_id), [])
            contacts[(contact.famille_id, contact.individu_id)].append(contact)

        def Rechercher_tel_contacts(inscription=None):
            liste_tel = []
            for contact in contacts.get((inscription.famille_id, inscription.individu_id), []):
                autorisations = []
                if contact.autorisation_sortie: autorisations.append("Sortie")
                if contact.autorisation_sortie: autorisations.append("Appel")
                tels = []
                if contact.tel_mobile: tels.append(contact.tel_mobile)
                if contact.tel_domicile: tels.append(contact.tel_domicile)
                if contact.tel_travail: tels.append(contact.tel_travail)
                liste_tel.append("%s %s (%s - %s) : %s" % (contact.nom or "", contact.prenom or "", contact.lien or "Lien inconnu", "+".join(autorisations), ", ".join(tels)))
            return " | ".join(liste_tel)

        # Recherche des cotisations
        dict_cotisations = {}
        for cotisation in Cotisation.objects.filter(date_debut__lte=self.dict_donnees["activite"].date_fin, date_fin__gte=self.dict_donnees["activite"].date_debut).order_by("-date_debut"):
            dict_cotisations.setdefault(cotisation.famille_id, [])
            dict_cotisations[cotisation.famille_id].append(cotisation)

        def Rechercher_cotisation(inscription=None):
            for cotisation in dict_cotisations.get(inscription.famille_id, []):
                if not cotisation.individu_id or cotisation.individu_id == inscription.individu_id:
                    return str(cotisation.numero or "")
            return ""

        # Scolarité
        scolarites = {}
        for scolarite in Scolarite.objects.select_related("ecole", "classe", "niveau").filter(individu_id__in=[inscription.individu_id for inscription in inscriptions], date_fin__gte=self.dict_donnees["date_situation"], date_debut__lte=self.dict_donnees["date_situation"]).order_by("date_debut"):
            scolarites[scolarite.individu_id] = scolarite

        # Questionnaires
        questionnaires_individus = utils_questionnaires.ChampsEtReponses(categorie="individu", filtre_reponses=Q(individu__in=[i.individu for i in inscriptions]))
        questionnaires_familles = utils_questionnaires.ChampsEtReponses(categorie="famille", filtre_reponses=Q(famille__in=[i.famille for i in inscriptions]))

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_activite = ParagraphStyle(name="centre", fontName="Helvetica-bold", alignment=1, fontSize=8, spaceBefore=0, spaceAfter=20, leading=0)
        style_infos = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceBefore=10, spaceAfter=0, leading=0)

        # Création du titre du document
        self.Insert_header()

        # Nom de l'activité
        self.story.append(Paragraph(self.dict_donnees["activite"].nom, style_activite))

        # Préparation du tableau
        data_tableau, largeurs_colonnes, ligne = [], [], []

        total_largeurs_fixes = 0
        nbre_colonnes_auto = 0
        for colonne in self.dict_donnees["colonnes_perso"]:
            ligne.append(colonne["nom"])
            total_largeurs_fixes += int(colonne["largeur"]) if colonne["largeur"] != "automatique" else 0
            nbre_colonnes_auto += 1 if colonne["largeur"] == "automatique" else 0
        data_tableau.append(ligne)

        # Calcul des largeurs de colonnes
        largeur_contenu = self.taille_page[0] - 75
        largeur_a_repartir = largeur_contenu - total_largeurs_fixes
        for colonne in self.dict_donnees["colonnes_perso"]:
            if colonne["largeur"] == "automatique":
                largeur = largeur_a_repartir / nbre_colonnes_auto
            else:
                largeur = int(colonne["largeur"])
            largeurs_colonnes.append(largeur)

        # Création des valeurs
        for inscription in inscriptions:
            valeurs = {
                "date_debut": inscription.date_debut.strftime("%d/%m/%Y") if inscription.date_debut else "",
                "date_fin": inscription.date_fin.strftime("%d/%m/%Y") if inscription.date_fin else "",
                "groupe": inscription.groupe.nom,
                "categorie_tarif": inscription.categorie_tarif.nom,
                "nom": inscription.individu.nom,
                "prenom": inscription.individu.prenom,
                "date_naiss": inscription.individu.date_naiss.strftime("%d/%m/%Y") if inscription.individu.date_naiss else "",
                "age": str(inscription.individu.Get_age()) if inscription.individu.date_naiss else "",
                "mail": inscription.individu.mail,
                "portable": inscription.individu.tel_mobile,
                "tel_parents": Rechercher_tel_parents(inscription),
                "mail_parents": Rechercher_mail_parents(inscription),
                "tel_contacts": Rechercher_tel_contacts(inscription),
                "individu_ville": inscription.individu.ville_resid,
                "famille": inscription.famille.nom,
                "famille_ville": inscription.famille.ville_resid,
                "num_cotisation": Rechercher_cotisation(inscription),
                "ecole": scolarites[inscription.individu_id].ecole.nom if inscription.individu_id in scolarites else None,
                "classe": scolarites[inscription.individu_id].classe.nom if inscription.individu_id in scolarites and scolarites[inscription.individu_id].classe else None,
                "statut": inscription.get_statut_display(),
                "solde": utils_texte.Formate_montant(dict_soldes.get((inscription.famille_id, inscription.individu_id), decimal.Decimal(0))),
            }

            # Ajout des réponses des questionnaires
            valeurs.update({"question_famille_%d" % question["IDquestion"]: question["reponse"] for question in questionnaires_familles.GetDonnees(inscription.famille_id)})
            valeurs.update({"question_individu_%d" % question["IDquestion"]: question["reponse"] for question in questionnaires_individus.GetDonnees(inscription.individu_id)})

            # Création de la ligne du tableau
            data_tableau.append([Paragraph(valeurs.get(colonne["code"], None) or "", style_defaut) for colonne in self.dict_donnees["colonnes_perso"]])

        # Finalisation du tableau
        style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
        ])
        # Création du tableau
        tableau = Table(data_tableau, largeurs_colonnes)
        tableau.setStyle(style)
        self.story.append(tableau)

        # Nombre d'inscriptions
        self.story.append(Paragraph("%d inscriptions" % len(inscriptions), style_infos))
