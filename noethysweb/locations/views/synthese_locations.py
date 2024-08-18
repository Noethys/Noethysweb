# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates, utils_infos_individus
from core.models import Location
from locations.forms.synthese_locations import Formulaire


class View(CustomView, TemplateView):
    menu_code = "synthese_locations"
    template_name = "locations/synthese_locations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Synthèse des locations"
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
            "titre": "Synthèse des locations",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])

        # Récupération des informations familiales et individuelles
        infosIndividus = utils_infos_individus.Informations(date_reference=date_debut, qf=False, inscriptions=False, messages=False, infosMedicales=False,
                                                                 cotisationsManquantes=False, piecesManquantes=False, questionnaires=True, scolarite=False)
        dictInfosFamilles = infosIndividus.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

        # Locations
        locations = Location.objects.select_related("famille", "produit", "produit__categorie").filter(date_fin__gte=date_debut, date_debut__lte=date_fin, produit__categorie__in=parametres["categories_produits"])

        # Calcul des données
        dictResultats = {}
        liste_produits = []
        for location in locations:

            # Recherche du regroupement
            if parametres["regroupement"] == "jour": regroupement = location.date_debut.date()
            if parametres["regroupement"] == "mois": regroupement = (location.date_debut.year, location.date_debut.month)
            if parametres["regroupement"] == "annee": regroupement = location.date_debut.year
            if parametres["regroupement"] == "categorie": regroupement = location.produit.categorie.nom
            if parametres["regroupement"] == "ville_residence": regroupement = dictInfosFamilles[location.famille_id]["FAMILLE_VILLE"]
            if parametres["regroupement"] == "secteur": regroupement = dictInfosFamilles[location.famille_id]["FAMILLE_SECTEUR"]
            if parametres["regroupement"] == "famille": regroupement = dictInfosFamilles[location.famille_id]["FAMILLE_NOM"]
            if parametres["regroupement"] == "regime": regroupement = dictInfosFamilles[location.famille_id]["FAMILLE_NOM_REGIME"]
            if parametres["regroupement"] == "caisse": regroupement = dictInfosFamilles[location.famille_id]["FAMILLE_NOM_CAISSE"]

            # Questionnaires
            if parametres["regroupement"].startswith("question_") and "famille" in parametres["regroupement"]:
                regroupement = dictInfosFamilles[location.famille_id]["QUESTION_%s" % parametres["regroupement"][17:]]

            if not regroupement:
                regroupement = "- Non renseigné -"

            if parametres["donnees"] == "quantite":
                valeur = 1
                defaut = 0
            else:
                defaut = datetime.timedelta(hours=0, minutes=0)
                valeur = datetime.timedelta(hours=0, minutes=0)
                if location.date_fin:
                    valeur = location.date_fin - location.date_debut
                else:
                    if location.date_debut < datetime.datetime.now():
                        valeur = datetime.datetime.now() - location.date_debut

            # En cas de regroupements multiples :
            if type(regroupement) == list:
                listeRegroupements = regroupement
            else:
                listeRegroupements = [regroupement, ]

            for regroupement in listeRegroupements:
                if not location.produit_id in dictResultats:
                    dictResultats[location.produit_id] = {}
                if not regroupement in dictResultats[location.produit_id]:
                    dictResultats[location.produit_id][regroupement] = defaut
                dictResultats[location.produit_id][regroupement] += valeur

            if location.produit not in liste_produits:
                liste_produits.append(location.produit)

        # Création de l'affichage
        liste_colonnes = []

        if parametres["donnees"] == "quantite":
            defaut = 0
        else:
            defaut = datetime.timedelta(hours=0, minutes=0)

        listeProduitsUtilises = []
        listeRegroupement = []
        dictTotaux = { "lignes" : {}, "colonnes" : {} }
        for IDproduit, dictProduit in dictResultats.items():
            if IDproduit not in listeProduitsUtilises:
                listeProduitsUtilises.append(IDproduit)
            for regroupement, valeur in dictProduit.items():
                if regroupement not in listeRegroupement:
                    listeRegroupement.append(regroupement)

                # Calcul des totaux
                if (IDproduit in dictTotaux["lignes"]) == False :
                    dictTotaux["lignes"][IDproduit] = defaut
                dictTotaux["lignes"][IDproduit] += valeur
                if (regroupement in dictTotaux["colonnes"]) == False :
                    dictTotaux["colonnes"][regroupement] = defaut
                dictTotaux["colonnes"][regroupement] += valeur

        # Création des colonnes
        liste_colonnes.append("Regroupement")
        dictColonnes = {}
        index = 0
        for produit in liste_produits:
            liste_colonnes.append(produit.nom)
            dictColonnes[produit.pk] = index
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
            else: label = str(regroupement)

            liste_lignes[index]["0"] = label
            dictLignes[regroupement] = index
            index += 1

        # Remplissage des valeurs
        for IDproduit, dictProduit in dictResultats.items():
            for regroupement, valeur in dictProduit.items():
                label = self.FormateValeur(valeur, parametres["donnees"])
                numLigne = dictLignes[regroupement]
                numColonne = dictColonnes[IDproduit]
                liste_lignes[numLigne][str(numColonne+1)] = label

        return liste_colonnes, liste_lignes

    def FormateValeur(self, valeur, mode="quantite"):
        if mode == "quantite":
            return valeur
        if "duree" in mode:
            heures = (valeur.days*24) + (valeur.seconds/3600)
            minutes = valeur.seconds % 3600/60
            return "%dh%02d" % (heures, minutes)
