# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from django.conf import settings
from django.db.models import Q
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from core.models import Activite, Rattachement, RegimeAlimentaire, Information, ContactUrgence
from core.utils import utils_dates, utils_impression, utils_polices
from individus.forms.edition_informations import COLONNES_DEFAUT


# Titre et largeur de chaque colonne (largeur fixe en points, ou None = largeur partagée avec les autres colonnes souples)
COLONNES = {
    "infos_perso": {"titre": "Informations", "largeur": None},
    "regimes": {"titre": "Régimes", "largeur": None},
    "sieste": {"titre": "Sieste", "largeur": None},
    "parents": {"titre": "Parents", "largeur": None},
    "contacts": {"titre": "Contacts", "largeur": None},
}
ORDRE_COLONNES = ["infos_perso", "regimes", "sieste", "parents", "contacts"]


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        if kwds["dict_donnees"]["orientation"] == "paysage":
            kwds["taille_page"] = landscape(A4)
        else:
            kwds["taille_page"] = portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        # Importation des individus rattachés
        param_activites = self.dict_donnees["activites"]
        if param_activites["type"] == "groupes_activites":
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
        conditions = Q(individu__inscription__activite__in=liste_activites)
        if self.dict_donnees["presents"]:
            conditions &= Q(individu__inscription__consommation__date__gte=self.dict_donnees["presents"][0], individu__inscription__consommation__date__lte=self.dict_donnees["presents"][1])
        rattachements_temp = Rattachement.objects.select_related("individu", "famille", "individu__medecin", "individu__type_sieste").prefetch_related("individu__regimes_alimentaires").filter(conditions).distinct().order_by("individu__nom", "individu__prenom")

        # Colonnes sélectionnées (dans l'ordre d'affichage, quel que soit l'ordre de saisie)
        choix = self.dict_donnees.get("colonnes") or COLONNES_DEFAUT
        colonnes = [code for code in ORDRE_COLONNES if code in choix]

        # Importation de toutes les informations
        dict_informations = {}
        if "infos_perso" in colonnes:
            for information in Information.objects.filter(diffusion_listing_enfants=True).order_by("intitule"):
                dict_informations.setdefault(information.individu_id, [])
                dict_informations[information.individu_id].append(information)

        # Importation de tous les contacts d'urgence et de sortie
        dict_contacts = {}
        if "contacts" in colonnes:
            for contact in ContactUrgence.objects.all().order_by("nom", "prenom"):
                dict_contacts.setdefault((contact.individu_id, contact.famille_id), [])
                dict_contacts[(contact.individu_id, contact.famille_id)].append(contact)

        # Importation de tous les représentants (parents)
        dict_representants = {}
        if "parents" in colonnes:
            for rattachement in Rattachement.objects.select_related("individu").filter(categorie=1).order_by("-titulaire", "individu__nom", "individu__prenom"):
                dict_representants.setdefault(rattachement.famille_id, [])
                dict_representants[rattachement.famille_id].append(rattachement)

        # Les colonnes informations, régimes et sieste servent de filtre : on conserve uniquement les individus
        # qui ont du contenu dans l'une d'elles. Si aucune n'est cochée, tous les individus sont conservés.
        def a_du_contenu(individu):
            if "infos_perso" in colonnes and individu.pk in dict_informations: return True
            if "regimes" in colonnes and individu.regimes_alimentaires.all(): return True
            if "sieste" in colonnes and individu.type_sieste_id: return True
            return False

        colonnes_filtre = [code for code in colonnes if code in ("infos_perso", "regimes", "sieste")]
        rattachements = [r for r in rattachements_temp if not colonnes_filtre or a_du_contenu(r.individu)]

        if not rattachements:
            self.erreurs.append("Aucun individu n'a été trouvé avec les paramètres donnés")

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName=utils_polices.FONT_NORMAL, fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName=utils_polices.FONT_NORMAL, alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_detail = ParagraphStyle(name="centre", fontName=utils_polices.FONT_NORMAL, alignment=1, fontSize=6, textColor="gray", spaceAfter=0, leading=8)

        # Création du titre du document
        self.Insert_header()

        def Img(fichier=""):
            return "<img src='%s/images/%s' width='6' height='6' valign='middle'/> " % (settings.STATIC_ROOT, fichier)

        # Légende des autorisations des contacts
        if "contacts" in colonnes:
            texte = "%s&nbsp;Autorisé à récupérer l'individu " % Img("sortie.png")
            texte += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; %s&nbsp;A contacter en cas d'urgence" % Img("appel.png")
            self.story.append(Paragraph(texte, style_centre))
            self.story.append(Spacer(0, 10))

        # Préparation du tableau
        largeur_contenu = self.taille_page[0] - 75
        largeur_individu = 120
        dataTableau = [["Individu"] + [COLONNES[code]["titre"] for code in colonnes]]

        # Les colonnes à largeur fixe sont déduites, le reste est réparti à parts égales entre les colonnes souples
        largeur_fixe = sum(COLONNES[code]["largeur"] for code in colonnes if COLONNES[code]["largeur"])
        nbre_souples = len([code for code in colonnes if not COLONNES[code]["largeur"]])
        largeur_souple = (largeur_contenu - largeur_individu - largeur_fixe) / nbre_souples if nbre_souples else 0
        largeursColonnes = [largeur_individu] + [COLONNES[code]["largeur"] or largeur_souple for code in colonnes]

        # Remplissage du tableau
        for rattachement in rattachements:
            ligne = []
            individu = rattachement.individu

            # Identité de l'individu
            detail = ""
            if individu.date_naiss:
                detail += "né%s le %s" % ("e" if individu.civilite in (2, 3, 5) else "", utils_dates.ConvertDateToFR(individu.date_naiss))
            if individu.info_garde:
                detail += "<br/><font color='red'>Info garde : %s</font>" % individu.info_garde
            ligne.append([Paragraph(individu.Get_nom(), style_centre), Paragraph(detail, style_detail)])

            for code in colonnes:

                # Informations personnelles
                if code == "infos_perso":
                    contenu_tableau = []
                    for information in dict_informations.get(rattachement.individu_id, []):
                        texte = "<b>%s</b>" % information.intitule
                        if information.description:
                            texte += " : %s" % information.description
                        contenu_tableau.append(Paragraph(texte, style_defaut))
                    ligne.append(contenu_tableau)

                # Régimes alimentaires
                if code == "regimes":
                    texte_regimes = ", ".join([regime.nom for regime in individu.regimes_alimentaires.all()])
                    ligne.append([Paragraph(texte_regimes, style_defaut)])

                # Sieste
                if code == "sieste":
                    ligne.append([Paragraph(individu.type_sieste.nom if individu.type_sieste_id else "", style_centre)])

                # Contacts d'urgence et de sortie
                if code == "contacts":
                    contacts = []
                    for contact in dict_contacts.get((rattachement.individu_id, rattachement.famille_id), []):
                        autorisations = []
                        if contact.autorisation_sortie: autorisations.append(Img("sortie.png"))
                        if contact.autorisation_appel: autorisations.append(Img("appel.png"))
                        texte = "".join(autorisations)
                        texte += "<b>%s</b>%s<br/>" % (contact.Get_nom(), " (%s)" % contact.lien if contact.lien else "")
                        for label, champ in [("Domicile", "tel_domicile"), ("Portable", "tel_mobile"), ("Pro", "tel_travail"), ("Email", "mail")]:
                            if getattr(contact, champ):
                                texte += "%s : %s<br/>" % (label, getattr(contact, champ))
                        contacts.append(Paragraph(texte, style_defaut))
                    ligne.append(contacts)

                # Coordonnées des parents
                if code == "parents":
                    parents = []
                    for representant in dict_representants.get(rattachement.famille_id, []):
                        texte = "<b>%s</b>%s<br/>" % (representant.individu.Get_nom(), " (titulaire)" if representant.titulaire else "")
                        for label, champ in [("Domicile", "tel_domicile"), ("Portable", "tel_mobile"), ("Pro", "travail_tel"), ("Email", "mail")]:
                            if getattr(representant.individu, champ):
                                texte += "%s : %s<br/>" % (label, getattr(representant.individu, champ))
                        parents.append(Paragraph(texte, style_defaut))
                    ligne.append(parents)

            # Finalisation de la ligne
            dataTableau.append(ligne)

        # Finalisation du tableau
        style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
        ])
        # Création du tableau
        tableau = Table(dataTableau, largeursColonnes)
        tableau.setStyle(style)
        self.story.append(tableau)
