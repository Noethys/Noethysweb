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
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import Activite, Lien, Rattachement, ContactUrgence, Information, Vaccin, Assurance, Organisateur, Scolarite
from core.data.data_liens import DICT_TYPES_LIENS
from core.data import data_civilites
from core.utils import utils_dates, utils_impression
from individus.utils import utils_vaccinations


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
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
        rattachements = Rattachement.objects.select_related("individu", "famille", "individu__medecin").filter(conditions).distinct().order_by("individu__nom", "individu__prenom")
        if not rattachements:
            self.erreurs.append("Aucun individu n'a été trouvé avec les paramètres donnés")

        # Importation de tous les représentants
        dict_representants = {}
        for rattachement in Rattachement.objects.select_related("individu").filter(categorie=1):
            dict_representants.setdefault(rattachement.famille_id, [])
            dict_representants[rattachement.famille_id].append(rattachement)

        # Importation de tous les liens
        dict_liens = {}
        for lien in Lien.objects.all():
            dict_liens[(lien.individu_sujet_id, lien.individu_objet_id)] = lien

        # Importation de toutes les assurances
        dict_assurances = {}
        for assurance in Assurance.objects.select_related("assureur").filter(Q(date_debut__lte=datetime.date.today()) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))).order_by("date_debut"):
            dict_assurances[(assurance.individu_id, assurance.famille_id)] = assurance

        # Importation de toutes les scolarités
        dict_scolarites = {}
        for scolarite in Scolarite.objects.select_related("ecole", "classe", "niveau").filter(date_fin__gte=datetime.date.today()).order_by("date_debut"):
            dict_scolarites[scolarite.individu_id] = scolarite

        # Importation de tous les contacts
        dict_contacts = {}
        for contact in ContactUrgence.objects.all().order_by("nom", "prenom"):
            key = (contact.individu_id, contact.famille_id)
            dict_contacts.setdefault(key, [])
            dict_contacts[key].append(contact)

        # Importation de toutes les informations
        dict_informations = {}
        for information in Information.objects.all().order_by("intitule"):
            dict_informations.setdefault(information.individu_id, [])
            dict_informations[information.individu_id].append(information)

        # Importation des vaccinations
        dict_vaccinations = utils_vaccinations.Get_tous_vaccins()

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

        # Remplissage du tableau
        for rattachement in rattachements:

            # Importation de l'organisateur
            organisateur = cache.get('organisateur', None)
            if not organisateur:
                organisateur = cache.get_or_set('organisateur', Organisateur.objects.filter(pk=1).first())

            # Importation de la photo de l'individu
            nom_fichier = rattachement.individu.Get_photo(forTemplate=False)
            if "media/" in nom_fichier:
                nom_fichier = settings.MEDIA_ROOT + nom_fichier.replace("media/", "")
            try:
                photo_individu = Image(nom_fichier, width=64, height=64)
            except:
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
                texte_scolarite = "Classe %s-%s : %s (%s - %s)." % (scolarite.date_debut.strftime("%Y"), scolarite.date_fin.strftime("%Y"), scolarite.niveau.abrege or "", scolarite.classe.nom or "", scolarite.ecole.nom or "")
                detail_individu.append(Paragraph(texte_scolarite, style_defaut))

            # Cadre identité de l'individu
            dataTableau = [(photo_individu, detail_individu, "%s\nEdité le %s" % (organisateur.nom, utils_dates.ConvertDateToFR(str(datetime.date.today()))))]
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

            # Famille
            contenu_tableau = []
            detail = []
            if rattachement.individu.situation_familiale:
                detail.append("Situation parentale : %s" % rattachement.individu.get_situation_familiale_display())
            if rattachement.individu.type_garde:
                detail.append("Type de garde : %s" % rattachement.individu.get_type_garde_display())
            if rattachement.individu.info_garde:
                detail.append("<font color='red'>Info garde : %s</font>" % rattachement.individu.info_garde)
            contenu_tableau.append([Paragraph("<br/>".join(detail), style_defaut)])
            self.story.append(Tableau(titre="Famille".upper(), contenu=contenu_tableau))

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

                # Autorisations du contact
                autorisations = []
                if contact.autorisation_sortie: autorisations.append(Img("sortie.png"))
                if contact.autorisation_appel: autorisations.append(Img("appel.png"))
                texte = "".join(autorisations) + "&nbsp;"

                # Nom contact
                texte += "<b>%s</b>%s" % (contact.Get_nom(), " (%s)" % contact.lien if contact.lien else "")

                # Coordonnées du contact
                for label, code in [("Domi.", "tel_domicile"), ("Port.", "tel_mobile"), ("Pro.", "tel_travail"), ("Email", "mail")]:
                    if getattr(contact, code):
                        texte += "&nbsp;&nbsp; %s : %s" % (label, getattr(contact, code))

                contenu_tableau.append(Paragraph(texte, style_defaut))

            self.story.append(Tableau(titre="Contacts".upper(), aide="Lister les noms des contacts d'urgence et leurs coordonnées", contenu=contenu_tableau))

            # Assurance
            assurance = dict_assurances.get((rattachement.individu_id, rattachement.famille_id), None)
            if assurance:
                texte_assurance = "%s - Contrat n°%s valable du %s au %s" % (assurance.assureur.nom, assurance.num_contrat, utils_dates.ConvertDateToFR(assurance.date_debut), utils_dates.ConvertDateToFR(assurance.date_fin) or "----")
            else:
                texte_assurance = ""
            self.story.append(Tableau(titre="Assurance".upper(), aide="Préciser l'assureur et ses coordonnées puis le numéro et les dates de validité du contrat", contenu=[Paragraph(texte_assurance, style_defaut)]))

            # Médecin
            if rattachement.individu.medecin:
                texte = "%s %s" % (rattachement.individu.medecin.nom, rattachement.individu.medecin.prenom or "")
                if rattachement.individu.medecin.tel_cabinet:
                    texte += "&nbsp;&nbsp; Tél : %s" % rattachement.individu.medecin.tel_cabinet
                texte_medecin = texte
            else:
                texte_medecin = ""
            self.story.append(Tableau(titre="Médecin traitant".upper(), aide="Renseigner le nom et les coordonnées du médecin traitant", contenu=[Paragraph(texte_medecin, style_defaut)]))

            # Régimes alimentaires
            texte_regimes = ", ".join([regime.nom for regime in rattachement.individu.regimes_alimentaires.all()])
            self.story.append(Tableau(titre="Régimes alimentaires".upper(), aide="Lister les régimes alimentaires", contenu=[Paragraph(texte_regimes, style_defaut)]))

            # Maladies
            texte_maladies = ", ".join([maladie.nom for maladie in rattachement.individu.maladies.all()])
            self.story.append(Tableau(titre="Maladies contractées".upper(), aide="Lister les maladies contractées", contenu=[Paragraph(texte_maladies, style_defaut)]))

            # Informations
            contenu_tableau = []
            for information in dict_informations.get(rattachement.individu_id, []):
                texte = "<b>%s</b> : %s" % (information.intitule, information.description or "")
                contenu_tableau.append(Paragraph(texte, style_defaut))
            self.story.append(Tableau(titre="Informations et recommandations".upper(), aide="Préciser les informations particulères et recommandations", contenu=contenu_tableau))

            # Vaccinations obligatoires
            liste_vaccinations_obligatoires = [vaccination for vaccination in dict_vaccinations.get(rattachement.individu, []) if vaccination["obligatoire"]]
            contenu_tableau = []
            ligne = []
            for index, vaccination in enumerate(liste_vaccinations_obligatoires):
                ligne.append(Paragraph("%s :" % vaccination["label"], style_droite))
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
            self.story.append(Tableau(titre="Autres vaccinations".upper(), aide="Indiquer les autres vaccinations en précisant la date de rappel", contenu=[Paragraph(", ".join(texte_vaccinations), style_defaut)]))

            # Certification
            if rattachement.certification_date:
                texte_certification = "Fiche certifiée sur le portail le %s" % utils_dates.ConvertDateToFR(rattachement.certification_date)
            else:
                texte_certification = "Fiche non certifiée sur le portail"
            self.story.append(Tableau(titre="Certification en ligne".upper(), aide="", contenu=[Paragraph(texte_certification, style_defaut)], bord_bas=not self.dict_donnees["afficher_signature"]))

            # Signature
            if self.dict_donnees["afficher_signature"]:
                texte_signature = [
                    Paragraph("Je soussigné _______________________________________________ déclare exacts les renseignements portés sur cette fiche.", style_defaut),
                    Paragraph("<br/>Date : __/__/____  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  Signature :<br/><br/><br/>", style_centre),
                ]
                self.story.append(Tableau(titre="Signature".upper(), aide="", contenu=texte_signature, bord_bas=True))

            # Saut de page
            self.story.append(PageBreak())
