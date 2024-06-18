# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, re
logger = logging.getLogger(__name__)
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from core.models import Evenement, Regime, Vacance, Activite, Quotient, TarifLigne, Consommation, Famille, Individu
from core.utils import utils_dates, utils_impression, utils_infos_individus, utils_dictionnaires
from core.utils.utils_dates import HeureStrEnDelta as HEURE


# Regex pour formule
REGEX_UNITES = re.compile(r"unite[0-9]+")


class Unite():
    def __init__(self, IDunite=None, heure_debut=None, heure_fin=None, etat=None, quantite=1):
        # Mémorisation des variables de l'unité
        self.debut = utils_dates.TimeEnDelta(heure_debut)
        self.fin = utils_dates.TimeEnDelta(heure_fin)
        self.duree = self.fin - self.debut


def FormateValeur(valeur, mode="decimal"):
    heures = int((valeur.days * 24) + (valeur.seconds / 3600))
    minutes = valeur.seconds % 3600 / 60
    if mode == "decimal":
        minDecimal = int(int(minutes) * 100 / 60)
        return float("%s.%s" % (heures, minDecimal))
    if mode == "horaire":
        return "%dh%02d" % (heures, minutes)


def GetQF(dictQuotientsFamiliaux={}, IDfamille=None, date=None):
    if IDfamille in dictQuotientsFamiliaux:
        for date_debut, date_fin, quotient in dictQuotientsFamiliaux[IDfamille]:
            if date >= date_debut and date <= date_fin :
                return quotient
    return None


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        if kwds["dict_donnees"]["options"]["orientation"] == "paysage":
            kwds["taille_page"] = landscape(A4)
        else:
            kwds["taille_page"] = portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        date_debut = self.dict_donnees["date_debut"]
        date_fin = self.dict_donnees["date_fin"]
        dict_options = self.dict_donnees["options"]
        dict_parametres = self.dict_donnees["parametres"]

        # Chargement des informations individuelles
        infosIndividus = utils_infos_individus.Informations(date_reference=self.dict_donnees["date_debut"], qf=True, inscriptions=True, messages=False, infosMedicales=False,
                                                            cotisationsManquantes=False, piecesManquantes=False, questionnaires=True, scolarite=True)
        dictInfosIndividus = infosIndividus.GetDictValeurs(mode="individu", ID=None, formatChamp=False)
        dictInfosFamilles = infosIndividus.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

        # Récupération des familles et des individus
        dict_familles = {famille.pk: famille for famille in Famille.objects.select_related("caisse").all()}
        dict_individus = {individu.pk: individu for individu in Individu.objects.all()}

        # Récupération des activités
        liste_idunite = [int(idunite) for idunite in dict_parametres.keys()]
        activites = Activite.objects.filter(unite__in=liste_idunite).distinct()

        # Evènements
        dictEvenements = {}
        for evenement in Evenement.objects.filter(date__gte=date_debut, date__lte=date_fin):
            dictEvenements[evenement.pk] = {"nom": evenement.nom, "date": evenement.date}

        # Récupération des régimes
        dictRegimes = {}
        for regime in Regime.objects.all():
            dictRegimes[regime.pk] = regime.nom

        # Récupération des périodes de vacances
        listeVacances = []
        for vacance in Vacance.objects.all().order_by("date_debut"):
            if vacance.date_debut.month in (6, 7, 8, 9) or vacance.date_fin.month in (6, 7, 8, 9):
                grandesVacs = True
            else:
                grandesVacs = False
            listeVacances.append({"nom": vacance.nom, "annee": vacance.annee, "date_debut": vacance.date_debut, "date_fin": vacance.date_fin, "vacs": True, "grandesVacs": grandesVacs})

        # Calcul des périodes détaillées
        LISTE_MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        listePeriodesDetail = []
        index = 0
        for dictTemp in listeVacances:

            # Vacances
            if dictTemp["nom"] == "Février":
                nom = "vacances_fevrier"
            elif dictTemp["nom"] == "Pâques":
                nom = "vacances_paques"
            elif dictTemp["nom"] == "Eté":
                nom = "vacances_ete"
            elif dictTemp["nom"] == "Toussaint":
                nom = "vacances_toussaint"
            elif dictTemp["nom"] == "Noël":
                nom = "vacances_noel"
            else:
                nom = "?"
            dictTemp["code"] = nom + "_%d" % dictTemp["annee"]
            dictTemp["label"] = "Vacances %s %d" % (dictTemp["nom"], dictTemp["annee"])
            listePeriodesDetail.append(dictTemp)

            # Hors vacances
            date_debut_temp = dictTemp["date_fin"] + datetime.timedelta(days=1)
            if len(listeVacances) > index + 1:
                date_fin_temp = listeVacances[index + 1]["date_debut"] - + datetime.timedelta(days=1)
                annee = dictTemp["annee"]
                if dictTemp["nom"].startswith("F"):
                    nom = "mercredis_mars_avril"
                elif dictTemp["nom"].startswith("P"):
                    nom = "mercredis_mai_juin"
                elif dictTemp["nom"].startswith("E"):
                    nom = "mercredis_sept_oct"
                elif dictTemp["nom"].startswith("T"):
                    nom = "mercredis_nov_dec"
                elif dictTemp["nom"].startswith("N"):
                    nom = "mercredis_janv_fev"
                    annee += 1
                else:
                    nom = "?"
                label = "Hors vacances %s-%s %d" % (LISTE_MOIS[date_debut_temp.month - 1], LISTE_MOIS[date_fin_temp.month - 1], annee)
                listePeriodesDetail.append({"code": nom + "_%d" % annee, "annee": annee, "label": label, "date_debut": date_debut_temp, "date_fin": date_fin_temp, "vacs": False, "grandesVacs": False})
            index += 1

        # Récupération des tranches de QF des tarifs
        if dict_options["regroupement_principal"] == "qf_tarifs":
            liste_tranches_qf = []
            for tarif_ligne in TarifLigne.objects.filter(qf_min__isnull=False, qf_max__isnull=False, activite__in=activites):
                tranche = (int(tarif_ligne.qf_min), int(tarif_ligne.qf_max))
                if tranche not in liste_tranches_qf:
                    liste_tranches_qf.append(tranche)
                    liste_tranches_qf.sort()

        # Récupération des tranches de qf perso
        if dict_options["regroupement_principal"] == "qf_perso":
            liste_tranches_qf = []
            temp = 0
            try:
                tranches_qf_perso = [int(x) for x in dict_options["tranches_qf_perso"].split(",")]
            except:
                self.erreurs.append("L'option 'Regroupement par tranche de QF n'est pas correctement renseignée")
                return False
            for x in tranches_qf_perso:
                liste_tranches_qf.append((temp, x - 1))
                temp = x
            liste_tranches_qf.append((temp, 999999))

        # Recherche des données
        listeRegimesUtilises = []

        # Préparation des tranches d'âge
        if len(dict_options["regroupement_age"]) == 0:
            dict_tranches_age = {0: {"label": u"", "min": -1, "max": -1}}
        else:
            dict_tranches_age = {}
            indexRegroupement = 0
            try:
                regroupements_age = [int(age) for age in dict_options["regroupement_age"].split(",")]
            except:
                self.erreurs.append("L'option 'Regroupement par tranche d'âge n'est pas correctement renseignée")
                return False

            for regroupement in regroupements_age:
                if indexRegroupement == 0:
                    dict_tranches_age[indexRegroupement] = {"label": "Âge < %d ans" % regroupement, "min": -1, "max": regroupement}
                else:
                    dict_tranches_age[indexRegroupement] = {
                        "label": "Âge >= %d et < %d ans" % (regroupements_age[indexRegroupement - 1], regroupement),
                        "min": regroupements_age[indexRegroupement - 1], "max": regroupement
                    }
                indexRegroupement += 1
                dict_tranches_age[indexRegroupement] = {"label": "Âge >= %d ans" % regroupement, "min": regroupement, "max": -1}

        # Récupère le QF de la famille
        dictQuotientsFamiliaux = {}
        if "qf" in dict_options["regroupement_principal"]:
            for quotient in Quotient.objects.filter(date_debut__lte=date_fin, date_fin__gte=date_debut).order_by("date_debut"):
                if quotient.famille_id not in dictQuotientsFamiliaux:
                    dictQuotientsFamiliaux[quotient.famille_id] = []
                dictQuotientsFamiliaux[quotient.famille_id].append((quotient.date_debut, quotient.date_fin, quotient.quotient))

        # Récupération des consommations
        self.dict_unites = {}
        liste_conso = Consommation.objects.select_related("unite", "activite", "groupe", "prestation", "categorie_tarif", "inscription", "evenement").filter(date__gte=date_debut, date__lte=date_fin, unite__in=liste_idunite)
        for conso in liste_conso:
            self.dict_unites.setdefault(conso.date, {})
            self.dict_unites[conso.date]["unite%d" % conso.unite_id] = Unite(conso.unite_id, conso.heure_debut, conso.heure_fin, conso.etat, conso.quantite)

        dict_resultats = {}
        listePrestationsTraitees = []
        dict_temps_journalier_individu = {}
        dict_stats = {"individus": [], "familles": []}
        for conso in liste_conso:
            individu = dict_individus[conso.individu_id]
            mois = conso.date.month
            annee = conso.date.year

            # ------------------------------------ REGROUPEMENT -----------------------------------

            # Recherche du regroupement principal
            try:
                if dict_options["regroupement_principal"] == "aucun": regroupement = None
                if dict_options["regroupement_principal"] == "jour": regroupement = conso.date
                if dict_options["regroupement_principal"] == "mois": regroupement = (annee, mois)
                if dict_options["regroupement_principal"] == "annee": regroupement = annee
                if dict_options["regroupement_principal"] == "activite": regroupement = conso.activite.nom
                if dict_options["regroupement_principal"] == "groupe": regroupement = conso.groupe.nom
                if dict_options["regroupement_principal"] == "evenement": regroupement = conso.evenement_id
                if dict_options["regroupement_principal"] == "evenement_date": regroupement = conso.evenement_id
                if dict_options["regroupement_principal"] == "categorie_tarif": regroupement = conso.categorie_tarif.nom
                if dict_options["regroupement_principal"] == "unite_conso": regroupement = conso.unite.nom
                if dict_options["regroupement_principal"] == "ville_residence": regroupement = dictInfosIndividus[conso.individu_id]["INDIVIDU_VILLE"]
                if dict_options["regroupement_principal"] == "secteur": regroupement = dictInfosIndividus[conso.individu_id]["INDIVIDU_SECTEUR"]
                if dict_options["regroupement_principal"] == "genre": regroupement = dictInfosIndividus[conso.individu_id]["INDIVIDU_SEXE"]
                if dict_options["regroupement_principal"] == "age": regroupement = dictInfosIndividus[conso.individu_id]["INDIVIDU_AGE_INT"]
                if dict_options["regroupement_principal"] == "ville_naissance": regroupement = dictInfosIndividus[conso.individu_id]["INDIVIDU_VILLE_NAISS"]
                if dict_options["regroupement_principal"] == "nom_ecole": regroupement = dictInfosIndividus[conso.individu_id]["SCOLARITE_NOM_ECOLE"]
                if dict_options["regroupement_principal"] == "nom_classe": regroupement = dictInfosIndividus[conso.individu_id]["SCOLARITE_NOM_CLASSE"]
                if dict_options["regroupement_principal"] == "nom_niveau_scolaire": regroupement = dictInfosIndividus[conso.individu_id]["SCOLARITE_NOM_NIVEAU"]
                if dict_options["regroupement_principal"] == "famille": regroupement = dictInfosFamilles[conso.individu_id]["FAMILLE_NOM"]
                if dict_options["regroupement_principal"] == "individu": regroupement = dictInfosIndividus[conso.individu_id]["INDIVIDU_NOM_COMPLET"]
                if dict_options["regroupement_principal"] == "regime": regroupement = dictInfosFamilles[conso.individu_id]["FAMILLE_NOM_REGIME"]
                if dict_options["regroupement_principal"] == "caisse": regroupement = dictInfosFamilles[conso.individu_id]["FAMILLE_NOM_CAISSE"]
                if dict_options["regroupement_principal"] == "categorie_travail": regroupement = dictInfosIndividus[conso.individu_id]["INDIVIDU_CATEGORIE_TRAVAIL"]
                if dict_options["regroupement_principal"] == "categorie_travail_pere": regroupement = dictInfosIndividus[conso.individu_id]["PERE_CATEGORIE_TRAVAIL"]
                if dict_options["regroupement_principal"] == "categorie_travail_mere": regroupement = dictInfosIndividus[conso.individu_id]["MERE_CATEGORIE_TRAVAIL"]

                # QF par tranche de 100
                if dict_options["regroupement_principal"] == "qf_100":
                    regroupement = None
                    qf = GetQF(dictQuotientsFamiliaux, conso.inscription.famille_id, conso.date)
                    for x in range(0, 10000, 100):
                        min, max = x, x + 99
                        if qf >= min and qf <= max:
                            regroupement = (min, max)

                # QF par tranches
                if dict_options["regroupement_principal"] in ("qf_tarifs", "qf_perso"):
                    regroupement = None
                    qf = GetQF(dictQuotientsFamiliaux, conso.inscription.famille_id, conso.date)
                    for min, max in liste_tranches_qf:
                        if qf >= min and qf <= max:
                            regroupement = (min, max)

                # # Etiquettes
                # if regroupement_principal == "etiquette":
                #     etiquettes = UTILS_Texte.ConvertStrToListe(etiquettes)
                #     if len(etiquettes) > 0:
                #         temp = []
                #         for IDetiquette in etiquettes:
                #             if IDetiquette in dictEtiquettes:
                #                 temp.append(dictEtiquettes[IDetiquette]["label"])
                #         regroupement = temp
                #     else:
                #         regroupement = _(u"- Aucune étiquette -")

                # Questionnaires
                if dict_options["regroupement_principal"].startswith("question_") and "famille" in dict_options["regroupement_principal"]:
                    regroupement = dictInfosFamilles[conso.inscription.famille_id]["QUESTION_%s" % dict_options["regroupement_principal"][17:]]
                if dict_options["regroupement_principal"].startswith("question_") and "individu" in dict_options["regroupement_principal"]:
                    regroupement = dictInfosIndividus[conso.individu_id]["QUESTION_%s" % dict_options["regroupement_principal"][18:]]

                # Formatage des regroupements de type date
                if type(regroupement) == datetime.date:
                    regroupement = str(regroupement)

            except:
                regroupement = None

            # ------------------------------------ ANALYSE DONNEES -----------------------------------

            # Formatage des heures
            heure_debut = conso.heure_debut
            heure_fin = conso.heure_fin

            # Recherche la période
            periode = ""
            if dict_options["periodes_detaillees"] == False:
                # Périodes non détaillées
                for dictVac in listeVacances:
                    if conso.date >= dictVac["date_debut"] and conso.date <= dictVac["date_fin"]:
                        if dictVac["grandesVacs"] == True:
                            periode = "grandesVacs"
                        else:
                            periode = "petitesVacs"
                if periode == "":
                    periode = "horsVacs"
            else:
                # Périodes détaillées
                for dictPeriode in listePeriodesDetail:
                    if conso.date >= dictPeriode["date_debut"] and conso.date <= dictPeriode["date_fin"]:
                        periode = dictPeriode["code"]

            if periode == "":
                texte = "Période inconnue pour la date du %s. Vérifiez que les périodes de vacances ont bien été paramétrées." % utils_dates.ConvertDateToFR(conso.date)
                if texte not in self.erreurs:
                    self.erreurs.append(texte)
                    return False

            # ------------ Application de filtres ---------------
            valide = False

            # Période
            if periode == "horsVacs" or periode.startswith("mercredis"):
                if str(conso.date.weekday()) in dict_options["jours_hors_vacances"]:
                    valide = True
            if periode in ("grandesVacs", "petitesVacs") or periode.startswith("vacances"):
                if str(conso.date.weekday()) in dict_options["jours_vacances"]:
                    valide = True

            # Etat
            if conso.etat not in dict_options["etat_consommations"]:
                valide = False

            # Calculs
            if valide == True:

                # ----- Recherche de la méthode de calcul pour cette unité -----
                dictCalcul = dict_parametres[str(conso.unite_id)]

                valeur = datetime.timedelta(hours=0, minutes=0)

                if dictCalcul["type"] == "0":
                    # Si c'est selon le coeff :
                    if valeur == None or valeur == "":
                        valeur = datetime.timedelta(hours=0, minutes=0)
                    else:
                        try:
                            valeur = datetime.timedelta(hours=float(dictCalcul["coeff"]), minutes=0)
                        except:
                            pass

                elif dictCalcul["type"] == "1":

                    # Si c'est en fonction du temps réél :
                    if heure_debut != None and heure_debut != "" and heure_fin != None and heure_fin != "":

                        # Si une heure seuil est demandée
                        heure_seuil = dictCalcul["heure_seuil"]
                        if heure_seuil:
                            try:
                                heure_seuil = utils_dates.HeureStrEnTime(heure_seuil)
                            except:
                                self.erreurs.append("L'heure de seuil de l'unité %s ne semble pas valide. Vérifiez qu'elle est au format 'hh:mm'." % conso.unite.nom)
                                return False
                            if heure_debut < heure_seuil:
                                heure_debut = heure_seuil

                        # Si une heure plafond est demandée
                        heure_plafond = dictCalcul["heure_plafond"]
                        if heure_plafond:
                            try:
                                heure_plafond = utils_dates.HeureStrEnTime(heure_plafond)
                            except:
                                self.erreurs.append("L'heure de plafond de l'unité %s ne semble pas valide. Vérifiez qu'elle est au format 'hh:mm'." % conso.unite.nom)
                                return False

                            if heure_fin > heure_plafond:
                                heure_fin = heure_plafond

                        # Calcul de la durée
                        valeur = datetime.timedelta(hours=heure_fin.hour, minutes=heure_fin.minute) - datetime.timedelta(hours=heure_debut.hour, minutes=heure_debut.minute)

                        # Si un arrondi est demandé
                        arrondi = dictCalcul["arrondi"]
                        if arrondi:

                            arrondi_type, arrondi_delta = arrondi.split(";")
                            valeur = utils_dates.CalculerArrondi(arrondi_type=arrondi_type, arrondi_delta=int(arrondi_delta), heure_debut=heure_debut, heure_fin=heure_fin)

                        # Si une durée seuil est demandée
                        duree_seuil = dictCalcul["duree_seuil"]
                        if duree_seuil:
                            try:
                                duree_seuil = utils_dates.HeureStrEnDelta(duree_seuil)
                            except:
                                self.erreurs.append("La durée seuil de l'unité %s ne semble pas valide. Vérifiez qu'elle est au format 'hh:mm'." % conso.unite.nom)
                                return False
                            if valeur < duree_seuil:
                                valeur = duree_seuil

                        # Si une durée plafond est demandée
                        duree_plafond = dictCalcul["duree_plafond"]
                        if duree_plafond:
                            try:
                                duree_plafond = utils_dates.HeureStrEnDelta(duree_plafond)
                            except:
                                self.erreurs.append("La durée plafond de l'unité %s ne semble pas valide. Vérifiez qu'elle est au format 'hh:mm'." % conso.unite.nom)
                                return False
                            if valeur > duree_plafond:
                                valeur = duree_plafond

                elif dictCalcul["type"] == "2":
                    # Si c'est en fonction du temps facturé
                    if conso.prestation.temps_facture != None and conso.prestation.temps_facture != "":
                        if conso.prestation_id not in listePrestationsTraitees:
                            valeur = conso.prestation.temps_facture
                            listePrestationsTraitees.append(conso.prestation_id)

                elif dictCalcul["type"] == "3":
                    # Calcul selon une formule
                    try:
                        valeur = self.Calcule_formule(formule=dictCalcul["formule"], date=conso.date, debut=heure_debut, fin=heure_fin)
                    except Exception as err:
                        self.erreurs.append("La formule saisie pour l'unité %s ne semble pas valide : %s" % (conso.unite.nom, err))
                        return False

                elif dictCalcul["type"] == "4":
                    # Si c'est selon l'équivalence en heures paramétrée :
                    valeur = datetime.timedelta(hours=0, minutes=0)
                    if conso.unite.equiv_heures:
                        valeur = utils_dates.TimeEnDelta(conso.unite.equiv_heures)
                    if conso.evenement and conso.evenement.equiv_heures:
                        valeur = utils_dates.TimeEnDelta(conso.evenement.equiv_heures)

                # Options plafond journalier par individu (valable pour l'ensemble des activités)
                plafond_journalier_individu = dict_options["plafond_journalier_individu"]
                if plafond_journalier_individu > 0:
                    dict_temps_journalier_individu = utils_dictionnaires.DictionnaireImbrique(dictionnaire=dict_temps_journalier_individu, cles=[conso.individu_id, conso.date], valeur=datetime.timedelta(hours=0, minutes=0))
                    if dict_temps_journalier_individu[conso.individu_id][conso.date] + valeur > datetime.timedelta(minutes=plafond_journalier_individu):
                        valeur = datetime.timedelta(minutes=plafond_journalier_individu) - dict_temps_journalier_individu[conso.individu_id][conso.date]
                    dict_temps_journalier_individu[conso.individu_id][conso.date] += valeur

                # Calcule l'âge de l'individu
                if individu.date_naiss:
                    age = (conso.date.year - individu.date_naiss.year) - int((conso.date.month, conso.date.day) < (individu.date_naiss.month, individu.date_naiss.day))
                else:
                    age = -1

                # ----- Recherche du regroupement par âge ou date de naissance  -----
                if len(dict_tranches_age) == 0:
                    index_tranche_age = 0
                else:
                    for key, dictTemp in dict_tranches_age.items():
                        if "min" in dictTemp:
                            if dictTemp["min"] == -1 and age < dictTemp["max"]: index_tranche_age = key
                            if dictTemp["max"] == -1 and age >= dictTemp["min"]: index_tranche_age = key
                            if dictTemp["min"] != -1 and dictTemp["max"] != -1 and age >= dictTemp["min"] and age < dictTemp["max"]: index_tranche_age = key

                if age == -1:
                    index_tranche_age = None

                # Mémorisation du résultat
                if valeur != datetime.timedelta(hours=0, minutes=0) or valeur != datetime.timedelta(hours=0, minutes=0):
                    famille = dict_familles[conso.inscription.famille_id]
                    if famille.caisse:
                        IDregime = famille.caisse.regime_id
                    else:
                        IDregime = 0
                        if dict_options["afficher_regime_inconnu"] == True:
                            self.erreurs.append("Attention, le régime d'appartenance n'a pas été renseigné pour la famille de %s. Remarque : Vous pouvez masquer cette erreur dans les options." % individu.Get_nom())
                            return False

                    # Si régime inconnu :
                    if dict_options["associer_regime_inconnu"] not in (None, "non", "") and IDregime == 0:
                        IDregime = int(dict_options["associer_regime_inconnu"])

                    # Mémoriser les régimes à afficher
                    if IDregime not in listeRegimesUtilises:
                        listeRegimesUtilises.append(IDregime)

                    # Stats globales
                    if conso.individu_id not in dict_stats["individus"]:
                        dict_stats["individus"].append(conso.individu_id)
                    if conso.inscription.famille_id not in dict_stats["familles"]:
                        dict_stats["familles"].append(conso.inscription.famille_id)

                    # Mémorisation du résultat
                    dict_resultats = utils_dictionnaires.DictionnaireImbrique(dictionnaire=dict_resultats, cles=[regroupement, index_tranche_age, periode, IDregime], valeur=datetime.timedelta(hours=0, minutes=0))
                    quantite = conso.quantite if conso.quantite else 1
                    dict_resultats[regroupement][index_tranche_age][periode][IDregime] += valeur * quantite

        # Création du titre du document
        self.Insert_header()

        # Insertion du label Paramètres
        # styleA = ParagraphStyle(name="A", fontName="Helvetica", fontSize=6, spaceAfter=0)
        # self.story.append(Paragraph(u"<b>Critères :</b> %s" % labelParametres, styleA))

        txt_stats_globales = u"%d individus | %d familles" % (len(dict_stats["individus"]), len(dict_stats["familles"]))
        styleA = ParagraphStyle(name="A", fontName="Helvetica", fontSize=6, spaceAfter=20)
        self.story.append(Paragraph(u"<b>Résultats :</b> %s" % txt_stats_globales, styleA))

        # Tri du niveau de regroupement principal
        regroupements = list(dict_resultats.keys())
        regroupements.sort()

        listeRegimesUtilises.sort()

        for regroupement in regroupements:

            dict_resultats_age = dict_resultats[regroupement]
            dict_totaux_regroupement = {}

            # Création des colonnes
            listeColonnes = []
            largeurColonne = 80
            for IDregime in listeRegimesUtilises:
                if IDregime in dictRegimes:
                    nomRegime = dictRegimes[IDregime]
                else:
                    nomRegime = "Sans régime"
                listeColonnes.append((IDregime, nomRegime, largeurColonne))
            listeColonnes.append((2000, "Total", largeurColonne))

            dataTableau = []

            listeStyles = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (-1, 0), "Helvetica-Bold", 7),
                ('FONT', (0, -1), (-1, -1), "Helvetica", 7), ('GRID', (1, 0), (-1, -1), 0.25, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTRE'), ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 7),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'), ]

            if dict_options["regroupement_principal"] != "aucun":
                listeStyles.append(('BACKGROUND', (0, 0), (0, 0), dict_options["couleur_case_regroupement"]))
                listeStyles.append(('TEXTCOLOR', (0, 0), (0, 0), dict_options["couleur_texte_regroupement"].replace('"', "")))

            # Formatage du regroupement
            if dict_options["regroupement_principal"] == "aucun": label_regroupement = ""
            elif dict_options["regroupement_principal"] == "jour": label_regroupement = utils_dates.ConvertDateToFR(regroupement)
            elif dict_options["regroupement_principal"] == "mois": label_regroupement = utils_dates.FormateMois(regroupement)
            elif dict_options["regroupement_principal"] == "annee": label_regroupement = str(regroupement)
            elif dict_options["regroupement_principal"] == "evenement" and regroupement in dictEvenements: label_regroupement = dictEvenements[regroupement]["nom"]
            elif dict_options["regroupement_principal"] == "evenement_date" and regroupement in dictEvenements: label_regroupement = u"%s (%s)" % (dictEvenements[regroupement]["nom"], utils_dates.ConvertDateToFR(dictEvenements[regroupement]["date"]))
            elif dict_options["regroupement_principal"].startswith("qf") and type(regroupement) == tuple: label_regroupement = u"%d-%d" % regroupement
            elif dict_options["regroupement_principal"] == "age": label_regroupement = "%d ans" % regroupement
            else: label_regroupement = str(regroupement)

            if dict_options["regroupement_principal"] != "aucun" and label_regroupement in ("None", ""):
                label_regroupement = "- Non renseigné -"

            # Régimes + total
            ligne1 = [label_regroupement, ]
            largeursColonnes = [150, ]
            indexColonne = 1
            for IDregime, label, largeur in listeColonnes:
                ligne1.append(label)
                largeursColonnes.append(largeur)
                indexColonne += 1

            dataTableau.append(ligne1)

            # Création du tableau d'entete de colonnes
            tableau = Table(dataTableau, largeursColonnes)
            tableau.setStyle(TableStyle(listeStyles))
            self.story.append(tableau)

            paraStyle = ParagraphStyle(name="normal", fontName="Helvetica", fontSize=7, leading=7, spaceBefore=0, spaceAfter=0)

            # Création des lignes
            index = 1
            for index_tranche_age, dict_resultats_periode in dict_resultats_age.items():

                dataTableau = []

                # Création des niveaux de regroupement
                if index_tranche_age in dict_tranches_age:
                    label_tranche_age = dict_tranches_age[index_tranche_age]["label"]
                else:
                    label_tranche_age = "Sans date de naissance"

                if label_tranche_age != "":
                    ligne = [label_tranche_age, ]
                    for IDregime, label, largeur in listeColonnes[:-1]:
                        ligne.append("")
                    dataTableau.append(ligne)
                    index += 1

                # Création des lignes de périodes
                if dict_options["periodes_detaillees"] == False:
                    listePeriodes = [{
                        "code": "petitesVacs", "label": "Petites vacances"},
                        {"code": "grandesVacs", "label": "Vacances d'été"},
                        {"code": "horsVacs", "label": "Hors vacances"},
                    ]
                else:
                    listePeriodes = listePeriodesDetail

                dictTotaux = {}
                for dictPeriode in listePeriodes:
                    if dictPeriode["code"] in dict_resultats_periode:
                        ligne = []

                        # Label ligne
                        if dict_options["periodes_detaillees"] == False:
                            ligne.append(dictPeriode["label"])
                        else:
                            date_debut_temp = dictPeriode["date_debut"]
                            if date_debut_temp < date_debut:
                                date_debut_temp = date_debut
                            date_fin_temp = dictPeriode["date_fin"]
                            if date_fin_temp > date_fin:
                                date_fin_temp = date_fin
                            label = "<para align='center'>%s<br/><font size=5>Du %s au %s</font></para>" % (
                                dictPeriode["label"],
                                utils_dates.ConvertDateToFR(date_debut_temp),
                                utils_dates.ConvertDateToFR(date_fin_temp)
                            )
                            ligne.append(Paragraph(label, paraStyle))

                        # Valeurs
                        totalLigne = datetime.timedelta(hours=0, minutes=0)
                        for IDregime, labelColonne, largeurColonne in listeColonnes:
                            if IDregime < 1000:
                                if IDregime in dict_resultats_periode[dictPeriode["code"]]:
                                    valeur = dict_resultats_periode[dictPeriode["code"]][IDregime]
                                else:
                                    valeur = datetime.timedelta(hours=0, minutes=0)
                                ligne.append(FormateValeur(valeur, dict_options["format_donnees"]))
                                totalLigne += valeur
                                if (IDregime in dictTotaux) == False:
                                    dictTotaux[IDregime] = datetime.timedelta(hours=0, minutes=0)
                                dictTotaux[IDregime] += valeur
                        # Total de la ligne
                        if IDregime == 2000:
                            ligne.append(FormateValeur(totalLigne, dict_options["format_donnees"]))
                        dataTableau.append(ligne)
                        index += 1

                # Création de la ligne de total
                ligne = ["Total", ]
                totalLigne = datetime.timedelta(hours=0, minutes=0)
                indexColonne = 0
                for IDregime, labelColonne, largeurColonne in listeColonnes:
                    if IDregime < 1000:
                        if IDregime in dictTotaux:
                            total = dictTotaux[IDregime]
                        else:
                            total = datetime.timedelta(hours=0, minutes=0)

                        ligne.append(FormateValeur(total, dict_options["format_donnees"]))
                        totalLigne += total

                        if (indexColonne in dict_totaux_regroupement) == False:
                            dict_totaux_regroupement[indexColonne] = datetime.timedelta(hours=0, minutes=0)
                        dict_totaux_regroupement[indexColonne] += total

                    indexColonne += 1

                # Total de la ligne
                if IDregime == 2000:
                    ligne.append(FormateValeur(totalLigne, dict_options["format_donnees"]))
                dataTableau.append(ligne)
                index += 1

                # Récupération des couleurs
                couleurFondFonce = dict_options["couleur_ligne_age"]
                couleurFondClair = dict_options["couleur_ligne_total"]

                listeStyles = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

                    ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),

                    ('BACKGROUND', (0, -1), (-1, -1), couleurFondClair),
                    ('BACKGROUND', (-1, 0), (-1, -1), couleurFondClair),

                    ('FONT', (0, -1), (-1, -1), "Helvetica-Bold", 7),  # Gras pour totaux
                ]

                if label_tranche_age != "":
                    listeStyles.extend([('ALIGN', (0, 0), (-1, 0), 'LEFT'), ('SPAN', (0, 0), (-1, 0)),
                        ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 7),
                        ('BACKGROUND', (0, 0), (-1, 0), couleurFondFonce), ])

                # Création du tableau
                tableau = Table(dataTableau, largeursColonnes)
                tableau.setStyle(TableStyle(listeStyles))
                self.story.append(tableau)

            # ---------- TOTAL de L'ACTIVITE --------------
            dataTableau = []

            listeStyles = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (-1, 0), "Helvetica-Bold", 7),
                ('FONT', (0, -1), (-1, -1), "Helvetica", 7), ('GRID', (1, 0), (-1, -1), 0.25, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTRE'), ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 7),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'), ]

            ligne1 = ["", ]
            largeursColonnes = [150, ]
            indexColonne = 0
            total = datetime.timedelta(hours=0, minutes=0)
            for IDregime, label, largeur in listeColonnes:

                # Colonne Total par régime
                if indexColonne in dict_totaux_regroupement:
                    valeur = dict_totaux_regroupement[indexColonne]
                else:
                    valeur = datetime.timedelta(hours=0, minutes=0)
                total += valeur

                # Colonne TOTAL du tableau
                if indexColonne == len(listeColonnes) - 1:
                    valeur = total

                label = FormateValeur(valeur, dict_options["format_donnees"])
                ligne1.append(label)
                largeursColonnes.append(largeur)
                indexColonne += 1
            dataTableau.append(ligne1)

            # Création du tableau d'entete de colonnes
            tableau = Table(dataTableau, largeursColonnes)
            tableau.setStyle(TableStyle(listeStyles))
            self.story.append(tableau)

            # Espace après activité
            self.story.append(Spacer(0, 20))

    def Calcule_formule(self, formule="", date=None, debut=None, fin=None):
        debut = utils_dates.TimeEnDelta(debut)
        fin = utils_dates.TimeEnDelta(fin)
        duree = fin - debut

        def SI(condition=None, alors=None, sinon=datetime.timedelta(minutes=0)):
            if condition:
                return alors
            else:
                return sinon

        # Remplacements
        remplacements = [("\n", ""), ("ET", "and"), ("OU", "or")]
        for expression, remplacement in remplacements:
            formule = formule.replace(expression, remplacement)

        # Unités
        dict_unites_date = self.dict_unites.get(date)
        for code_unite in REGEX_UNITES.findall(formule):
            unite = dict_unites_date.get(code_unite, None)
            setattr(self, code_unite, unite)
            formule = formule.replace(code_unite, "self.%s" % code_unite)

        # Calcul de la formule
        resultat = eval(formule)
        if resultat == None :
            resultat = datetime.timedelta(minutes=0)
        if type(resultat) == int:
            resultat = datetime.timedelta(hours=resultat)

        return resultat
