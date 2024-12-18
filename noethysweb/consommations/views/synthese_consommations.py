# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates, utils_infos_individus
from core.models import Unite, Evenement, Consommation, Groupe
from consommations.forms.synthese_consommations import Formulaire


class View(CustomView, TemplateView):
    menu_code = "synthese_consommations"
    template_name = "consommations/synthese_consommations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Synthèse des consommations"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_colonnes, liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
            "titre": "Synthèse des consommations",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])

        # Récupération des informations familiales et individuelles
        infosIndividus = utils_infos_individus.Informations(date_reference=date_debut, qf=True, inscriptions=True, messages=False, infosMedicales=False,
                                                                 cotisationsManquantes=False, piecesManquantes=False, questionnaires=True, scolarite=True)
        dictInfosIndividus = infosIndividus.GetDictValeurs(mode="individu", ID=None, formatChamp=False)
        dictInfosFamilles = infosIndividus.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

        # Unités
        liste_unites = Unite.objects.filter(activite=parametres["activite"])

        # Evènements
        dictEvenements = {}
        for evenement in Evenement.objects.filter(activite=parametres["activite"]):
            dictEvenements[evenement.pk] = evenement

        # Consommations
        consommations = Consommation.objects.values("date", "individu_id", "inscription__famille_id", "quantite", "groupe_id", "evenement_id", "heure_debut", "heure_fin", "unite_id", "prestation_id", "prestation__temps_facture", "activite__nom", "groupe__nom", "categorie_tarif__nom").filter(activite=parametres["activite"], date__gte=date_debut, date__lte=date_fin, etat__in=parametres["etats"]).order_by("date")

        # Calcul des données
        dictResultats = {}
        listePrestationsTraitees = []
        for conso in consommations:

            # Recherche du regroupement
            if parametres["regroupement"] == "jour": regroupement = conso["date"]
            if parametres["regroupement"] == "mois": regroupement = (conso["date"].year, conso["date"].month)
            if parametres["regroupement"] == "annee": regroupement = conso["date"].year
            if parametres["regroupement"] == "activite": regroupement = conso["activite__nom"]
            if parametres["regroupement"] == "groupe": regroupement = conso["groupe__nom"]
            if parametres["regroupement"] == "evenement": regroupement = conso["evenement_id"]
            if parametres["regroupement"] == "evenement_date": regroupement = conso["evenement_id"]
            if parametres["regroupement"] == "categorie_tarif": regroupement = conso["categorie_tarif__nom"]
            if parametres["regroupement"] == "ville_residence": regroupement = dictInfosIndividus[conso["individu_id"]]["INDIVIDU_VILLE"]
            if parametres["regroupement"] == "secteur": regroupement = dictInfosIndividus[conso["individu_id"]]["INDIVIDU_SECTEUR"]
            if parametres["regroupement"] == "genre": regroupement = dictInfosIndividus[conso["individu_id"]]["INDIVIDU_SEXE"]
            if parametres["regroupement"] == "age": regroupement = dictInfosIndividus[conso["individu_id"]]["INDIVIDU_AGE_INT"]
            if parametres["regroupement"] == "ville_naissance": regroupement = dictInfosIndividus[conso["individu_id"]]["INDIVIDU_VILLE_NAISS"]
            if parametres["regroupement"] == "nom_ecole": regroupement = dictInfosIndividus[conso["individu_id"]]["SCOLARITE_NOM_ECOLE"]
            if parametres["regroupement"] == "nom_classe": regroupement = dictInfosIndividus[conso["individu_id"]]["SCOLARITE_NOM_CLASSE"]
            if parametres["regroupement"] == "nom_niveau_scolaire": regroupement = dictInfosIndividus[conso["individu_id"]]["SCOLARITE_NOM_NIVEAU"]
            if parametres["regroupement"] == "famille": regroupement = dictInfosFamilles[conso["inscription__famille_id"]]["FAMILLE_NOM"]
            if parametres["regroupement"] == "individu": regroupement = dictInfosIndividus[conso["individu_id"]]["INDIVIDU_NOM_COMPLET"]
            if parametres["regroupement"] == "regime": regroupement = dictInfosFamilles[conso["inscription__famille_id"]]["FAMILLE_NOM_REGIME"]
            if parametres["regroupement"] == "caisse": regroupement = dictInfosFamilles[conso["inscription__famille_id"]]["FAMILLE_NOM_CAISSE"]
            if parametres["regroupement"] == "categorie_travail": regroupement = dictInfosIndividus[conso["individu_id"]]["INDIVIDU_CATEGORIE_TRAVAIL"]
            if parametres["regroupement"] == "categorie_travail_pere": regroupement = dictInfosIndividus[conso["individu_id"]]["PERE_CATEGORIE_TRAVAIL"]
            if parametres["regroupement"] == "categorie_travail_mere": regroupement = dictInfosIndividus[conso["individu_id"]]["MERE_CATEGORIE_TRAVAIL"]

            # QF
            if parametres["regroupement"] == "qf":
                regroupement = None
                if "FAMILLE_QF_ACTUEL_INT" in dictInfosFamilles[conso["inscription__famille_id"]]:
                    qf = dictInfosFamilles[conso["inscription__famille_id"]]["FAMILLE_QF_ACTUEL_INT"]
                    for x in range(0, 10000, 100):
                        min, max = x, x + 99
                        if qf >= min and qf <= max:
                            regroupement = (min, max)

            # Questionnaires
            if parametres["regroupement"].startswith("question_") and "famille" in parametres["regroupement"]:
                regroupement = dictInfosFamilles[conso["inscription__famille_id"]]["QUESTION_%s" % parametres["regroupement"][17:]]
            if parametres["regroupement"].startswith("question_") and "individu" in parametres["regroupement"]:
                regroupement = dictInfosIndividus[conso["individu_id"]]["QUESTION_%s" % parametres["regroupement"][18:]]

            if not regroupement:
                regroupement = "- Non renseigné -"

            # Calcul du temps
            temps_presence = datetime.timedelta(hours=0, minutes=0)
            if conso["heure_debut"] and conso["heure_fin"]:
                valeur = datetime.timedelta(hours=conso["heure_fin"].hour, minutes=conso["heure_fin"].minute) - datetime.timedelta(hours=conso["heure_debut"].hour, minutes=conso["heure_debut"].minute)
                temps_presence += valeur

            # Si c'est en fonction du temps facturé
            temps_facture = datetime.timedelta(hours=0, minutes=0)
            if conso["prestation__temps_facture"]:
                if conso["prestation_id"] not in listePrestationsTraitees:
                    valeur = conso["prestation__temps_facture"]
                    listePrestationsTraitees.append(conso["prestation_id"])

            if parametres["afficher_detail_groupe"] == True:
                groupe = conso["groupe_id"]
            else:
                groupe = None

            if parametres["donnees"] == "quantite": valeur = conso["quantite"] if conso["quantite"] else 1
            if parametres["donnees"] == "temps_presence": valeur = temps_presence
            if parametres["donnees"] == "temps_facture": valeur = temps_facture

            if parametres["donnees"] == "quantite":
                defaut = 0
            else:
                defaut = datetime.timedelta(hours=0, minutes=0)

            # En cas de regroupements multiples :
            if type(regroupement) == list:
                listeRegroupements = regroupement
            else:
                listeRegroupements = [regroupement, ]

            for regroupement in listeRegroupements:
                if not groupe in dictResultats:
                    dictResultats[groupe] = {}
                if not conso["unite_id"] in dictResultats[groupe]:
                    dictResultats[groupe][conso["unite_id"]] = {}
                if not regroupement in dictResultats[groupe][conso["unite_id"]]:
                    dictResultats[groupe][conso["unite_id"]][regroupement] = defaut
                dictResultats[groupe][conso["unite_id"]][regroupement] += valeur

        # Création de l'affichage
        liste_colonnes = []

        if parametres["donnees"] == "quantite":
            defaut = 0
        else:
            defaut = datetime.timedelta(hours=0, minutes=0)

        listeGroupesUtilises = []
        listeUnitesUtilises = []
        listeRegroupement = []
        dictTotaux = {"lignes": {}, "colonnes": {}}
        for IDgroupe, dictGroupe in dictResultats.items():
            if IDgroupe not in listeGroupesUtilises:
                listeGroupesUtilises.append(IDgroupe)
            for IDunite, dictUnite in dictGroupe.items():
                if IDunite not in listeUnitesUtilises:
                    listeUnitesUtilises.append(IDunite)
                for regroupement, valeur in dictUnite.items():
                    if regroupement not in listeRegroupement:
                        listeRegroupement.append(regroupement)

                    # Calcul des totaux
                    if ((IDgroupe, IDunite) in dictTotaux["lignes"]) == False:
                        dictTotaux["lignes"][(IDgroupe, IDunite)] = defaut
                    dictTotaux["lignes"][(IDgroupe, IDunite)] += valeur
                    if (regroupement in dictTotaux["colonnes"]) == False:
                        dictTotaux["colonnes"][regroupement] = defaut
                    dictTotaux["colonnes"][regroupement] += valeur

        # Création des colonnes
        liste_colonnes.append("Regroupement")
        dictColonnes = {}
        if parametres["afficher_detail_groupe"] == True:
            groupes = Groupe.objects.filter(activite=parametres["activite"]).order_by("ordre")
            index = 0
            for unite in liste_unites:
                for groupe in groupes:
                    liste_colonnes.append("%s - %s" % (groupe.nom, unite.abrege if unite.abrege else unite.nom))
                    dictColonnes[(groupe.pk, unite.pk)] = index
                    index += 1
        else:
            index = 0
            for unite in liste_unites:
                liste_colonnes.append("%s" % unite.nom)
                dictColonnes[(None, unite.pk)] = index
                index += 1

        # Création des lignes
        def sortby(x):
            """ Convertit un int en str mais conserve le tri """
            if isinstance(x, int):
                x = str(x).zfill(8)
            return x
        listeRegroupement.sort(key=sortby)

        # Création d'un tableau virtuel
        liste_lignes = []
        for num_ligne in range(0, len(listeRegroupement)):
            ligne = {}
            for num_colonne in range(0, len(dictColonnes.keys())+1):
                ligne[str(num_colonne)] = ""
            liste_lignes.append(ligne)

        index = 0
        dictLignes = {}
        for regroupement in listeRegroupement:
            if parametres["regroupement"] == "jour": label = utils_dates.DateComplete(regroupement)
            elif parametres["regroupement"] == "mois": label = utils_dates.FormateMois(regroupement)
            elif parametres["regroupement"] == "annee": label = str(regroupement)
            elif parametres["regroupement"] == "evenement" and regroupement in dictEvenements: label = dictEvenements[regroupement].nom
            elif parametres["regroupement"] == "evenement_date" and regroupement in dictEvenements: label = u"%s (%s)" % (dictEvenements[regroupement].nom, utils_dates.ConvertDateToFR(dictEvenements[regroupement].date))
            elif parametres["regroupement"] == "qf" and type(regroupement) == tuple: label = u"%d-%d" % regroupement
            else: label = str(regroupement)

            liste_lignes[index]["0"] = label
            dictLignes[regroupement] = index
            index += 1

        # Remplissage des valeurs
        for IDgroupe, dictGroupe in dictResultats.items():
            for IDunite, dictUnite in dictGroupe.items():
                for regroupement, valeur in dictUnite.items():
                    label = self.FormateValeur(valeur, parametres["donnees"])
                    numLigne = dictLignes[regroupement]
                    numColonne = dictColonnes[(IDgroupe, IDunite)]
                    liste_lignes[numLigne][str(numColonne+1)] = label

        return liste_colonnes, liste_lignes

    def FormateValeur(self, valeur, mode="quantite"):
        if mode == "quantite":
            return valeur
        if "temps" in mode:
            heures = (valeur.days*24) + (valeur.seconds/3600)
            minutes = valeur.seconds % 3600/60
            return "%dh%02d" % (heures, minutes)
