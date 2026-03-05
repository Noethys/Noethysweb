# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from django.conf import settings
from django.db.models import Q
from django.core.cache import cache
from reportlab.platypus import Paragraph, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import Lien, Rattachement, ContactUrgence, Information, Assurance, Organisateur, Scolarite, Activite, Inscription, Structure
from core.data.data_liens import DICT_TYPES_LIENS
from core.data import data_civilites
from core.utils import utils_dates, utils_impression, utils_questionnaires
from individus.utils import utils_vaccinations
import os
from reportlab.platypus import Spacer


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        # Importation des rattachements
        conditions = Q(pk__in=self.dict_donnees["rattachements"])
        rattachements = Rattachement.objects.select_related("individu", "famille", "individu__medecin").prefetch_related("individu__regimes_alimentaires", "individu__maladies", "individu__allergies", "individu__dispmed").filter(conditions).distinct().order_by("individu__nom", "individu__prenom")
        if not rattachements:
            self.erreurs.append("Aucun individu n'a été trouvé avec les paramètres donnés")

        # Récupération des IDs nécessaires pour filtrer les requêtes
        individus_ids = [r.individu_id for r in rattachements]
        familles_ids = [r.famille_id for r in rattachements]

        # Importation de tous les représentants
        dict_representants = {}
        for rattachement in Rattachement.objects.select_related("individu").filter(categorie=1, famille_id__in=familles_ids):
            dict_representants.setdefault(rattachement.famille_id, [])
            dict_representants[rattachement.famille_id].append(rattachement)

        # Importation de tous les liens
        dict_liens = {}
        for lien in Lien.objects.filter(Q(individu_sujet_id__in=individus_ids) | Q(individu_objet_id__in=individus_ids)):
            dict_liens[(lien.individu_sujet_id, lien.individu_objet_id)] = lien

        # Importation de toutes les assurances
        dict_assurances = {}
        for assurance in Assurance.objects.select_related("assureur").filter(Q(individu_id__in=individus_ids) | Q(famille_id__in=familles_ids), Q(date_debut__lte=datetime.date.today()) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))).order_by("date_debut"):
            dict_assurances[(assurance.individu_id, assurance.famille_id)] = assurance

        # Importation de toutes les scolarités
        dict_scolarites = {}
        for scolarite in Scolarite.objects.select_related("ecole", "classe", "niveau").filter(individu_id__in=individus_ids, date_fin__gte=datetime.date.today()).order_by("date_debut"):
            dict_scolarites[scolarite.individu_id] = scolarite

        # Importation de tous les contacts
        dict_contacts = {}
        for contact in ContactUrgence.objects.filter(Q(individu_id__in=individus_ids) | Q(famille_id__in=familles_ids)).order_by("nom", "prenom"):
            key = (contact.individu_id, contact.famille_id)
            dict_contacts.setdefault(key, [])
            dict_contacts[key].append(contact)

        # Importation de toutes les informations
        dict_informations = {}
        for information in Information.objects.filter(individu_id__in=individus_ids).order_by("intitule"):
            dict_informations.setdefault(information.individu_id, [])
            dict_informations[information.individu_id].append(information)

        # Importation des vaccinations
        dict_vaccinations = utils_vaccinations.Get_tous_vaccins()

        # Importation des questionnaires
        individus_inscrits=[r.individu for r in rattachements]
        inscriptions_accessibles = Inscription.objects.filter(individu__in=individus_inscrits)
        activites_accessibles = Activite.objects.filter(idactivite__in=inscriptions_accessibles.values('activite'))
        structures_accessibles = Structure.objects.filter(idstructure__in=activites_accessibles.values('structure'))

        questionnaires_individus = utils_questionnaires.ChampsEtReponses(
            categorie="individu",
            structure=structures_accessibles,
            filtre_reponses=(Q(individu__in=individus_inscrits) & Q(reponse__isnull=False) & ~Q(
                reponse="")))
        questionnaires_familles = utils_questionnaires.ChampsEtReponses(
            categorie="famille",
            filtre_reponses=(Q(famille__in=[r.famille for r in rattachements]) & Q(reponse__isnull=False) & ~Q(
                reponse="")))

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_droite = ParagraphStyle(name="droite", fontName="Helvetica", alignment=2, fontSize=7, spaceAfter=0, leading=9)
        style_identite = ParagraphStyle(name="identite", fontName="Helvetica-Bold", fontSize=16, spaceAfter=0, leading=28)

        def Img(fichier=""):
            return "<img src='%s/images/%s' width='6' height='6' valign='middle'/> " % (settings.STATIC_ROOT, fichier)

        def Tableau(titre="", aide="", contenu=[], bord_bas=False):
            dataTableau = [[titre, aide]]
            dataTableau.append([contenu, ""])
            tableau = Table(dataTableau, [largeur_contenu/2, largeur_contenu/2])
            style = [
                ('SPAN', (0, 1), (-1, 1)),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                ('LINEBEFORE', (0, 0), (0, -1), 0.25, colors.black),
                ('LINEAFTER', (-1, 0), (-1, -1), 0.25, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
                ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 7),
                ('FONT', (1, 0), (1, 0), "Helvetica", 6),
                ('TEXTCOLOR', (0, 0), (-1, 0), (1, 1, 1)),
                ('BACKGROUND', (0, 0), (-1, 0), (0.5, 0.5, 0.5)),
                ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ]
            if bord_bas:
                style.append(('LINEBELOW', (0, -1), (-1, -1), 0.25, colors.black))
            tableau.setStyle(TableStyle(style))
            return tableau

        # Préparation du tableau
        largeur_contenu = self.taille_page[0] - 75

        # Importation de l'organisateur (une seule fois avant la boucle)
        organisateur = cache.get('organisateur', None)
        if not organisateur:
            organisateur = cache.get_or_set('organisateur', Organisateur.objects.filter(pk=1).first())

        # Tri des pages
        def tri_classe(rattachement):
            scolarite = dict_scolarites.get(rattachement.individu_id, None)
            return scolarite.classe.nom if scolarite else ""

        if self.dict_donnees["tri"] == "classe":
            rattachements = sorted(rattachements, key=tri_classe)

        # Remplissage du tableau
        for rattachement in rattachements:

            # Importation de la photo de l'individu
            nom_fichier = rattachement.individu.Get_photo(forTemplate=False)
            if "media/" in nom_fichier:
                nom_fichier = settings.MEDIA_ROOT + nom_fichier.replace("media/", "")

            if os.path.exists(nom_fichier):
                try:
                    photo_individu = Image(nom_fichier, width=64, height=64)
                except:
                    photo_individu = None
            else:
                photo_individu = None

            detail_individu = []

            # Nom de l'individu
            detail_individu.append(Paragraph(rattachement.individu.Get_nom(), style_identite))

            # Date de naissance
            if rattachement.individu.date_naiss:
                texte_date_naiss = "Né%s le %s" % ("e" if rattachement.individu.civilite in (2, 3, 5) else "", utils_dates.ConvertDateToFR(rattachement.individu.date_naiss))
                if rattachement.individu.ville_naiss:
                    texte_date_naiss += " à %s" % rattachement.individu.ville_naiss
                texte_date_naiss += ", %s ans." % rattachement.individu.Get_age()
            else:
                texte_date_naiss = "Date de naissance inconnue."
            detail_individu.append(Paragraph(texte_date_naiss, style_defaut))

            # Adresse
            texte_adresse = rattachement.individu.Get_adresse_complete()
            for label, code in [("Domi.", "tel_domicile"), ("Port.", "tel_mobile"), ("Pro.", "travail_tel"), ("Email", "mail")]:
                if getattr(rattachement.individu, code):
                    texte_adresse += "&nbsp;&nbsp; %s : %s" % (label, getattr(rattachement.individu, code))
            detail_individu.append(Paragraph(texte_adresse, style_defaut))

            # Scolarité
            scolarite = dict_scolarites.get(rattachement.individu_id, None)
            if scolarite:
                texte_scolarite = "Classe %s-%s : %s (%s - %s)." % (
                    scolarite.date_debut.strftime("%Y"),
                    scolarite.date_fin.strftime("%Y"),
                    scolarite.niveau.abrege if scolarite.niveau else "",
                    scolarite.classe.nom if scolarite.classe else "",
                    scolarite.ecole.nom if scolarite.ecole else "",
                )
                detail_individu.append(Paragraph(texte_scolarite, style_defaut))

            # Construction du tableau identité
            col0=""
            if photo_individu:
                    col0 = photo_individu
            else:
                    col0 = Spacer(64, 64)
            dataTableau = [(col0, detail_individu, "%s\nEdité le %s" % (
            organisateur.nom, utils_dates.ConvertDateToFR(str(datetime.date.today()))))]
            col_widths = [self.taille_page[0] - 100 - 75,
                              100]  # Ajuster la largeur si pas de photo
            style = TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ('FONT', (2, 0), (2, 0), "Helvetica", 6),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('TOPPADDING', (0, 0), (0, 0), 0),
                ('BOTTOMPADDING', (0, 0), (0, 0), 0),
            ])
            tableau = Table(dataTableau, [64, self.taille_page[0] - 100 - 75 - 64, 100])
            tableau.setStyle(style)
            self.story.append(tableau)

            # Représentants
            contenu_tableau = []
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
                texte += representant.individu.Get_adresse_complete()
                for label, code in [("Domi.", "tel_domicile"), ("Port.", "tel_mobile"), ("Pro.", "travail_tel"), ("Email", "mail")]:
                    if getattr(representant.individu, code):
                        texte += "&nbsp;&nbsp; %s : %s" % (label, getattr(representant.individu, code))

                contenu_tableau.append(Paragraph(texte, style_defaut))
            self.story.append(Tableau(titre="Représentants".upper(), contenu=contenu_tableau))

            # Contacts
            contenu_tableau = []
            for contact in dict_contacts.get((rattachement.individu_id, rattachement.famille_id), []):
                # Nom contact
                texte = "<b>%s</b>%s" % (contact.Get_nom(), " (%s)" % contact.lien if contact.lien else "")

                # Coordonnées du contact
                for label, code in [("Domi.", "tel_domicile"), ("Port.", "tel_mobile"), ("Pro.", "tel_travail"), ("Email", "mail")]:
                    if getattr(contact, code):
                        texte += "&nbsp;&nbsp; %s : %s" % (label, getattr(contact, code))

                contenu_tableau.append(Paragraph(texte, style_defaut))

            if not self.dict_donnees["mode_condense"]:
                contenu_tableau.append(Paragraph("<br/><br/><br/>", style_defaut))
            self.story.append(Tableau(titre="Contacts".upper(), aide="", contenu=contenu_tableau))

            #Allergies
            texte_allergies = ", ".join([f"<b>{allergie.nom}</b>" for allergie in rattachement.individu.allergies.all()])
            if rattachement.individu.allergies_detail:
                texte_allergies += f" : {rattachement.individu.allergies_detail}"
            if not self.dict_donnees["mode_condense"]:
                texte_allergies += "<br/><br/>"
            self.story.append(Tableau(titre="Allergies".upper(), aide="", contenu=[Paragraph(texte_allergies, style_defaut)]))

            #Dispositifs médicaux
            texte_dispmed = ", ".join([f"<b>{dispmed.nom}</b>" for dispmed in rattachement.individu.dispmed.all()])
            if rattachement.individu.dispmed_detail:
                texte_dispmed += f" : {rattachement.individu.dispmed_detail}"
            if not self.dict_donnees["mode_condense"]:
                texte_dispmed += "<br/><br/>"
            self.story.append(Tableau(titre="Dispositifs médicaux".upper(), aide="", contenu=[Paragraph(texte_dispmed, style_defaut)]))

            # Maladies
            texte_maladies = ", ".join([maladie.nom for maladie in rattachement.individu.maladies.all()])
            if not self.dict_donnees["mode_condense"]:
                texte_maladies += "<br/><br/>"
            self.story.append(Tableau(titre="Maladies déjà contractées".upper(), aide="", contenu=[Paragraph(texte_maladies, style_defaut)]))

            # Informations
            contenu_tableau = []
            for information in dict_informations.get(rattachement.individu_id, []):
                texte = "<b>%s</b>" % information.intitule
                if information.description:
                    texte += " : %s" % information.description
                contenu_tableau.append(Paragraph(texte, style_defaut))
            if not self.dict_donnees["mode_condense"]:
                contenu_tableau.append(Paragraph("<br/><br/><br/>", style_defaut))
            self.story.append(Tableau(titre="Informations et recommandations".upper(), aide="", contenu=contenu_tableau))

            # Vaccinations obligatoires
            liste_vaccinations_obligatoires = [vaccination for vaccination in dict_vaccinations.get(rattachement.individu, []) if vaccination["obligatoire"]]
            contenu_tableau = []
            ligne = []
            for index, vaccination in enumerate(liste_vaccinations_obligatoires):
                label_vaccin = vaccination["label"]
                label_vaccin = label_vaccin.replace("influenzae", "infl.")
                ligne.append(Paragraph("%s :" % label_vaccin, style_droite))
                ligne.append(Paragraph(utils_dates.ConvertDateToFR(vaccination["dernier_rappel"]) if vaccination["dernier_rappel"] else "__/__/____", style_defaut))
                if len(ligne) == 6 or index == len(liste_vaccinations_obligatoires)-1:
                    contenu_tableau.append(ligne)
                    ligne = []

            if contenu_tableau:
                tableau = Table(contenu_tableau, [largeur_contenu/6] * 6)
                tableau.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                ]))
            else:
                tableau = [Paragraph("Aucune vaccination obligatoire", style_defaut)]
            self.story.append(Tableau(titre="Vaccinations obligatoires".upper(), aide="Indiquer la date du dernier rappel pour chaque vaccin", contenu=[tableau]))

            # Autres vaccinations
            texte_vaccinations = []
            for index, vaccination in enumerate(dict_vaccinations.get(rattachement.individu, [])):
                if not vaccination["obligatoire"] and vaccination["valide"]:
                    texte_vaccinations.append("%s (%s)" % (vaccination["label"], utils_dates.ConvertDateToFR(vaccination["dernier_rappel"])))
            if not self.dict_donnees["mode_condense"]:
                texte_vaccinations.append("<br/><br/><br/>")
            self.story.append(Tableau(titre="Autres vaccinations".upper(), aide="Indiquer les autres vaccinations en précisant la date de rappel", contenu=[Paragraph(", ".join(texte_vaccinations), style_defaut)]))

            # Questionnaires
            questions_famille = questionnaires_familles.GetDonnees(rattachement.famille_id)
            if questions_famille:
                contenu_tableau = [Paragraph("%s : <b>%s</b>" % (question["label"], question["reponse"]), style_defaut) for question in questions_famille if question["visible_fiche_renseignement"]]
                self.story.append(Tableau(titre="Questionnaire familial".upper(), aide="", contenu=contenu_tableau))

            questions_individu = questionnaires_individus.GetDonnees(rattachement.individu_id)
            if questions_individu:
                contenu_tableau = [Paragraph("%s : <b>%s</b>" % (question["label"], question["reponse"]), style_defaut) for question in questions_individu if question["visible_fiche_renseignement"]]
                self.story.append(Tableau(titre="Questionnaire individuel".upper(), aide="", contenu=contenu_tableau))

            # Certification
            if rattachement.certification_date:
                texte_certification = "Fiche vérifiée par le responsable le %s" % utils_dates.ConvertDateToFR(rattachement.certification_date)
            else:
                texte_certification = "Fiche non vérifiée sur le portail"
            self.story.append(Tableau(titre="Certification en ligne".upper(), aide="", contenu=[Paragraph(texte_certification, style_defaut)],))

            # Saut de page
            self.story.append(PageBreak())
