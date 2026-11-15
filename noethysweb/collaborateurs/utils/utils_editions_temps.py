# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Editions des congés et du temps de travail : attestations de congés, bons de demande d'absence, relevés mensuels d'heures """

import datetime
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle, Spacer, PageBreak, KeepTogether
from reportlab.platypus.flowables import HRFlowable
from core.models import DroitCongeCollaborateur, DemandeAbsenceCollaborateur, TypeEvenementCollaborateur, Ferie
from core.utils import utils_dates
from collaborateurs.forms.planning_absences import Lire_mois
from collaborateurs.utils import utils_conges, utils_planning, utils_absences, utils_paie
from collaborateurs.utils.utils_affectations import Arbre
from collaborateurs.utils.utils_editions import Impression_edition, Get_contrats, Get_situation, Style, P, PM, E, Date, Duree, Style_tableau, Titre_section, Zone_signatures, \
    Texte_periode_contrat, COULEUR_TEXTE_CLAIR, COULEUR_PRINCIPALE, COULEUR_ENTETE, JOURS, MOIS


def Bloc_collaborateur(collaborateur=None, contrat=None, largeur=0, details=[]):
    """ Cadre d'identification du collaborateur """
    gauche = [P(collaborateur.Get_nom(), Style("bloc_nom", 12, gras=True, interligne=15))]
    if contrat:
        gauche.append(P("%s%s" % (contrat.type_poste.nom, " - %s" % contrat.type_contrat.nom if contrat.type_contrat else ""), Style("bloc_poste", 8.5, couleur=COULEUR_PRINCIPALE)))
        gauche.append(P("Contrat %s%s" % (Texte_periode_contrat(contrat), " - %s h par semaine" % ("%g" % float(contrat.heures_hebdo)).replace(".", ",") if contrat.heures_hebdo else ""),
                        Style("bloc_contrat", 8, couleur=COULEUR_TEXTE_CLAIR)))
    droite = [P(texte, Style("bloc_detail", 8.5, alignement="droite")) for texte in details]
    tableau = Table([[gauche, droite]], [largeur * 0.6, largeur * 0.4])
    tableau.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D1DA")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return tableau


# ------------------------------------------------- Attestations de congés -------------------------------------------------

class Impression_attestations_conges(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        collaborateurs = self.dict_donnees["collaborateurs"]
        date_reference = parametres["date"]
        types = list(parametres["types"])
        contrats = Get_contrats(collaborateurs)
        compteurs = utils_conges.Get_compteurs(collaborateurs=[collaborateur.pk for collaborateur in collaborateurs], types=types, date_reference=date_reference)
        largeur = self.largeur_utile
        style = Style("conges", 8.5)
        style_droite = Style("conges_d", 8.5, alignement="droite")
        style_gras_droite = Style("conges_gd", 8.5, gras=True, alignement="droite")

        for index, collaborateur in enumerate(collaborateurs):
            if index:
                self.story.append(PageBreak())
            self.Entete("Relevé de congés", "Situation au %s" % Date(date_reference))
            self.story.append(Bloc_collaborateur(collaborateur, Get_situation(contrats.get(collaborateur.pk, []), date_reference), largeur,
                                                 details=["Edité le %s" % Date(datetime.date.today())]))
            self.story.append(Spacer(0, 6 * mm))

            # Compteurs
            donnees = [[P(texte, Style("conges_e", 8.5, gras=True, alignement="droite" if num else None)) for num, texte in
                        enumerate(("Type de congé", "Période de référence", "Droits", "Pris", "En attente", "Solde", "Solde prévisionnel"))]]
            for type_conge in types:
                compteur = compteurs.get((collaborateur.pk, type_conge.pk))
                if not compteur or not (compteur["droits"] or compteur["poses"] or compteur["attente"]):
                    continue
                periode = utils_conges.Periode(type_conge, compteur["annee"])
                donnees.append([P(type_conge.nom, Style("conges_type", 8.5, gras=True)), P("du %s au %s" % (Date(periode["debut"]), Date(periode["fin"])), style_droite),
                                P(compteur["droits_txt"], style_droite), P(compteur["poses_txt"], style_droite), P(compteur["attente_txt"] if compteur["attente"] else "-", style_droite),
                                P(compteur["solde_txt"], style_gras_droite), P(compteur["previsionnel_txt"], style_droite)])
            if len(donnees) == 1:
                donnees.append([P("Aucun droit ni absence sur les périodes en cours", style), "", "", "", "", "", ""])
            tableau = Table(donnees, [largeur * part for part in (0.2, 0.24, 0.1, 0.1, 0.11, 0.1, 0.15)], repeatRows=1)
            tableau.setStyle(Style_tableau(nbre_lignes=len(donnees), taille=8.5, padding=4))
            self.story.append(KeepTogether([Titre_section("Compteurs", largeur), Spacer(0, 2 * mm), tableau]))
            self.story.append(Spacer(0, 6 * mm))

            if parametres.get("afficher_detail"):
                for type_conge in types:
                    compteur = compteurs.get((collaborateur.pk, type_conge.pk))
                    if not compteur:
                        continue
                    periode = utils_conges.Periode(type_conge, compteur["annee"])
                    lignes = [["Date", "Mouvement", "Détail", "Valeur"]]
                    for droit in DroitCongeCollaborateur.objects.filter(collaborateur=collaborateur, type_conge=type_conge, annee=compteur["annee"]).order_by("date_saisie"):
                        lignes.append([Date(droit.date_saisie.date()), droit.get_nature_display(), P(droit.motif or "", style),
                                       ("+" if droit.valeur > 0 else "") + utils_conges.Format_valeur(droit.valeur, type_conge.unite)])
                    for demande in DemandeAbsenceCollaborateur.objects.filter(collaborateur=collaborateur, type_conge=type_conge, etat__in=("VALIDEE", "ATTENTE"),
                                                                              date_debut__gte=periode["debut"], date_debut__lte=periode["fin"]).order_by("date_debut"):
                        lignes.append([Date(demande.date_debut), "Absence %s" % ("validée" if demande.etat == "VALIDEE" else "en attente"),
                                       P(utils_conges.Texte_periode_demande(demande).capitalize(), style), "-" + utils_conges.Format_valeur(demande.quantite, type_conge.unite)])
                    if len(lignes) == 1:
                        continue
                    tableau = Table(lignes, [largeur * part for part in (0.14, 0.22, 0.49, 0.15)], repeatRows=1)
                    style_tableau = Style_tableau(nbre_lignes=len(lignes), taille=8)
                    style_tableau.add("ALIGN", (3, 0), (3, -1), "RIGHT")
                    tableau.setStyle(style_tableau)
                    self.story.append(KeepTogether([P("%s - période %s" % (type_conge.nom, periode["libelle"]), Style("conges_titre", 9.5, gras=True)), Spacer(0, 1.5 * mm), tableau]))
                    self.story.append(Spacer(0, 5 * mm))
                self.story.append(P("Les jours pris comprennent les absences validées et celles saisies directement dans le planning. Les droits et les soldes sont exprimés dans l'unité de chaque type de congé.",
                                    Style("conges_mention", 7.5, couleur=COULEUR_TEXTE_CLAIR)))

            if parametres.get("afficher_signature"):
                self.story.append(Spacer(0, 8 * mm))
                self.story.append(KeepTogether([Zone_signatures(["Le collaborateur", "Le responsable"], largeur)]))


# ------------------------------------------------- Bons de demande d'absence -------------------------------------------------

class Impression_demandes(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        demandes = self.dict_donnees["demandes"]
        largeur = self.largeur_utile
        contrats = Get_contrats([demande.collaborateur for demande in demandes])
        deux_par_page = parametres.get("deux_par_page")
        style_label = Style("dem_label", 8.5, couleur=COULEUR_TEXTE_CLAIR)
        style_valeur = Style("dem_valeur", 9.5)
        style_valeur_gras = Style("dem_valeur_g", 9.5, gras=True)

        for index, demande in enumerate(demandes):
            if index:
                if deux_par_page and index % 2 == 1:
                    self.story.append(Spacer(0, 7 * mm))
                    self.story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ADB5BD"), dash=(3, 3)))
                    self.story.append(Spacer(0, 7 * mm))
                else:
                    self.story.append(PageBreak())
            elements = []
            type_conge = demande.type_conge
            contrat = Get_situation(contrats.get(demande.collaborateur_id, []), demande.date_debut)
            titre = Table([[P("Demande d'absence", Style("dem_titre", 14, gras=True)), P("N° %d" % demande.pk, Style("dem_num", 9, couleur=COULEUR_TEXTE_CLAIR, alignement="droite"))]],
                          [largeur * 0.7, largeur * 0.3])
            titre.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 1.2, COULEUR_PRINCIPALE), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
            elements += [titre, Spacer(0, 4 * mm)]
            elements.append(Bloc_collaborateur(demande.collaborateur, contrat, largeur, details=["Demande du %s" % demande.date_demande.strftime("%d/%m/%Y"),
                                                                                                   "Saisie par %s" % demande.auteur.get_full_name() if demande.auteur and demande.auteur.get_full_name() else ""]))
            elements.append(Spacer(0, 4 * mm))

            valeurs = [("Type d'absence", P(type_conge.nom, style_valeur_gras)), ("Période", P(utils_conges.Texte_periode_demande(demande).capitalize(), style_valeur_gras)),
                       ("Durée décomptée", P(utils_conges.Format_valeur(demande.quantite, type_conge.unite), style_valeur))]
            if demande.motif:
                valeurs.append(("Motif", P(demande.motif, style_valeur)))
            if parametres.get("afficher_solde"):
                compteur = utils_conges.Get_compteurs(collaborateurs=[demande.collaborateur_id], types=[type_conge], date_reference=demande.date_debut).get((demande.collaborateur_id, type_conge.pk))
                if compteur:
                    valeurs.append(("Compteur %s" % compteur["periode"], P("Droits %s - pris %s - en attente %s - solde %s" % (
                        compteur["droits_txt"], compteur["poses_txt"], compteur["attente_txt"], compteur["solde_txt"]), style_valeur)))
            tableau = Table([[P(label, style_label), valeur] for label, valeur in valeurs], [38 * mm, largeur - 38 * mm])
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#EDF0F3")),
                                         ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
            elements += [tableau, Spacer(0, 4 * mm)]

            # Décision
            couleurs = {"ATTENTE": colors.HexColor("#FFF4DB"), "VALIDEE": colors.HexColor("#E6F4EA"), "REFUSEE": colors.HexColor("#FDECEE"), "ANNULEE": colors.HexColor("#F1F3F5")}
            if demande.etat == "ATTENTE":
                decision = [PM("Décision : <b>en attente</b>", Style("dem_decision", 9.5)), Spacer(0, 2 * mm),
                            PM("[&nbsp;&nbsp;&nbsp;] Accordée &nbsp;&nbsp;&nbsp;&nbsp; [&nbsp;&nbsp;&nbsp;] Refusée &nbsp;&nbsp;&nbsp;&nbsp; Commentaire : ......................................................................", Style("dem_choix", 9))]
            else:
                texte = "Décision : <b>%s</b>" % E(demande.get_etat_display().lower())
                if demande.date_decision:
                    texte += " le %s" % demande.date_decision.strftime("%d/%m/%Y")
                if demande.decideur and demande.decideur.get_full_name():
                    texte += " par %s" % E(demande.decideur.get_full_name())
                decision = [PM(texte, Style("dem_decision", 9.5))]
                if demande.commentaire:
                    decision.append(P("Commentaire : %s" % demande.commentaire, Style("dem_commentaire", 9)))
            cadre = Table([[decision]], [largeur])
            cadre.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), couleurs.get(demande.etat)), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D1DA")),
                                       ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
            elements += [cadre, Spacer(0, 5 * mm), Zone_signatures(["Signature du collaborateur", "Signature du responsable"], largeur, hauteur=18 * mm)]
            self.story.append(KeepTogether(elements))


# ------------------------------------------------- Relevés mensuels d'heures -------------------------------------------------

class Impression_releves(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        collaborateurs = self.dict_donnees["collaborateurs"]
        mois = Lire_mois(parametres["mois"])
        date_debut, date_fin = utils_paie.Limites_mois(mois)
        dates = [date_debut + datetime.timedelta(days=n) for n in range((date_fin - date_debut).days + 1)]
        realise = parametres["donnees"] == "REALISE"
        categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
        categories_absence = utils_absences.Get_categories_absence()
        arbre = Arbre() if parametres.get("afficher_affectations") else None
        liste_feries = list(Ferie.objects.all())
        contrats = Get_contrats(collaborateurs)
        largeur = self.largeur_utile
        titre_mois = "%s %d" % (MOIS[mois.month - 1], mois.year)
        evenements = {}
        for evenement in utils_planning.Get_evenements(date_debut, date_fin, [collaborateur.pk for collaborateur in collaborateurs]):
            if date_debut <= evenement.date_debut.date() <= date_fin:
                evenements.setdefault((evenement.collaborateur_id, evenement.date_debut.date()), []).append(evenement)

        taille = 7.2
        style = Style("rel", taille)
        style_droite = Style("rel_d", taille, alignement="droite")
        style_gras_droite = Style("rel_gd", taille, gras=True, alignement="droite")
        parts = (0.1, 0.24, 0.28, 0.095, 0.095, 0.095, 0.095)
        largeurs = [largeur * part for part in parts]

        for index, collaborateur in enumerate(collaborateurs):
            if index:
                self.story.append(PageBreak())
            liste_contrats = contrats.get(collaborateur.pk, [])
            self.Entete("Relevé mensuel d'heures", "%s - heures retenues : %s" % (titre_mois.capitalize(), "réalisé si saisi, sinon planifié" if realise else "planifié"), espace_apres=4 * mm)
            self.story.append(Bloc_collaborateur(collaborateur, Get_situation(liste_contrats, date_fin), largeur))
            self.story.append(Spacer(0, 3 * mm))

            entetes = ["Date", "Horaires", "Catégorie%s" % (" / affectation" if arbre else ""), "Planifié", "Réalisé", "Retenu", "Absence"]
            donnees = [[P(texte, Style("rel_e", taille, gras=True, alignement="droite" if num >= 3 else None)) for num, texte in enumerate(entetes)]]
            regles = []
            total = {"planifie": 0, "realise": 0, "retenu": 0, "absence": 0}
            semaine = {"planifie": 0, "realise": 0, "retenu": 0, "absence": 0}

            def Ligne_semaine(dernier_jour):
                lundi = dernier_jour - datetime.timedelta(days=dernier_jour.weekday())
                donnees.append([P("Semaine du %s" % lundi.strftime("%d/%m"), Style("rel_s", taille, gras=True)), "", "",
                                P(Duree(semaine["planifie"]), style_gras_droite), P(Duree(semaine["realise"]), style_gras_droite),
                                P(Duree(semaine["retenu"]), style_gras_droite), P(Duree(semaine["absence"]), style_gras_droite)])
                regles.append(("BACKGROUND", (0, len(donnees) - 1), (-1, len(donnees) - 1), COULEUR_ENTETE))
                regles.append(("SPAN", (0, len(donnees) - 1), (2, len(donnees) - 1)))
                for cle in semaine:
                    semaine[cle] = 0

            for date in dates:
                liste = sorted(evenements.get((collaborateur.pk, date), []), key=lambda evenement: evenement.date_debut)
                ferie = utils_dates.EstFerie(date, liste_feries)
                if liste or parametres.get("afficher_jours_vides") or ferie:
                    horaires, libelles = [], []
                    valeurs = {"planifie": 0, "realise": 0, "retenu": 0, "absence": 0}
                    for evenement in liste:
                        categorie = categories.get(evenement.type_evenement_id)
                        if not categorie:
                            continue
                        # Horaires réalisés lorsqu'ils sont saisis et retenus, sinon planifiés
                        debut, fin = (evenement.realise_debut, evenement.realise_fin) if realise and evenement.realise_debut and evenement.realise_fin else (evenement.date_debut, evenement.date_fin)
                        horaires.append("%s-%s" % (debut.strftime("%H:%M"), fin.strftime("%H:%M")))
                        libelle = categorie.nom
                        if arbre and evenement.affectation_id:
                            libelle += " / %s" % arbre.Get_chemin(evenement.affectation_id)
                        if evenement.titre:
                            libelle += " (%s)" % evenement.titre
                        if libelle not in libelles:
                            libelles.append(libelle)
                        duree_planifiee = (evenement.date_fin - evenement.date_debut).total_seconds() / 60
                        if categorie.type == "ADDITION":
                            valeurs["planifie"] += duree_planifiee
                            if evenement.realise_debut and evenement.realise_fin:
                                valeurs["realise"] += (evenement.realise_fin - evenement.realise_debut).total_seconds() / 60
                            valeurs["retenu"] += utils_paie.Duree_retenue(evenement, realise)[0]
                        elif categorie.pk in categories_absence:
                            valeurs["absence"] += duree_planifiee
                    if ferie:
                        libelles.insert(0, "Férié : %s" % ferie.nom)
                    donnees.append([P("%s %s" % (JOURS[date.weekday()][:3] + ".", date.strftime("%d/%m")), style), P(" / ".join(horaires), style), P("\n".join(libelles), style),
                                    P(Duree(valeurs["planifie"]), style_droite), P(Duree(valeurs["realise"]), style_droite), P(Duree(valeurs["retenu"]), style_droite),
                                    P(Duree(valeurs["absence"]), style_droite)])
                    if date.weekday() >= 5 or ferie:
                        regles.append(("TEXTCOLOR", (0, len(donnees) - 1), (0, len(donnees) - 1), COULEUR_TEXTE_CLAIR))
                    for cle in valeurs:
                        semaine[cle] += valeurs[cle]
                        total[cle] += valeurs[cle]
                if date.weekday() == 6 or date == date_fin:
                    if any(semaine.values()):
                        Ligne_semaine(date)
                    else:
                        for cle in semaine:
                            semaine[cle] = 0

            donnees.append([P("Total du mois", Style("rel_t", taille + 0.5, gras=True)), "", "", P(Duree(total["planifie"]), style_gras_droite),
                            P(Duree(total["realise"]), style_gras_droite), P(Duree(total["retenu"]), style_gras_droite), P(Duree(total["absence"]), style_gras_droite)])
            tableau = Table(donnees, largeurs, repeatRows=1)
            style_tableau = Style_tableau(nbre_lignes=0, taille=taille, padding=1.6)
            for regle in regles:
                style_tableau.add(*regle)
            style_tableau.add("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DDE3EA"))
            style_tableau.add("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#ADB5BD"))
            style_tableau.add("VALIGN", (0, 0), (-1, -1), "TOP")
            style_tableau.add("SPAN", (0, -1), (2, -1))
            tableau.setStyle(style_tableau)
            self.story.append(tableau)

            # Synthèse
            attendu = utils_planning.Heures_attendues(liste_contrats, dates, liste_feries)
            assimile = utils_paie.Minutes_assimilees([evenement for (idcollaborateur, date), liste in evenements.items() if idcollaborateur == collaborateur.pk for evenement in liste],
                                                     categories, liste_contrats)
            synthese = [("Heures travaillées retenues", Duree(total["retenu"], False)), ("Absences comptées comme du temps de travail", Duree(assimile, False)),
                        ("Heures attendues (contrat)", Duree(attendu, False))]
            if attendu:
                ecart = total["retenu"] + assimile - attendu
                synthese.append(("Ecart", ("+" if ecart > 0 else "") + Duree(ecart, False)))
            tableau = Table([[P(label, Style("syn_l", 8.5)), P(valeur, Style("syn_v", 8.5, gras=True, alignement="droite"))] for label, valeur in synthese], [70 * mm, 25 * mm], hAlign="RIGHT")
            tableau.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#EDF0F3")), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
            elements = [Spacer(0, 4 * mm), tableau]
            if parametres.get("afficher_signature"):
                elements += [Spacer(0, 6 * mm), P("Je certifie l'exactitude des heures figurant sur ce relevé.", Style("certif", 8.5)), Spacer(0, 2 * mm),
                             Zone_signatures(["Le collaborateur (date et signature)", "Le responsable (date et signature)"], largeur, hauteur=20 * mm)]
            self.story.append(KeepTogether(elements))
