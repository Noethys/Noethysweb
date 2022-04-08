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
from core.models import Activite, Groupe, Lien, Rattachement, ContactUrgence
from core.data.data_liens import DICT_TYPES_LIENS
from core.data import data_civilites
from core.utils import utils_dates, utils_impression


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
            conditions = Q(individu__inscription__activite__in=liste_activites)
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
            conditions = Q(individu__inscription__activite__in=liste_activites)
        if param_activites["type"] == "groupes":
            liste_groupes = Groupe.objects.filter(pk__in=param_activites["ids"])
            conditions = Q(individu__inscription__groupe__in=liste_groupes)

        if self.dict_donnees["presents"]:
            conditions &= Q(individu__inscription__consommation__date__gte=self.dict_donnees["presents"][0], individu__inscription__consommation__date__lte=self.dict_donnees["presents"][1])
        rattachements = Rattachement.objects.select_related("individu", "famille", "individu__medecin").filter(conditions).distinct().order_by("individu__nom", "individu__prenom")

        # Importation de tous les représentants
        dict_representants = {}
        for rattachement in Rattachement.objects.select_related("individu").filter(categorie=1):
            dict_representants.setdefault(rattachement.famille_id, [])
            dict_representants[rattachement.famille_id].append(rattachement)

        # Importation de tous les liens
        dict_liens = {}
        for lien in Lien.objects.all():
            dict_liens[(lien.individu_sujet_id, lien.individu_objet_id)] = lien

        # Importation de tous les contacts
        dict_contacts = {}
        for contact in ContactUrgence.objects.all().order_by("nom", "prenom"):
            key = (contact.individu_id, contact.famille_id)
            dict_contacts.setdefault(key, [])
            dict_contacts[key].append(contact)

        if not rattachements:
            self.erreurs.append("Aucun individu n'a été trouvé avec les paramètres donnés")

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_detail = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=6, textColor="gray", spaceAfter=0, leading=8)

        # Création du titre du document
        self.Insert_header()

        def Img(fichier=""):
            return "<img src='%s/images/%s' width='6' height='6' valign='middle'/> " % (settings.STATIC_ROOT, fichier)

        # Légende
        texte = "%s&nbsp;Autorisé à récupérer l'individu " % Img("sortie.png")
        texte += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; %s&nbsp;A contacter en cas d'urgence" % Img("appel.png")
        self.story.append(Paragraph(texte, style_centre))
        self.story.append(Spacer(0, 10))

        # Préparation du tableau
        largeur_contenu = self.taille_page[0] - 75
        dataTableau = [("Individu", "Représentants", "Contacts", "Médecin")]
        largeursColonnes = [100, (largeur_contenu-180)/2, (largeur_contenu-180)/2, 80]

        # Remplissage du tableau
        for rattachement in rattachements:
            ligne = []

            # Identité de l'individu
            detail = ""
            if rattachement.individu.date_naiss:
                detail += "<br/>né%s le %s" % ("e" if rattachement.individu.civilite in (2, 3, 5) else "", utils_dates.ConvertDateToFR(rattachement.individu.date_naiss))
            if rattachement.individu.situation_familiale:
                detail += "<br/>Situation parentale : %s" % rattachement.individu.get_situation_familiale_display()
            if rattachement.individu.type_garde:
                detail += "<br/>Type de garde : %s" % rattachement.individu.get_type_garde_display()
            if rattachement.individu.info_garde:
                detail += "<br/><font color='red'>Info garde : %s</font>" % rattachement.individu.info_garde
            ligne.append([Paragraph(rattachement.individu.Get_nom(), style_centre), Paragraph(detail, style_detail)])

            # Représentants
            representants = []
            for representant in dict_representants.get(rattachement.famille_id):

                # Lien du représentant avec l'individu
                texte_lien = []
                lien = dict_liens.get((representant.individu_id, rattachement.individu_id), None)
                dict_civilite = data_civilites.GetCiviliteForIndividu(individu=representant.individu)
                if lien and lien.idtype_lien and dict_civilite["sexe"]:
                    texte_lien.append(DICT_TYPES_LIENS[lien.idtype_lien][dict_civilite["sexe"]])
                if representant.titulaire:
                    texte_lien.append("titulaire")

                # Nom représentant
                texte = "<b>%s</b> (%s)<br/>" % (representant.individu.Get_nom(), " ".join(texte_lien))

                # Coordonnées du représentant
                for label, code in [("Domicile", "tel_domicile"), ("Portable", "tel_mobile"), ("Pro", "travail_tel"), ("Email", "mail")]:
                    if getattr(representant.individu, code):
                        texte += "%s : %s<br/>" % (label, getattr(representant.individu, code))

                representants.append(Paragraph(texte, style_defaut))
            ligne.append(representants)

            # Contacts
            contacts = []
            for contact in dict_contacts.get((rattachement.individu_id, rattachement.famille_id), []):

                # Autorisations du contact
                autorisations = []
                if contact.autorisation_sortie: autorisations.append(Img("sortie.png"))
                if contact.autorisation_appel: autorisations.append(Img("appel.png"))
                texte = "".join(autorisations)

                # Nom contact
                texte += "<b>%s</b>%s<br/>" % (contact.Get_nom(), " (%s)" % contact.lien if contact.lien else "")

                # Coordonnées du contact
                for label, code in [("Domicile", "tel_domicile"), ("Portable", "tel_mobile"), ("Pro", "tel_travail"), ("Email", "mail")]:
                    if getattr(contact, code):
                        texte += "%s : %s<br/>" % (label, getattr(contact, code))

                contacts.append(Paragraph(texte, style_defaut))
            ligne.append(contacts)

            # Médecin
            if rattachement.individu.medecin:
                texte = "%s %s" % (rattachement.individu.medecin.nom, rattachement.individu.medecin.prenom or "")
                if rattachement.individu.medecin.tel_cabinet:
                    texte += "<br/>Tél : %s" % rattachement.individu.medecin.tel_cabinet
                texte_medecin = Paragraph(texte, style_centre)
            else:
                texte_medecin = ""
            ligne.append(texte_medecin)

            # Finalisation de la ligne
            dataTableau.append(ligne)

        # Finalisation du tableau
        style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
        ])
        # Création du tableau
        tableau = Table(dataTableau, largeursColonnes)
        tableau.setStyle(style)
        self.story.append(tableau)
