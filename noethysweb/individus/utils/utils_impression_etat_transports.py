# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.db.models import Q
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.barcode import code39
from core.models import Transport, Vacance, Rattachement, Scolarite, Consommation
from core.utils import utils_dates, utils_impression, utils_polices

BLEU = colors.HexColor("#3c8dbc")
GRIS = colors.HexColor("#f4f4f4")
ROSE = colors.HexColor("#ffe0e0")
VERT_CLAIR = colors.HexColor("#e2f5e9")


def Minutes(heure=None):
    """ Convertit un objet time (ou None) en minutes depuis minuit, pour un tri chronologique fiable.
    ATTENTION : ne jamais trier une heure sous forme de texte ("17h00" < "8h00" alphabétiquement) """
    if not heure:
        return 99999
    return heure.hour * 60 + heure.minute


class Impression(utils_impression.Impression):
    """ Etat récapitulatif des transports pour une date donnée : 40 variantes sélectionnables (dict_donnees["type_etat"]) """

    # -----------------------------------------------------------------
    # Récupération des transports concernés par la date et les critères
    # -----------------------------------------------------------------
    def Get_transports_ponctuels(self, date=None, categories=None):
        conditions = Q(mode="TRANSP") & Q(categorie__in=categories) & (Q(depart_date=date) | Q(arrivee_date=date))
        return list(Transport.objects.select_related(
            "individu", "compagnie", "ligne", "depart_arret", "depart_lieu", "arrivee_arret", "arrivee_lieu", "prog",
        ).prefetch_related("unites", "unites__activite").filter(conditions))

    def Get_transports_programmes(self, date=None, categories=None, uniquement_actifs=True):
        conditions = Q(mode="PROG") & Q(categorie__in=categories)
        if uniquement_actifs:
            conditions &= Q(actif=True)
        conditions &= Q(date_debut__isnull=True) | Q(date_debut__lte=date)
        conditions &= Q(date_fin__isnull=True) | Q(date_fin__gte=date)

        liste_vacances = Vacance.objects.all()
        est_vacances = utils_dates.EstEnVacances(date=date, liste_vacances=liste_vacances)
        jour_semaine = str(date.weekday())

        resultats = []
        candidats = Transport.objects.select_related(
            "individu", "compagnie", "ligne", "depart_arret", "depart_lieu", "arrivee_arret", "arrivee_lieu", "prog",
        ).prefetch_related("unites", "unites__activite").filter(conditions)
        for transport in candidats:
            jours = transport.jours_vacances if est_vacances else transport.jours_scolaires
            if jours and jour_semaine in jours:
                resultats.append(transport)
        return resultats

    # -----------------------------------------------------------------
    # Enrichissements transverses (calculés une seule fois pour tous les états)
    # -----------------------------------------------------------------
    def Precalculer_enrichissements(self, liste_transports=None, date=None):
        individu_ids = [t.individu_id for t in liste_transports if t.individu_id]

        # Famille (via le rattachement "enfant", categorie=2)
        self.dict_familles = {}
        for rattachement in Rattachement.objects.select_related("famille").filter(individu_id__in=individu_ids, categorie=2):
            self.dict_familles.setdefault(rattachement.individu_id, rattachement.famille.nom)

        # Ecole (scolarité en cours à la date)
        self.dict_ecoles = {}
        for scolarite in Scolarite.objects.select_related("ecole").filter(individu_id__in=individu_ids, date_debut__lte=date, date_fin__gte=date):
            self.dict_ecoles[scolarite.individu_id] = scolarite.ecole.nom

        # Age à la date de l'état
        self.dict_ages = {}
        for t in liste_transports:
            if t.individu and t.individu.date_naiss and t.individu_id not in self.dict_ages:
                self.dict_ages[t.individu_id] = t.individu.Get_age(today=date)

        # Présence prévue (Consommation) sur les activités liées aux unités du transport (si renseignées)
        activite_ids = set()
        for t in liste_transports:
            for unite in t.unites.all():
                activite_ids.add(unite.activite_id)
        self.dict_presences = {}
        if activite_ids:
            for conso in Consommation.objects.values("individu_id", "activite_id").filter(
                date=date, activite_id__in=activite_ids, etat__in=["reservation", "present"]
            ):
                self.dict_presences.setdefault(conso["individu_id"], set()).add(conso["activite_id"])

    # -----------------------------------------------------------------
    # Accesseurs pratiques sur un objet Transport
    # -----------------------------------------------------------------
    def Get_lieu(self, transport=None, sens="depart"):
        lieu = getattr(transport, "%s_lieu" % sens)
        arret = getattr(transport, "%s_arret" % sens)
        localisation = getattr(transport, "%s_localisation" % sens)
        if lieu:
            return lieu.nom
        if arret:
            return arret.nom
        if localisation:
            return localisation
        return ""

    def Get_transporteur(self, transport=None):
        liste = []
        if transport.compagnie:
            liste.append(transport.compagnie.nom)
        if transport.ligne:
            liste.append(transport.ligne.nom)
        if transport.numero:
            liste.append("N° %s" % transport.numero)
        if transport.details:
            liste.append(transport.details)
        return " - ".join(liste)

    def Get_ligne_ou_mode(self, transport=None):
        return transport.ligne.nom if transport.ligne else transport.get_categorie_display()

    def Get_activites(self, transport=None):
        return [unite.activite.nom for unite in transport.unites.all()]

    def Get_famille(self, transport=None):
        return self.dict_familles.get(transport.individu_id, "Famille inconnue")

    def Get_ecole(self, transport=None):
        return self.dict_ecoles.get(transport.individu_id, "Ecole inconnue")

    def Get_age(self, transport=None):
        return self.dict_ages.get(transport.individu_id)

    def Get_creneau(self, transport=None):
        m = Minutes(transport.depart_heure)
        if m < 12 * 60:
            return "Matin (avant 12h)"
        if m < 17 * 60:
            return "Après-midi (12h-17h)"
        return "Soir (après 17h)"

    def Get_duree(self, transport=None):
        if not transport.depart_heure or not transport.arrivee_heure:
            return None
        return Minutes(transport.arrivee_heure) - Minutes(transport.depart_heure)

    def Get_sens(self, transport=None):
        """ Estimation du sens : 'Retour' si le point de départ est le lieu/arrêt d'activité (le plus fréquent
        en destination des autres transports), sinon 'Aller'. A défaut d'un champ dédié dans le modèle,
        on se base sur l'heure : avant 12h = Aller, après 12h = Retour. Adaptez cette règle si besoin. """
        return "Aller" if Minutes(transport.depart_heure) < 12 * 60 else "Retour"

    def Cle_nom(self, transport=None):
        return (transport.individu.nom if transport.individu else "", transport.individu.prenom if transport.individu else "")

    # -----------------------------------------------------------------
    # Rendu générique d'un tableau nominatif
    # -----------------------------------------------------------------
    def Style_defaut(self):
        return ParagraphStyle("defaut", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10)

    def Style_entete(self):
        return ParagraphStyle("entete", fontName=utils_polices.FONT_BOLD, fontSize=6, leading=8, textColor=colors.white, alignment=1)

    def Style_groupe(self):
        return ParagraphStyle("groupe", fontName=utils_polices.FONT_BOLD, fontSize=10, spaceBefore=12, spaceAfter=4, leading=12)

    def Style_soustitre(self):
        return ParagraphStyle("soustitre", fontName=utils_polices.FONT_NORMAL, fontSize=8, spaceAfter=8, leading=10, textColor=colors.HexColor("#555555"))

    def Groupe_titre(self, texte=""):
        self.story.append(Paragraph(texte, self.Style_groupe()))

    def Table_nominative(self, lignes=None, entetes=None, largeurs=None, alerte_lignes=None, ok_lignes=None, hauteurs_lignes=None):
        alerte_lignes = alerte_lignes or set()
        ok_lignes = ok_lignes or set()
        style_defaut = self.Style_defaut()
        data = [[Paragraph(e, self.Style_entete()) for e in entetes]]
        for ligne in lignes:
            data.append([Paragraph(str(v) if v not in (None, "") else "-", style_defaut) for v in ligne])
        kwargs = {"repeatRows": 1}
        if hauteurs_lignes:
            kwargs["rowHeights"] = hauteurs_lignes
        tableau = Table(data, largeurs, **kwargs)
        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), BLEU),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ]
        for i in alerte_lignes:
            style.append(("BACKGROUND", (0, i + 1), (-1, i + 1), ROSE))
        for i in ok_lignes:
            style.append(("BACKGROUND", (0, i + 1), (-1, i + 1), VERT_CLAIR))
        tableau.setStyle(TableStyle(style))
        self.story.append(tableau)

    ENTETES_STD = ["Nom", "Prénom", "Ligne", "Compagnie", "Départ", "Origine", "Arrivée", "Destination", "Obs."]
    LARGEURS_STD = [55, 50, 65, 65, 35, 65, 35, 70, 80]

    def Ligne_std(self, t=None):
        return [
            t.individu.nom if t.individu else "", t.individu.prenom if t.individu else "",
            t.ligne.nom if t.ligne else "", t.compagnie.nom if t.compagnie else "",
            t.depart_heure.strftime("%Hh%M") if t.depart_heure else "", self.Get_lieu(t, "depart"),
            t.arrivee_heure.strftime("%Hh%M") if t.arrivee_heure else "", self.Get_lieu(t, "arrivee"),
            t.observations or "",
        ]

    # -----------------------------------------------------------------
    # Point d'entrée
    # -----------------------------------------------------------------
    def Draw(self):
        date = self.dict_donnees["date"]
        categories = self.dict_donnees["categories"]

        liste_transports = []
        if self.dict_donnees.get("inclure_ponctuels", True):
            liste_transports += self.Get_transports_ponctuels(date=date, categories=categories)
        if self.dict_donnees.get("inclure_programmes", True):
            liste_transports += self.Get_transports_programmes(date=date, categories=categories)

        self.liste_transports = liste_transports
        self.date = date
        self.Precalculer_enrichissements(liste_transports=liste_transports, date=date)

        # Entête standard
        self.Insert_header(detail="Date : %s" % utils_dates.ConvertDateToFR(date))

        if not liste_transports and self.dict_donnees["type_etat"] not in ("sans_transport",):
            self.story.append(Paragraph("Aucun transport trouvé pour cette date avec les critères sélectionnés.", self.Style_defaut()))
            return

        # Dispatch vers la méthode de l'état sélectionné
        code_etat = self.dict_donnees["type_etat"]
        nom_methode = "Etat_%s" % code_etat
        methode = getattr(self, nom_methode, None)
        if not methode:
            self.story.append(Paragraph("Type d'état inconnu : %s" % code_etat, self.Style_defaut()))
            return
        methode()

        # Pied de page commun
        self.story.append(Spacer(0, 10))
        self.story.append(Paragraph(
            "%d transport(s) au total pour le %s" % (len(liste_transports), utils_dates.ConvertDateToFR(date)),
            ParagraphStyle("infos", fontName=utils_polices.FONT_NORMAL, alignment=1, fontSize=8, spaceBefore=10),
        ))

    # ===================================================================
    # ETAT 1 - Par mode de transport
    # ===================================================================
    def Etat_par_mode(self):
        dict_groupes = {}
        for t in self.liste_transports:
            dict_groupes.setdefault(t.get_categorie_display(), []).append(t)
        for nom_groupe in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_groupe], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom_groupe, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 2 - Par ligne de transport
    # ===================================================================
    def Etat_par_ligne(self):
        dict_groupes = {}
        sans_ligne = []
        for t in self.liste_transports:
            if t.ligne:
                dict_groupes.setdefault(t.ligne.nom, []).append(t)
            else:
                sans_ligne.append(t)
        for nom_ligne in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_ligne], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom_ligne, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)
        if sans_ligne:
            self.Groupe_titre("Sans ligne renseignée (%d)" % len(sans_ligne))
            self.Table_nominative([self.Ligne_std(t) for t in sans_ligne], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 3 - Par arrêt (prise en charge)
    # ===================================================================
    def Etat_par_arret(self):
        dict_groupes = {}
        for t in self.liste_transports:
            nom_arret = self.Get_lieu(t, "depart") or "Non renseigné"
            dict_groupes.setdefault(nom_arret, []).append(t)
        for nom_arret in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_arret], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom_arret, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 4 - Par ligne puis par arrêt (tri chronologique CORRIGÉ)
    # ===================================================================
    def Etat_par_ligne_arret(self):
        lignes_dispo = sorted(set(t.ligne.nom for t in self.liste_transports if t.ligne))
        for nom_ligne in lignes_dispo:
            self.Groupe_titre(nom_ligne)
            transports_ligne = [t for t in self.liste_transports if t.ligne and t.ligne.nom == nom_ligne]
            arrets = sorted(set(self.Get_lieu(t, "depart") for t in transports_ligne if self.Get_lieu(t, "depart")))
            for arret in arrets:
                sel = sorted([t for t in transports_ligne if self.Get_lieu(t, "depart") == arret], key=lambda t: Minutes(t.depart_heure))
                self.story.append(Paragraph("↳ %s (%d)" % (arret, len(sel)), self.Style_soustitre()))
                self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 5 - Par compagnie
    # ===================================================================
    def Etat_par_compagnie(self):
        dict_groupes = {}
        sans_compagnie = []
        for t in self.liste_transports:
            if t.compagnie:
                dict_groupes.setdefault(t.compagnie.nom, []).append(t)
            else:
                sans_compagnie.append(t)
        for nom in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)
        if sans_compagnie:
            self.Groupe_titre("Sans compagnie renseignée (%d)" % len(sans_compagnie))
            self.Table_nominative([self.Ligne_std(t) for t in sans_compagnie], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 6 - Par compagnie puis par ligne
    # ===================================================================
    def Etat_par_compagnie_ligne(self):
        compagnies = sorted(set(t.compagnie.nom for t in self.liste_transports if t.compagnie))
        for nom_compagnie in compagnies:
            self.Groupe_titre(nom_compagnie)
            transports_compagnie = [t for t in self.liste_transports if t.compagnie and t.compagnie.nom == nom_compagnie]
            lignes_dispo = sorted(set((t.ligne.nom if t.ligne else "(sans ligne)") for t in transports_compagnie))
            for nom_ligne in lignes_dispo:
                sel = sorted([t for t in transports_compagnie if (t.ligne.nom if t.ligne else "(sans ligne)") == nom_ligne], key=self.Cle_nom)
                self.story.append(Paragraph("↳ %s (%d)" % (nom_ligne, len(sel)), self.Style_soustitre()))
                self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 7 - Par activité concernée
    # ===================================================================
    def Etat_par_activite(self):
        dict_groupes = {}
        for t in self.liste_transports:
            activites = self.Get_activites(t) or ["Activité non renseignée"]
            for nom_activite in activites:
                dict_groupes.setdefault(nom_activite, []).append(t)
        for nom_activite in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_activite], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom_activite, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 8 - Par famille
    # ===================================================================
    def Etat_par_famille(self):
        dict_groupes = {}
        for t in self.liste_transports:
            dict_groupes.setdefault(self.Get_famille(t), []).append(t)
        for nom_famille in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_famille], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom_famille, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 9 - Par école
    # ===================================================================
    def Etat_par_ecole(self):
        dict_groupes = {}
        for t in self.liste_transports:
            dict_groupes.setdefault(self.Get_ecole(t), []).append(t)
        for nom_ecole in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_ecole], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom_ecole, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 10 - Chronologique (heure de départ) - tri CORRIGÉ
    # ===================================================================
    def Etat_chrono_depart(self):
        sel = sorted(self.liste_transports, key=lambda t: Minutes(t.depart_heure))
        self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 11 - Chronologique (heure d'arrivée) - tri CORRIGÉ
    # ===================================================================
    def Etat_chrono_arrivee(self):
        sel = sorted(self.liste_transports, key=lambda t: Minutes(t.arrivee_heure))
        self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 12 - Par sens (Aller / Retour)
    # ===================================================================
    def Etat_par_sens(self):
        for sens in ["Aller", "Retour"]:
            sel = sorted([t for t in self.liste_transports if self.Get_sens(t) == sens], key=lambda t: Minutes(t.depart_heure))
            self.Groupe_titre("%s (%d)" % (sens, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 13 - Ponctuels uniquement
    # ===================================================================
    def Etat_ponctuels(self):
        sel = sorted([t for t in self.liste_transports if t.mode == "TRANSP"], key=self.Cle_nom)
        self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 14 - Programmés uniquement
    # ===================================================================
    def Etat_programmes(self):
        sel = sorted([t for t in self.liste_transports if t.mode == "PROG"], key=self.Cle_nom)
        self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 15 - Avec observations (PAI, etc.)
    # ===================================================================
    def Etat_observations(self):
        sel = sorted([t for t in self.liste_transports if t.observations], key=self.Cle_nom)
        self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD, alerte_lignes=set(range(len(sel))))

    # ===================================================================
    # ETAT 16 - Anomalies (compagnie ou ligne manquante)
    # ===================================================================
    def Etat_anomalies_infos(self):
        sel = [t for t in self.liste_transports if not t.compagnie or (not t.ligne and t.categorie not in ("taxi", "voiture", "marche", "velo"))]
        if not sel:
            self.story.append(Paragraph("Aucune anomalie détectée (compagnie et ligne renseignées partout où c'est pertinent).", self.Style_defaut()))
            return
        self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD, alerte_lignes=set(range(len(sel))))

    # ===================================================================
    # ETAT 17 - Récapitulatif statistique
    # ===================================================================
    def Etat_statistique(self):
        def tableau_comptage(titre, valeurs):
            self.Groupe_titre(titre)
            dict_c = {}
            for v in valeurs:
                v = v or "Non renseigné"
                dict_c[v] = dict_c.get(v, 0) + 1
            data = [[Paragraph("Valeur", self.Style_entete()), Paragraph("Nombre", self.Style_entete())]]
            for v, n in sorted(dict_c.items(), key=lambda x: -x[1]):
                data.append([Paragraph(v, self.Style_defaut()), Paragraph(str(n), self.Style_defaut())])
            tableau = Table(data, [250, 150])
            tableau.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.black), ("BACKGROUND", (0, 0), (-1, 0), BLEU), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS])]))
            self.story.append(tableau)
            self.story.append(Spacer(0, 10))
        tableau_comptage("Par mode", [t.get_categorie_display() for t in self.liste_transports])
        tableau_comptage("Par ligne", [t.ligne.nom if t.ligne else None for t in self.liste_transports])
        tableau_comptage("Par compagnie", [t.compagnie.nom if t.compagnie else None for t in self.liste_transports])

    # ===================================================================
    # ETAT 18 - Étiquettes nominatives
    # ===================================================================
    def Etat_etiquettes(self):
        style_nom = ParagraphStyle("etiq_nom", fontName=utils_polices.FONT_BOLD, fontSize=11)
        style_det = ParagraphStyle("etiq_det", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10)
        data, ligne_courante = [], []
        for t in sorted(self.liste_transports, key=self.Cle_nom):
            contenu = Table([
                [Paragraph("%s %s" % (t.individu.prenom, t.individu.nom) if t.individu else "", style_nom)],
                [Paragraph("%s%s" % (self.Get_ligne_ou_mode(t), " — " + self.Get_lieu(t, "depart") if self.Get_lieu(t, "depart") else ""), style_det)],
                [Paragraph("Départ %s → Arrivée %s" % (
                    t.depart_heure.strftime("%Hh%M") if t.depart_heure else "?",
                    t.arrivee_heure.strftime("%Hh%M") if t.arrivee_heure else "?"), style_det)],
            ], colWidths=[240])
            contenu.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, BLEU), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
            ligne_courante.append(contenu)
            if len(ligne_courante) == 2:
                data.append(ligne_courante)
                ligne_courante = []
        if ligne_courante:
            data.append(ligne_courante + [""])
        tableau = Table(data, [250, 250])
        tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        self.story.append(tableau)

    # ===================================================================
    # ETAT 19 - Vue aller-retour consolidée
    # ===================================================================
    def Etat_aller_retour(self):
        par_enfant = {}
        for t in self.liste_transports:
            par_enfant.setdefault(self.Cle_nom(t), {})[self.Get_sens(t)] = t
        lignes = []
        for (nom, prenom), d in sorted(par_enfant.items()):
            aller, retour = d.get("Aller"), d.get("Retour")
            ref = aller or retour
            txt_aller = "%s à %s" % (self.Get_lieu(aller, "depart") or self.Get_ligne_ou_mode(aller), aller.depart_heure.strftime("%Hh%M")) if aller and aller.depart_heure else "-"
            txt_retour = "%s à %s" % (retour.depart_heure.strftime("%Hh%M"), self.Get_lieu(retour, "arrivee")) if retour and retour.depart_heure else "-"
            lignes.append([nom, prenom, self.Get_ligne_ou_mode(ref), txt_aller, txt_retour])
        self.Table_nominative(lignes, ["Nom", "Prénom", "Ligne", "Aller", "Retour"], [70, 65, 75, 130, 130])

    # ===================================================================
    # ETAT 20 - Feuille de route par transporteur
    # ===================================================================
    def Etat_par_transporteur(self):
        compagnies = sorted(set(t.compagnie for t in self.liste_transports if t.compagnie), key=lambda c: c.nom)
        for compagnie in compagnies:
            sel = sorted([t for t in self.liste_transports if t.compagnie_id == compagnie.pk], key=self.Cle_nom)
            coordonnees = " - ".join(filter(None, [compagnie.rue, compagnie.cp, compagnie.ville, ("Tél. %s" % compagnie.tel) if compagnie.tel else ""]))
            entete = Table([[Paragraph(compagnie.nom, ParagraphStyle("cp", fontName=utils_polices.FONT_BOLD, fontSize=11)),
                              Paragraph(coordonnees, ParagraphStyle("cd", fontName=utils_polices.FONT_NORMAL, fontSize=8, alignment=2))]], colWidths=[250, 250])
            entete.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, -1), GRIS),
                                         ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
            self.story.append(entete)
            self.story.append(Spacer(0, 4))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)
            self.story.append(Spacer(0, 10))

    # ===================================================================
    # ETAT 21 - Par lieu (gare, aéroport, port)
    # ===================================================================
    def Etat_par_lieu(self):
        dict_groupes = {}
        for t in self.liste_transports:
            nom_lieu = t.depart_lieu.nom if t.depart_lieu else (t.arrivee_lieu.nom if t.arrivee_lieu else None)
            if nom_lieu:
                dict_groupes.setdefault(nom_lieu, []).append(t)
        if not dict_groupes:
            self.story.append(Paragraph("Aucun transport de type gare/aéroport/port pour cette date.", self.Style_defaut()))
            return
        entetes = ["Nom", "Prénom", "Mode", "Compagnie", "N°", "Départ", "Arrivée", "Obs."]
        largeurs = [55, 50, 45, 70, 55, 40, 40, 95]
        for nom_lieu in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_lieu], key=lambda t: Minutes(t.depart_heure))
            self.Groupe_titre("%s (%d)" % (nom_lieu, len(sel)))
            lignes = [[t.individu.nom, t.individu.prenom, t.get_categorie_display(), t.compagnie.nom if t.compagnie else "",
                       t.numero or "", t.depart_heure.strftime("%Hh%M") if t.depart_heure else "", t.arrivee_heure.strftime("%Hh%M") if t.arrivee_heure else "", t.observations or ""] for t in sel]
            self.Table_nominative(lignes, entetes, largeurs)

    # ===================================================================
    # ETAT 22 - Par destination (arrivée)
    # ===================================================================
    def Etat_par_destination(self):
        dict_groupes = {}
        for t in self.liste_transports:
            nom_dest = self.Get_lieu(t, "arrivee") or "Non renseignée"
            dict_groupes.setdefault(nom_dest, []).append(t)
        for nom_dest in sorted(dict_groupes.keys()):
            sel = sorted(dict_groupes[nom_dest], key=self.Cle_nom)
            self.Groupe_titre("%s (%d)" % (nom_dest, len(sel)))
            self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 23 - Par créneau horaire
    # ===================================================================
    def Etat_par_creneau(self):
        for creneau in ["Matin (avant 12h)", "Après-midi (12h-17h)", "Soir (après 17h)"]:
            sel = sorted([t for t in self.liste_transports if self.Get_creneau(t) == creneau], key=lambda t: Minutes(t.depart_heure))
            if sel:
                self.Groupe_titre("%s (%d)" % (creneau, len(sel)))
                self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 24 - Par durée de trajet
    # ===================================================================
    def Etat_par_duree(self):
        def bucket(t):
            d = self.Get_duree(t)
            if d is None:
                return "Durée inconnue"
            if d < 15:
                return "Court (< 15 min)"
            if d <= 30:
                return "Moyen (15-30 min)"
            return "Long (> 30 min)"
        for b in ["Court (< 15 min)", "Moyen (15-30 min)", "Long (> 30 min)", "Durée inconnue"]:
            sel = sorted([t for t in self.liste_transports if bucket(t) == b], key=self.Cle_nom)
            if sel:
                self.Groupe_titre("%s (%d)" % (b, len(sel)))
                self.Table_nominative([self.Ligne_std(t) for t in sel], self.ENTETES_STD, self.LARGEURS_STD)

    # ===================================================================
    # ETAT 25 - Chronologique global avec repères Matin/Soir
    # ===================================================================
    def Etat_chrono_global(self):
        sel = sorted(self.liste_transports, key=lambda t: Minutes(t.depart_heure))
        entetes = ["Nom", "Prénom", "Sens", "Ligne", "Départ", "Arrivée"]
        largeurs = [70, 65, 55, 70, 45, 45]
        dernier_creneau, lignes_bloc = None, []
        for t in sel:
            creneau = self.Get_creneau(t)
            if creneau != dernier_creneau:
                if lignes_bloc:
                    self.Table_nominative(lignes_bloc, entetes, largeurs)
                    lignes_bloc = []
                self.Groupe_titre(creneau)
                dernier_creneau = creneau
            lignes_bloc.append([t.individu.nom, t.individu.prenom, self.Get_sens(t), self.Get_ligne_ou_mode(t),
                                 t.depart_heure.strftime("%Hh%M") if t.depart_heure else "", t.arrivee_heure.strftime("%Hh%M") if t.arrivee_heure else ""])
        if lignes_bloc:
            self.Table_nominative(lignes_bloc, entetes, largeurs)

    # ===================================================================
    # ETAT 26 - Traçabilité : ponctuels issus d'une programmation
    # ===================================================================
    def Etat_traca_prog(self):
        sel = sorted([t for t in self.liste_transports if t.mode == "TRANSP" and t.prog_id], key=self.Cle_nom)
        if not sel:
            self.story.append(Paragraph("Aucun transport ponctuel rattaché à une programmation d'origine pour cette date.", self.Style_defaut()))
            return
        lignes = [[t.individu.nom, t.individu.prenom, self.Get_ligne_ou_mode(t), t.depart_heure.strftime("%Hh%M") if t.depart_heure else "",
                   "Programmation #%d" % t.prog_id] for t in sel]
        self.Table_nominative(lignes, ["Nom", "Prénom", "Ligne", "Heure", "Programmation d'origine"], [65, 60, 65, 40, 220])

    # ===================================================================
    # ETAT 27 - Enfants inscrits (présence prévue) sans transport affecté
    # ===================================================================
    def Etat_sans_transport(self):
        self.story.append(Paragraph(
            "Comparaison entre les présences prévues (réservations/consommations) sur les activités liées aux transports "
            "sélectionnés, et les individus effectivement couverts par un transport ce jour-là.", self.Style_soustitre()))
        individus_transportes = set(t.individu_id for t in self.liste_transports if t.individu_id)
        individus_prevus = set()
        for individu_id, activites in self.dict_presences.items():
            individus_prevus.add(individu_id)
        manquants = individus_prevus - individus_transportes
        if not manquants:
            self.story.append(Paragraph("Aucun écart détecté : tous les individus présents prévus sur les activités concernées ont un transport ce jour.", self.Style_defaut()))
            return
        from core.models import Individu
        lignes = []
        for individu in Individu.objects.filter(pk__in=manquants):
            lignes.append([individu.nom, individu.prenom, "Présence prévue mais aucun transport trouvé"])
        self.Table_nominative(lignes, ["Nom", "Prénom", "Alerte"], [90, 90, 270], alerte_lignes=set(range(len(lignes))))

    # ===================================================================
    # ETAT 28 - Par numéro de transport
    # ===================================================================
    def Etat_par_numero(self):
        sel = sorted([t for t in self.liste_transports if t.numero], key=lambda t: t.numero)
        if not sel:
            self.story.append(Paragraph("Aucun numéro de transport (vol, rotation, n° de car...) renseigné pour cette date.", self.Style_defaut()))
            return
        lignes = [[t.numero, t.get_categorie_display(), t.compagnie.nom if t.compagnie else "", t.individu.nom, t.individu.prenom,
                   t.depart_heure.strftime("%Hh%M") if t.depart_heure else "", t.arrivee_heure.strftime("%Hh%M") if t.arrivee_heure else ""] for t in sel]
        self.Table_nominative(lignes, ["N°", "Mode", "Compagnie", "Nom", "Prénom", "Départ", "Arrivée"], [60, 45, 80, 60, 55, 45, 45])

    # ===================================================================
    # ETAT 29 - Justificatif jour scolaire / jour de vacances
    # ===================================================================
    def Etat_justif_jour(self):
        liste_vacances = Vacance.objects.all()
        est_vacances = utils_dates.EstEnVacances(date=self.date, liste_vacances=liste_vacances)
        type_jour = "Jour de vacances scolaires" if est_vacances else "Jour scolaire (hors vacances)"
        self.story.append(Paragraph("Jour retenu pour l'application des programmations : <b>%s</b>." % type_jour, self.Style_soustitre()))
        sel = [t for t in self.liste_transports if t.mode == "PROG"]
        jours_labels = {"0": "Lun", "1": "Mar", "2": "Mer", "3": "Jeu", "4": "Ven", "5": "Sam", "6": "Dim"}
        lignes = []
        for t in sel:
            jours = t.jours_vacances if est_vacances else t.jours_scolaires
            txt_jours = ", ".join(jours_labels.get(j, j) for j in sorted(jours or [])) or "-"
            lignes.append([t.individu.nom, t.individu.prenom, self.Get_ligne_ou_mode(t), type_jour, txt_jours])
        self.Table_nominative(lignes, ["Nom", "Prénom", "Ligne", "Type de jour appliqué", "Jours retenus"], [65, 60, 65, 120, 110])

    # ===================================================================
    # ETAT 30 - Multi-trajets par enfant
    # ===================================================================
    def Etat_multi_trajets(self):
        par_enfant = {}
        for t in sorted(self.liste_transports, key=lambda t: Minutes(t.depart_heure)):
            par_enfant.setdefault(self.Cle_nom(t), []).append(t)
        lignes = []
        for (nom, prenom), trajets in sorted(par_enfant.items()):
            txt = " puis ".join("%s (%s→%s)" % (
                self.Get_sens(t),
                t.depart_heure.strftime("%Hh%M") if t.depart_heure else "?",
                t.arrivee_heure.strftime("%Hh%M") if t.arrivee_heure else "?") for t in trajets)
            lignes.append([nom, prenom, len(trajets), txt])
        self.Table_nominative(lignes, ["Nom", "Prénom", "Nb trajets", "Détail des trajets du jour"], [65, 60, 55, 300])

    # ===================================================================
    # ETAT 31 - Transports concernant plusieurs activités
    # ===================================================================
    def Etat_multi_activites(self):
        sel = [t for t in self.liste_transports if len(self.Get_activites(t)) > 1]
        if not sel:
            self.story.append(Paragraph("Aucun transport n'est rattaché à plusieurs activités pour cette date.", self.Style_defaut()))
            return
        lignes = [[t.individu.nom, t.individu.prenom, ", ".join(self.Get_activites(t)), self.Get_ligne_ou_mode(t),
                   t.depart_heure.strftime("%Hh%M") if t.depart_heure else ""] for t in sel]
        self.Table_nominative(lignes, ["Nom", "Prénom", "Activités concernées", "Ligne", "Départ"], [65, 60, 180, 65, 40])

    # ===================================================================
    # ETAT 32 - Feuille d'émargement
    # ===================================================================
    def Etat_emargement(self):
        sel = sorted(self.liste_transports, key=self.Cle_nom)
        style_case = ParagraphStyle("case", fontName=utils_polices.FONT_NORMAL, fontSize=14, alignment=1)
        data = [[Paragraph(e, self.Style_entete()) for e in ["Nom", "Prénom", "Ligne / Arrêt", "Présent Aller", "Présent Retour"]]]
        for t in sel:
            data.append([
                Paragraph(t.individu.nom, self.Style_defaut()), Paragraph(t.individu.prenom, self.Style_defaut()),
                Paragraph("%s — %s" % (self.Get_ligne_ou_mode(t), self.Get_lieu(t, "depart") or "-"), self.Style_defaut()),
                Paragraph("☐", style_case), Paragraph("☐", style_case),
            ])
        tableau = Table(data, [70, 65, 150, 90, 90], rowHeights=[22] + [26] * len(sel))
        tableau.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("BACKGROUND", (0, 0), (-1, 0), BLEU), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        self.story.append(tableau)

    # ===================================================================
    # ETAT 33 - Par ligne, dans l'ordre réel des arrêts (TransportArret.ordre)
    # ===================================================================
    def Etat_ordre_arrets(self):
        lignes_dispo = sorted(set(t.ligne.nom for t in self.liste_transports if t.ligne))
        for nom_ligne in lignes_dispo:
            self.Groupe_titre(nom_ligne)
            sel = sorted(
                [t for t in self.liste_transports if t.ligne and t.ligne.nom == nom_ligne],
                key=lambda t: (t.depart_arret.ordre if t.depart_arret else 999, Minutes(t.depart_heure)),
            )
            lignes = [[t.depart_arret.ordre if t.depart_arret else "-", self.Get_lieu(t, "depart"), t.individu.nom, t.individu.prenom,
                       t.depart_heure.strftime("%Hh%M") if t.depart_heure else ""] for t in sel]
            self.Table_nominative(lignes, ["Ordre", "Arrêt", "Nom", "Prénom", "Heure"], [40, 90, 65, 60, 45])

    # ===================================================================
    # ETAT 34 - Tableau croisé Ligne × Créneau horaire
    # ===================================================================
    def Etat_pivot_ligne_creneau(self):
        creneaux = ["Matin (avant 12h)", "Après-midi (12h-17h)", "Soir (après 17h)"]
        toutes_lignes = sorted(set(self.Get_ligne_ou_mode(t) for t in self.liste_transports))
        data = [[Paragraph("Ligne / Mode", self.Style_entete())] + [Paragraph(c, self.Style_entete()) for c in creneaux] + [Paragraph("Total", self.Style_entete())]]
        for nom_ligne in toutes_lignes:
            compte, total = [], 0
            for creneau in creneaux:
                n = len([t for t in self.liste_transports if self.Get_ligne_ou_mode(t) == nom_ligne and self.Get_creneau(t) == creneau])
                compte.append(str(n) if n else "-")
                total += n
            data.append([Paragraph(nom_ligne, self.Style_defaut())] + [Paragraph(v, self.Style_defaut()) for v in compte] + [Paragraph(str(total), self.Style_defaut())])
        tableau = Table(data, [130, 110, 110, 110, 60])
        tableau.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.black), ("BACKGROUND", (0, 0), (-1, 0), BLEU), ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS])]))
        self.story.append(tableau)

    # ===================================================================
    # ETAT 35 - Format affichage public (grande police)
    # ===================================================================
    def Etat_affichage_public(self):
        sel = sorted(self.liste_transports, key=lambda t: Minutes(t.depart_heure))
        style_grand = ParagraphStyle("grand", fontName=utils_polices.FONT_NORMAL, fontSize=13, leading=17)
        style_entete_grand = ParagraphStyle("entete_grand", fontName=utils_polices.FONT_BOLD, fontSize=13, textColor=colors.white)
        data = [[Paragraph(e, style_entete_grand) for e in ["Prénom", "Ligne", "Heure"]]]
        for t in sel:
            data.append([Paragraph(t.individu.prenom, style_grand), Paragraph(self.Get_ligne_ou_mode(t), style_grand),
                         Paragraph(t.depart_heure.strftime("%Hh%M") if t.depart_heure else "", style_grand)])
        tableau = Table(data, [180, 180, 140], rowHeights=[30] + [28] * len(sel))
        tableau.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("BACKGROUND", (0, 0), (-1, 0), BLEU), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS])]))
        self.story.append(tableau)

    # ===================================================================
    # ETAT 36 - Étiquettes avec code-barres
    # ===================================================================
    def Etat_etiquettes_codebarres(self):
        style_nom = ParagraphStyle("etiq_nom", fontName=utils_polices.FONT_BOLD, fontSize=11)
        style_det = ParagraphStyle("etiq_det", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10)
        data, ligne_courante = [], []
        for t in sorted(self.liste_transports, key=self.Cle_nom):
            code = "T%d" % t.pk
            barre = code39.Extended39(code, barHeight=12, humanReadable=False)
            contenu = Table([
                [Paragraph("%s %s" % (t.individu.prenom, t.individu.nom), style_nom)],
                [barre],
                [Paragraph("%s — %s" % (self.Get_ligne_ou_mode(t), t.depart_heure.strftime("%Hh%M") if t.depart_heure else ""), style_det)],
            ], colWidths=[240])
            contenu.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, BLEU), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                          ("LEFTPADDING", (0, 0), (-1, -1), 8), ("ALIGN", (0, 1), (0, 1), "CENTER")]))
            ligne_courante.append(contenu)
            if len(ligne_courante) == 2:
                data.append(ligne_courante)
                ligne_courante = []
        if ligne_courante:
            data.append(ligne_courante + [""])
        tableau = Table(data, [250, 250])
        tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        self.story.append(tableau)

    # ===================================================================
    # ETAT 37 - Par tranche d'âge
    # ===================================================================
    def Etat_par_age(self):
        def tranche(age):
            if age is None:
                return "Âge inconnu"
            if age <= 6:
                return "3-6 ans"
            if age <= 10:
                return "7-10 ans"
            return "11 ans et +"
        for t_label in ["3-6 ans", "7-10 ans", "11 ans et +", "Âge inconnu"]:
            sel = sorted([t for t in self.liste_transports if tranche(self.Get_age(t)) == t_label], key=self.Cle_nom)
            if sel:
                self.Groupe_titre("%s (%d)" % (t_label, len(sel)))
                lignes = [[t.individu.nom, t.individu.prenom, self.Get_age(t) if self.Get_age(t) is not None else "-", self.Get_ligne_ou_mode(t),
                           t.depart_heure.strftime("%Hh%M") if t.depart_heure else ""] for t in sel]
                self.Table_nominative(lignes, ["Nom", "Prénom", "Âge", "Ligne", "Départ"], [70, 60, 40, 90, 60])

    # ===================================================================
    # ETAT 38 - Programmations désactivées qui auraient pu s'appliquer
    # ===================================================================
    def Etat_prog_desactivees(self):
        categories = self.dict_donnees["categories"]
        sel = self.Get_transports_programmes(date=self.date, categories=categories, uniquement_actifs=False)
        sel = [t for t in sel if not t.actif]
        if not sel:
            self.story.append(Paragraph("Aucune programmation désactivée n'aurait dû s'appliquer à cette date.", self.Style_defaut()))
            return
        lignes = [[t.individu.nom, t.individu.prenom, self.Get_ligne_ou_mode(t), "Programmation #%d" % t.pk, t.observations or ""] for t in sel]
        self.Table_nominative(lignes, ["Nom", "Prénom", "Ligne", "Programmation", "Motif / Observations"], [65, 60, 70, 90, 190], alerte_lignes=set(range(len(lignes))))

    # ===================================================================
    # ETAT 39 - Occupation cumulée par ligne
    # ===================================================================
    def Etat_occupation_ligne(self):
        lignes_dispo = sorted(set(t.ligne.nom for t in self.liste_transports if t.ligne))
        for nom_ligne in lignes_dispo:
            sel = sorted([t for t in self.liste_transports if t.ligne and t.ligne.nom == nom_ligne], key=lambda t: Minutes(t.depart_heure))
            total = sum(max(self.Get_duree(t) or 0, 0) for t in sel)
            self.Groupe_titre("%s — occupation totale estimée : %d min" % (nom_ligne, total))
            lignes = [[t.individu.nom, t.individu.prenom, t.depart_heure.strftime("%Hh%M") if t.depart_heure else "",
                       t.arrivee_heure.strftime("%Hh%M") if t.arrivee_heure else "",
                       ("%d min" % self.Get_duree(t)) if self.Get_duree(t) is not None else "-"] for t in sel]
            self.Table_nominative(lignes, ["Nom", "Prénom", "Départ", "Arrivée", "Durée"], [80, 70, 60, 60, 60])

    # ===================================================================
    # ETAT 40 - Contrôle de cohérence transport / présence déclarée
    # ===================================================================
    def Etat_controle_presence(self):
        self.story.append(Paragraph(
            "Compare, pour chaque transport, la présence déclarée (réservation/consommation) sur les activités liées "
            "aux unités du transport. Sans activité renseignée sur le transport, la cohérence ne peut pas être vérifiée.",
            self.Style_soustitre()))
        sel = sorted(self.liste_transports, key=self.Cle_nom)
        lignes, alertes = [], set()
        for i, t in enumerate(sel):
            activite_ids = {u.activite_id for u in t.unites.all()}
            if not activite_ids:
                statut = "Non vérifiable (aucune activité liée)"
            elif activite_ids & self.dict_presences.get(t.individu_id, set()):
                statut = "OK"
            else:
                statut = "A VERIFIER"
                alertes.add(i)
            lignes.append([t.individu.nom, t.individu.prenom, "Oui", "Oui" if statut == "OK" else ("?" if "Non vérifiable" in statut else "Non"), statut])
        self.Table_nominative(lignes, ["Nom", "Prénom", "Transport prévu", "Présence déclarée", "Statut"], [80, 70, 90, 100, 130], alerte_lignes=alertes)
