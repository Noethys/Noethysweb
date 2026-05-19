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
from core.models import Lien, Rattachement, ContactUrgence, Information, Assurance, Organisateur, Scolarite
from core.data.data_liens import DICT_TYPES_LIENS
from core.data import data_civilites
from core.utils import utils_dates, utils_impression, utils_questionnaires, utils_polices
from individus.utils import utils_vaccinations


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        colonnes_export = [
            {"code": "IDrattachement", "titre": "IDrattachement"},
            {"code": "IDindividu", "titre": "IDindividu"},
            {"code": "IDfamille", "titre": "IDfamille"},
            {"code": "nom", "titre": "Nom"},
            {"code": "prenom", "titre": "Prénom"},
            {"code": "sexe", "titre": "Sexe"},
            {"code": "date_naiss", "titre": "Date de naissance", "format": "date"},
            {"code": "ville_naiss", "titre": "Ville de naissance"},
            {"code": "rue_resid", "titre": "Rue"},
            {"code": "cp_resid", "titre": "CP"},
            {"code": "ville_resid", "titre": "Ville"},
            {"code": "scolarite_niveau", "titre": "Niveau"},
            {"code": "scolarite_classe", "titre": "Classe"},
            {"code": "scolarite_ecole", "titre": "Ecole"},
            {"code": "situation_parentale", "titre": "Situation parentale"},
            {"code": "type_garde", "titre": "Type de garde"},
            {"code": "info_garde", "titre": "Info garde"},
            {"code": "representant_1_id", "titre": "Représentant 1 - ID"},
            {"code": "representant_1_nom", "titre": "Représentant 1 - Nom"},
            {"code": "representant_1_prenom", "titre": "Représentant 1 - Prénom"},
            {"code": "representant_1_sexe", "titre": "Représentant 1 - Sexe"},
            {"code": "representant_1_lien", "titre": "Représentant 1 - Lien"},
            {"code": "representant_1_tel_domi", "titre": "Représentant 1 - Tél domicile"},
            {"code": "representant_1_tel_mobile", "titre": "Représentant 1 - Tél portable"},
            {"code": "representant_1_tel_travail", "titre": "Représentant 1 - Tél pro"},
            {"code": "representant_1_mail", "titre": "Représentant 1 - Mail"},
            {"code": "representant_2_id", "titre": "Représentant 2 - ID"},
            {"code": "representant_2_nom", "titre": "Représentant 2 - Nom"},
            {"code": "representant_2_prenom", "titre": "Représentant 2 - Prénom"},
            {"code": "representant_2_sexe", "titre": "Représentant 2 - Sexe"},
            {"code": "representant_2_lien", "titre": "Représentant 2 - Lien"},
            {"code": "representant_2_tel_domi", "titre": "Représentant 2 - Tél domicile"},
            {"code": "representant_2_tel_mobile", "titre": "Représentant 2 - Tél portable"},
            {"code": "representant_2_tel_travail", "titre": "Représentant 2 - Tél pro"},
            {"code": "representant_2_mail", "titre": "Représentant 2 - Mail"},
            {"code": "representant_3_id", "titre": "Représentant 3 - ID"},
            {"code": "representant_3_nom", "titre": "Représentant 3 - Nom"},
            {"code": "representant_3_prenom", "titre": "Représentant 3 - Prénom"},
            {"code": "representant_3_sexe", "titre": "Représentant 3 - Sexe"},
            {"code": "representant_3_lien", "titre": "Représentant 3 - Lien"},
            {"code": "representant_3_tel_domi", "titre": "Représentant 3 - Tél domicile"},
            {"code": "representant_3_tel_mobile", "titre": "Représentant 3 - Tél portable"},
            {"code": "representant_3_tel_travail", "titre": "Représentant 3 - Tél pro"},
            {"code": "representant_3_mail", "titre": "Représentant 3 - Mail"},
            {"code": "contacts_famille", "titre": "Contacts de la famille"},
            {"code": "contacts_individu", "titre": "Contacts de l'individu"},
            {"code": "assurance", "titre": "Assurance"},
            {"code": "medecin", "titre": "Médecin"},
            {"code": "maladies", "titre": "Maladies"},
            {"code": "informations", "titre": "Informations"},
            {"code": "vaccinations_obligatoires", "titre": "Vaccinations obligatoires"},
            {"code": "autres_vaccinations", "titre": "Autres vaccinations"},
        ]
        self.export_xlsx["colonnes"] = colonnes_export

        # Importation des rattachements
        conditions = Q(pk__in=self.dict_donnees["rattachements"])
        rattachements = Rattachement.objects.select_related("individu", "famille", "individu__medecin").prefetch_related("individu__regimes_alimentaires", "individu__maladies").filter(conditions).distinct().order_by("individu__nom", "individu__prenom")
        if not rattachements:
            self.erreurs.append("Aucun individu n'a été trouvé avec les paramètres donnés")

        # Importation de tous les représentants
        dict_representants = {}
        for rattachement in Rattachement.objects.select_related("individu").filter(categorie=1):
            dict_representants.setdefault(rattachement.famille_id, [])
            dict_representants[rattachement.famille_id].append(rattachement)

        # Importation de tous les contacts famille
        dict_contacts_famille = {}
        for rattachement in Rattachement.objects.select_related("individu").filter(categorie=3):
            dict_contacts_famille.setdefault(rattachement.famille_id, [])
            dict_contacts_famille[rattachement.famille_id].append(rattachement)

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

        # Importation des questionnaires
        questionnaires_individus = utils_questionnaires.ChampsEtReponses(categorie="individu", filtre_reponses=Q(individu__in=[r.individu for r in rattachements]))
        questionnaires_familles = utils_questionnaires.ChampsEtReponses(categorie="famille", filtre_reponses=Q(famille__in=[r.famille for r in rattachements]))
        for module in (questionnaires_individus, questionnaires_familles):
            for dict_question in module.listeQuestions:
                self.export_xlsx["colonnes"].append({"code": "question_%s" % dict_question["IDquestion"], "titre": dict_question["label"]})

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName=utils_polices.FONT_NORMAL, fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName=utils_polices.FONT_NORMAL, alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_droite = ParagraphStyle(name="droite", fontName=utils_polices.FONT_NORMAL, alignment=2, fontSize=7, spaceAfter=0, leading=9)
        style_identite = ParagraphStyle(name="identite", fontName=utils_polices.FONT_BOLD, fontSize=16, spaceAfter=0, leading=28)

        def Img(fichier=""):
            return "<img src='%s/images/%s' width='6' height='6' valign='middle'/> " % (settings.STATIC_ROOT, fichier)

        def Tableau(titre="", aide="", contenu=[], bord_bas=False):
            dataTableau = [[titre, aide]]
            dataTableau.append([contenu, ""])
            tableau = Table(dataTableau, [largeur_contenu/2, largeur_contenu/2])
            style = [
                ('SPAN', (0, 1), (-1, 1)),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONT', (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7),
                ('LINEBEFORE', (0, 0), (0, -1), 0.25, colors.black),
                ('LINEAFTER', (-1, 0), (-1, -1), 0.25, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
                ('FONT', (0, 0), (0, 0), utils_polices.FONT_BOLD, 7),
                ('FONT', (1, 0), (1, 0), utils_polices.FONT_NORMAL, 6),
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

        # Tri des pages
        def tri_classe(rattachement):
            scolarite = dict_scolarites.get(rattachement.individu_id, None)
            return scolarite.classe.nom if scolarite and scolarite.classe else ""

        if self.dict_donnees["tri"] == "classe":
            rattachements = sorted(rattachements, key=tri_classe)

        # Remplissage du tableau
        for rattachement in rattachements:
            ligne_export = {}

            def Ajouter_lignes_export(liste_lignes=[]):
                for l in liste_lignes:
                    if type(l["valeur"]) == str:
                        for balise in ["<b>", "</b>", "<br/>", "&nbsp;"]:
                            l["valeur"] = l["valeur"].replace(balise, "")
                        l["valeur"] = l["valeur"].replace(Img("sortie.png"), "[SORTIE]")
                        l["valeur"] = l["valeur"].replace(Img("appel.png"), "[APPEL]")
                    ligne_export[l["code"]] = l["valeur"]

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

            Ajouter_lignes_export([
                {"code": "IDrattachement", "valeur": rattachement.pk},
                {"code": "IDindividu", "valeur": rattachement.individu_id},
                {"code": "IDfamille", "valeur": rattachement.famille_id},
                {"code": "nom", "valeur": rattachement.individu.nom},
                {"code": "prenom", "valeur": rattachement.individu.prenom},
                {"code": "sexe", "valeur": "F" if rattachement.individu.civilite in (2, 3, 5) else "M"},
            ])

            # Date de naissance
            if rattachement.individu.date_naiss:
                texte_date_naiss = "Né%s le %s" % ("e" if rattachement.individu.civilite in (2, 3, 5) else "", utils_dates.ConvertDateToFR(rattachement.individu.date_naiss))
                if rattachement.individu.ville_naiss:
                    texte_date_naiss += " à %s" % rattachement.individu.ville_naiss
                texte_date_naiss += ", %s ans." % rattachement.individu.Get_age()
                Ajouter_lignes_export([
                    {"code": "date_naiss", "valeur": utils_dates.ConvertDateToFR(rattachement.individu.date_naiss)},
                    {"code": "ville_naiss", "valeur": rattachement.individu.ville_naiss},
                ])
            else:
                texte_date_naiss = "Date de naissance inconnue."
            detail_individu.append(Paragraph(texte_date_naiss, style_defaut))

            # Adresse
            texte_adresse = rattachement.individu.Get_adresse_complete()
            for label, code in [("Domi.", "tel_domicile"), ("Port.", "tel_mobile"), ("Pro.", "travail_tel"), ("Email", "mail")]:
                if getattr(rattachement.individu, code):
                    texte_adresse += "&nbsp;&nbsp; %s : %s" % (label, getattr(rattachement.individu, code))
            detail_individu.append(Paragraph(texte_adresse, style_defaut))

            Ajouter_lignes_export([
                {"code": "rue_resid", "valeur": rattachement.individu.rue_resid},
                {"code": "cp_resid", "valeur": rattachement.individu.cp_resid},
                {"code": "ville_resid", "valeur": rattachement.individu.ville_resid},
            ])

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

                Ajouter_lignes_export([
                    {"code": "scolarite_niveau", "valeur": scolarite.niveau.abrege if scolarite.niveau else ""},
                    {"code": "scolarite_classe", "valeur": scolarite.classe.nom if scolarite.classe else ""},
                    {"code": "scolarite_ecole", "valeur": scolarite.ecole.nom if scolarite.ecole else ""},
                ])

            # Cadre identité de l'individu
            dataTableau = [(photo_individu, detail_individu, "%s\nEdité le %s" % (organisateur.nom, utils_dates.ConvertDateToFR(str(datetime.date.today()))))]
            style = TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ('FONT', (2, 0), (2, 0), utils_polices.FONT_NORMAL, 6),
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

            Ajouter_lignes_export([
                {"code": "situation_parentale", "valeur": rattachement.individu.get_situation_familiale_display()},
                {"code": "type_garde", "valeur": rattachement.individu.get_type_garde_display()},
                {"code": "info_garde", "valeur": rattachement.individu.info_garde},
            ])

            # Représentants
            contenu_tableau = []
            for index_representant, representant in enumerate(dict_representants.get(rattachement.famille_id), 1):

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

                Ajouter_lignes_export([
                    {"code": "representant_%d_id" % index_representant, "valeur": representant.individu.pk},
                    {"code": "representant_%d_nom" % index_representant, "valeur": representant.individu.nom},
                    {"code": "representant_%d_prenom" % index_representant, "valeur": representant.individu.prenom},
                    {"code": "representant_%d_sexe" % index_representant, "valeur": "F" if representant.individu.civilite in (2, 3, 5) else "M"},
                    {"code": "representant_%d_lien" % index_representant, "valeur": " ".join(texte_lien)},
                    {"code": "representant_%d_tel_domi" % index_representant, "valeur": representant.individu.tel_domicile},
                    {"code": "representant_%d_tel_mobile" % index_representant, "valeur": representant.individu.tel_mobile},
                    {"code": "representant_%d_tel_travail" % index_representant, "valeur": representant.individu.travail_tel},
                    {"code": "representant_%d_mail" % index_representant, "valeur": representant.individu.mail},
                ])

            self.story.append(Tableau(titre="Représentants".upper(), contenu=contenu_tableau))

            # Contacts de la famille
            contenu_tableau = []
            textes_temp = []
            for contact in dict_contacts_famille.get(rattachement.famille_id, []):

                # Lien du représentant avec l'individu
                texte_lien = []
                lien = dict_liens.get((contact.individu_id, rattachement.individu_id), None)
                dict_civilite = data_civilites.GetCiviliteForIndividu(individu=contact.individu)
                if lien and lien.idtype_lien and dict_civilite["sexe"]:
                    texte_lien.append(DICT_TYPES_LIENS[lien.idtype_lien][dict_civilite["sexe"]])

                # Nom représentant
                texte = "<b>%s</b> (%s)<br/>" % (contact.individu.Get_nom(), " ".join(texte_lien))

                # Coordonnées du contact
                texte += contact.individu.Get_adresse_complete()
                for label, code in [("Domi.", "tel_domicile"), ("Port.", "tel_mobile"), ("Pro.", "travail_tel"), ("Email", "mail")]:
                    if getattr(contact.individu, code):
                        texte += "&nbsp;&nbsp; %s : %s" % (label, getattr(contact.individu, code))

                contenu_tableau.append(Paragraph(texte, style_defaut))
                textes_temp.append(texte)

            if contenu_tableau:
                self.story.append(Tableau(titre="Contacts de la famille".upper(), contenu=contenu_tableau))

            Ajouter_lignes_export([{"code": "contacts_famille", "valeur": "|".join(textes_temp)}])

            # Contacts de l'individu
            contenu_tableau = []
            textes_temp = []
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
                textes_temp.append(texte)

            Ajouter_lignes_export([{"code": "contacts_individu", "valeur": "|".join(textes_temp)}])

            if not self.dict_donnees["mode_condense"]:
                contenu_tableau.append(Paragraph("<br/><br/><br/>", style_defaut))
            self.story.append(Tableau(titre="Contacts de l'individu".upper(), aide="Lister les noms des contacts d'urgence et leurs coordonnées", contenu=contenu_tableau))

            # Assurance
            assurance = dict_assurances.get((rattachement.individu_id, rattachement.famille_id), None)
            if assurance:
                texte_assurance = "%s - Contrat n°%s valable du %s au %s" % (assurance.assureur.nom, assurance.num_contrat, utils_dates.ConvertDateToFR(assurance.date_debut), utils_dates.ConvertDateToFR(assurance.date_fin) or "----")
            else:
                texte_assurance = ""
            if not self.dict_donnees["mode_condense"]:
                texte_assurance += "<br/><br/>"
            self.story.append(Tableau(titre="Assurance".upper(), aide="Préciser l'assureur et ses coordonnées puis le numéro et les dates de validité du contrat", contenu=[Paragraph(texte_assurance, style_defaut)]))
            Ajouter_lignes_export([{"code": "assurance", "valeur": texte_assurance}])

            # Médecin
            if rattachement.individu.medecin:
                texte = "%s %s" % (rattachement.individu.medecin.nom, rattachement.individu.medecin.prenom or "")
                if rattachement.individu.medecin.tel_cabinet:
                    texte += "&nbsp;&nbsp; Tél : %s" % rattachement.individu.medecin.tel_cabinet
                texte_medecin = texte
            else:
                texte_medecin = ""
            if not self.dict_donnees["mode_condense"]:
                texte_medecin += "<br/><br/>"
            self.story.append(Tableau(titre="Médecin traitant".upper(), aide="Renseigner le nom et les coordonnées du médecin traitant", contenu=[Paragraph(texte_medecin, style_defaut)]))
            Ajouter_lignes_export([{"code": "medecin", "valeur": texte_medecin}])

            # Régimes alimentaires
            texte_regimes = ", ".join([regime.nom for regime in rattachement.individu.regimes_alimentaires.all()])
            if not self.dict_donnees["mode_condense"]:
                texte_regimes += "<br/><br/>"
            self.story.append(Tableau(titre="Régimes alimentaires".upper(), aide="Lister les régimes alimentaires", contenu=[Paragraph(texte_regimes, style_defaut)]))
            Ajouter_lignes_export([{"code": "regimes_alimentaires", "valeur": texte_regimes}])

            # Maladies
            texte_maladies = ", ".join([maladie.nom for maladie in rattachement.individu.maladies.all()])
            if not self.dict_donnees["mode_condense"]:
                texte_maladies += "<br/><br/>"
            self.story.append(Tableau(titre="Maladies contractées".upper(), aide="Lister les maladies contractées", contenu=[Paragraph(texte_maladies, style_defaut)]))
            Ajouter_lignes_export([{"code": "maladies", "valeur": texte_maladies}])

            # Informations
            contenu_tableau = []
            textes_temp = []
            for information in dict_informations.get(rattachement.individu_id, []):
                texte = "<b>%s</b>" % information.intitule
                if information.description:
                    texte += " : %s" % information.description
                contenu_tableau.append(Paragraph(texte, style_defaut))
                textes_temp.append(texte)
            if not self.dict_donnees["mode_condense"]:
                contenu_tableau.append(Paragraph("<br/><br/><br/>", style_defaut))
            self.story.append(Tableau(titre="Informations et recommandations".upper(), aide="Préciser les informations particulières et recommandations", contenu=contenu_tableau))
            Ajouter_lignes_export([{"code": "informations", "valeur": "|".join(textes_temp)}])

            # Vaccinations obligatoires
            liste_vaccinations_obligatoires = [vaccination for vaccination in dict_vaccinations.get(rattachement.individu, []) if vaccination["obligatoire"]]
            contenu_tableau = []
            ligne = []
            textes_temp = []
            for index, vaccination in enumerate(liste_vaccinations_obligatoires):
                label_vaccin = vaccination["label"]
                label_vaccin = label_vaccin.replace("influenzae", "infl.")
                ligne.append(Paragraph("%s :" % label_vaccin, style_droite))
                ligne.append(Paragraph(utils_dates.ConvertDateToFR(vaccination["dernier_rappel"]) if vaccination["dernier_rappel"] else "__/__/____", style_defaut))
                if len(ligne) == 6 or index == len(liste_vaccinations_obligatoires)-1:
                    contenu_tableau.append(ligne)
                    ligne = []
                    textes_temp.append("%s : %s" % (label_vaccin, utils_dates.ConvertDateToFR(vaccination["dernier_rappel"]) if vaccination["dernier_rappel"] else "__/__/____"))

            if contenu_tableau:
                tableau = Table(contenu_tableau, [largeur_contenu/6] * 6)
                tableau.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONT', (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7),
                ]))
            else:
                tableau = [Paragraph("Aucune vaccination obligatoire", style_defaut)]
            self.story.append(Tableau(titre="Vaccinations obligatoires".upper(), aide="Indiquer la date du dernier rappel pour chaque vaccin", contenu=[tableau]))
            Ajouter_lignes_export([{"code": "vaccinations_obligatoires", "valeur": "|".join(textes_temp)}])

            # Autres vaccinations
            texte_vaccinations = []
            for index, vaccination in enumerate(dict_vaccinations.get(rattachement.individu, [])):
                if not vaccination["obligatoire"] and vaccination["valide"]:
                    texte_vaccinations.append("%s (%s)" % (vaccination["label"], utils_dates.ConvertDateToFR(vaccination["dernier_rappel"])))
            if not self.dict_donnees["mode_condense"]:
                texte_vaccinations.append("<br/><br/><br/>")
            self.story.append(Tableau(titre="Autres vaccinations".upper(), aide="Indiquer les autres vaccinations en précisant la date de rappel", contenu=[Paragraph(", ".join(texte_vaccinations), style_defaut)]))
            Ajouter_lignes_export([{"code": "autres_vaccinations", "valeur": "|".join(texte_vaccinations)}])

            # Questionnaires
            questions_famille = questionnaires_familles.GetDonnees(rattachement.famille_id)
            if questions_famille:
                contenu_tableau = [Paragraph("%s : <b>%s</b>" % (question["label"], question["reponse"]), style_defaut) for question in questions_famille if question["visible_fiche_renseignement"]]
                self.story.append(Tableau(titre="Questionnaire familial".upper(), aide="", contenu=contenu_tableau))
                for question in questions_famille:
                    Ajouter_lignes_export([{"code": "question_%d" % question["IDquestion"], "valeur": question["reponse"]}])

            questions_individu = questionnaires_individus.GetDonnees(rattachement.individu_id)
            if questions_individu:
                contenu_tableau = [Paragraph("%s : <b>%s</b>" % (question["label"], question["reponse"]), style_defaut) for question in questions_individu if question["visible_fiche_renseignement"]]
                self.story.append(Tableau(titre="Questionnaire individuel".upper(), aide="", contenu=contenu_tableau))
                for question in questions_individu:
                    Ajouter_lignes_export([{"code": "question_%d" % question["IDquestion"], "valeur": question["reponse"]}])

            # Certification
            if rattachement.certification_date:
                texte_certification = "Fiche certifiée sur le portail le %s" % utils_dates.ConvertDateToFR(rattachement.certification_date)
            else:
                texte_certification = "Fiche non certifiée sur le portail"
            self.story.append(Tableau(titre="Certification en ligne".upper(), aide="", contenu=[Paragraph(texte_certification, style_defaut)], bord_bas=not self.dict_donnees["afficher_signature"]))

            # Texte bonus
            if self.dict_donnees["bonus_texte"]:
                texte_bonus = [Paragraph("<para>%s</para>" % ligne, style_defaut) for ligne in self.dict_donnees["bonus_texte"].splitlines()]
                self.story.append(Tableau(titre=(self.dict_donnees["bonus_titre"] or "").upper(), aide="", contenu=texte_bonus, bord_bas=True))

            # Signature
            if self.dict_donnees["afficher_signature"]:
                texte_signature = [
                    Paragraph("Je soussigné _______________________________________________ déclare exacts les renseignements portés sur cette fiche.", style_defaut),
                    Paragraph("<br/>Date : __/__/____  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  Signature :<br/><br/><br/>", style_centre),
                ]
                self.story.append(Tableau(titre="Signature".upper(), aide="", contenu=texte_signature, bord_bas=True))

            # Saut de page
            self.story.append(PageBreak())

            # Export xlsx
            self.export_xlsx["lignes"].append(ligne_export)
