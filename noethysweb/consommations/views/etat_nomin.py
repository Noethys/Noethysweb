# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Consommation, Vacance, Parametre, Quotient, Scolarite
from core.utils import utils_questionnaires
from consommations.forms.etat_nomin import Formulaire


def get_data_profil(donnees=None, request=None):
    """ Récupère les données à sauvegarder dans le profil de configuration """
    form = Formulaire(donnees, request=request)

    # Validation des paramètres
    if not form.is_valid():
        #todo : pas fonctionnel
        print("Erreurs =", form.errors.as_data())
        return JsonResponse({"erreur": "Les paramètres ne sont pas valides"}, status=401)

    # Suppression des données inutiles
    data = form.cleaned_data
    [data.pop(key) for key in ["profil",]]
    return data


class View(CustomView, TemplateView):
    menu_code = "etat_nomin"
    template_name = "consommations/etat_nomin.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Etat nominatif"
        context['box_introduction'] = "Sélectionnez une période et une ou plusieurs activités, puis créez les colonnes souhaitées avant de cliquer sur le bouton Actualiser."

        # Form par défaut
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)

        # Application du profil de configuration
        profil = Parametre.objects.filter(idparametre=int(self.request.POST.get("profil"))).first() if self.request.POST.get("profil") else False
        if profil and self.request.POST.get("application_profil"):
            request_post = self.request.POST.copy()
            request_post["profil"] = profil.pk
            initial_data = json.loads(profil.parametre)
            [request_post.pop(key) for key in initial_data.keys() if key in request_post]
            request_post.update(initial_data)
            context['form_parametres'] = Formulaire(initial=request_post, request=self.request)

        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_colonnes, liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
            "afficher_resultats": "type_submit" in request.POST,
            "titre": form.cleaned_data.get("titre", "Etat nominatif"),
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        # Création des conditions de période et d'activités
        date_min = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_max = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
        param_activites = json.loads(parametres["activites"])
        conditions_periodes = Q(date__gte=date_min) & Q(date__lte=date_max)
        if param_activites["type"] == "groupes_activites":
            condition_activites = Q(activite__groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            condition_activites = Q(activite__in=param_activites["ids"])

        # Consommations
        conditions = conditions_periodes & condition_activites & Q(etat__in=parametres["etats"])
        if parametres.get("filtre_caisses") == "SELECTION":
            conditions &= Q(inscription__famille__caisse_id__in=[int(idcaisse) for idcaisse in parametres["caisses"]])
        consommations = Consommation.objects.select_related("individu", "inscription", "inscription__famille", "inscription__famille__caisse", "inscription__famille__allocataire","prestation", "unite").filter(conditions)

        # Importation des scolarités
        dict_scolarites = {}
        if parametres.get("filtre_ecoles") == "SELECTION":
            for scolarite in Scolarite.objects.filter(ecole_id__in=[int(idecole) for idecole in parametres["ecoles"]], date_debut__lte=date_max, date_fin__gte=date_min):
                dict_scolarites.setdefault(scolarite.individu, [])
                dict_scolarites[scolarite.individu].append((scolarite.date_debut, scolarite.date_fin))

        # Importation des vacances
        liste_vacances = Vacance.objects.filter(date_fin__gte=date_min, date_debut__lte=date_max)

        # Importation des QF
        conditions_qf = Q(famille__in=[conso.inscription.famille for conso in consommations]) & Q(date_debut__lte=date_max) & Q(date_fin__gte=date_min)
        dict_quotients = {quotient.famille_id: quotient.quotient for quotient in Quotient.objects.filter(conditions_qf)}

        # Importation des questionnaires
        questionnaires_individus = utils_questionnaires.ChampsEtReponses(categorie="individu", filtre_reponses=Q(individu__in=[conso.individu for conso in consommations]))
        questionnaires_familles = utils_questionnaires.ChampsEtReponses(categorie="famille", filtre_reponses=Q(famille__in=[conso.inscription.famille for conso in consommations]))

        # Récupération des colonnes
        colonnes = json.loads(parametres["colonnes"])

        # Calcul des données
        resultats = {}
        for conso in consommations:

            # Filtre ville (placé ici car crypté)
            if parametres.get("filtre_villes") == "SELECTION":
                if conso.individu.ville_resid not in parametres["villes"]:
                    continue

            # Filtre écoles
            if parametres.get("filtre_ecoles") == "SELECTION":
                valide = False
                for date_debut_scolarite, date_fin_scolarite in dict_scolarites.get(conso.individu, []):
                    if date_debut_scolarite <= conso.date <= date_fin_scolarite:
                        valide = True
                if not valide:
                    continue

            # Création des valeurs des colonnes
            key_individu = (conso.individu, conso.inscription.famille)

            def Memorise_valeur(code_colonne="", valeur=None, ajouter_valeur=None, valeur_defaut=None, conso=None):
                if valeur:
                    resultats[key_individu][code_colonne] = valeur
                for index, colonne in enumerate(colonnes):
                    if colonne["code"] == code_colonne:
                        # Vérifie si valide
                        valide = True
                        if conso and colonne.get("unites", None):
                            valide = False
                            for nom_unite in colonne["unites"].split(";"):
                                if conso.unite.nom.lower().strip() == nom_unite.lower().strip():
                                    valide = True

                        # Mémorisation de la valeur
                        if valide:
                            if ajouter_valeur:
                                resultats[key_individu].setdefault(index, valeur_defaut)
                                resultats[key_individu][index] += ajouter_valeur
                            else:
                                resultats[key_individu][index] = valeur

            if key_individu not in resultats:
                resultats[key_individu] = {}

                # Individu
                Memorise_valeur("individu_nom_complet", conso.individu.Get_nom())
                Memorise_valeur("individu_nom", conso.individu.nom)
                Memorise_valeur("individu_prenom", conso.individu.prenom)
                Memorise_valeur("individu_sexe", conso.individu.Get_sexe())
                Memorise_valeur("individu_date_naiss", utils_dates.ConvertDateToFR(str(conso.individu.date_naiss)))
                Memorise_valeur("individu_age", conso.individu.Get_age())
                Memorise_valeur("individu_adresse_complete", conso.individu.Get_adresse_complete())
                Memorise_valeur("individu_rue", conso.individu.rue_resid)
                Memorise_valeur("individu_cp", conso.individu.cp_resid)
                Memorise_valeur("individu_ville", conso.individu.ville_resid)

                # Famille
                Memorise_valeur("famille_nom_complet", conso.inscription.famille.nom)
                Memorise_valeur("famille_num_allocataire", conso.inscription.famille.num_allocataire)
                Memorise_valeur("famille_allocataire", conso.inscription.famille.allocataire.Get_nom() if conso.inscription.famille.allocataire else None)
                Memorise_valeur("famille_caisse", conso.inscription.famille.caisse.nom if conso.inscription.famille.caisse else None)
                Memorise_valeur("famille_qf", int(dict_quotients[conso.inscription.famille_id]) if conso.inscription.famille_id in dict_quotients else None)

                # Ajout des questionnaires
                for reponse in questionnaires_individus.GetDonnees(conso.individu_id):
                    Memorise_valeur("question_%d" % reponse["IDquestion"], reponse["reponse"])
                for reponse in questionnaires_familles.GetDonnees(conso.inscription.famille_id):
                    Memorise_valeur("question_%d" % reponse["IDquestion"], reponse["reponse"])

            # Recherche si date durant les vacances
            est_vacances = utils_dates.EstEnVacances(date=conso.date, liste_vacances=liste_vacances)
            for suffixe in ("", "_vacances", "_hors_vacances"):
                condition_suffixe = suffixe == "" or (suffixe == "_vacances" and est_vacances) or (suffixe == "_hors_vacances" and not est_vacances)

                # Nombre de conso
                code_colonne = "*nbre_conso" + suffixe
                if condition_suffixe:
                    Memorise_valeur(code_colonne, ajouter_valeur=1, valeur_defaut=0, conso=conso)

                # Durée réelle de la conso
                code_colonne = "*temps_conso" + suffixe
                if condition_suffixe and conso.heure_debut and conso.heure_fin:
                    valeur = datetime.timedelta(hours=conso.heure_fin.hour, minutes=conso.heure_fin.minute) - datetime.timedelta(hours=conso.heure_debut.hour, minutes=conso.heure_debut.minute)
                    Memorise_valeur(code_colonne, ajouter_valeur=valeur, valeur_defaut=datetime.timedelta(hours=0, minutes=0), conso=conso)

                # Temps facturé
                code_colonne = "*temps_facture" + suffixe
                if condition_suffixe and conso.prestation and conso.prestation.temps_facture:
                    Memorise_valeur(code_colonne, ajouter_valeur=conso.prestation.temps_facture, valeur_defaut=datetime.timedelta(hours=0, minutes=0), conso=conso)

                # Equivalence journées
                code_colonne = "*equiv_journees" + suffixe
                if condition_suffixe and conso.unite.equiv_journees:
                    Memorise_valeur(code_colonne, ajouter_valeur=conso.unite.equiv_journees, valeur_defaut=0.0, conso=conso)

                # Equivalence heures
                code_colonne = "*equiv_heures" + suffixe
                if condition_suffixe and conso.unite.equiv_heures:
                    Memorise_valeur(code_colonne, ajouter_valeur=utils_dates.TimeEnDelta(conso.unite.equiv_heures), valeur_defaut=datetime.timedelta(0), conso=conso)

        # Création des colonnes
        liste_colonnes = [colonne["nom"] for colonne in colonnes]

        # Création des lignes
        keys_individus = sorted(list(resultats.keys()), key=lambda x: str(resultats[x][parametres["tri"]]), reverse=parametres["ordre"]=="decroissant")

        liste_lignes = []
        for key_individu in keys_individus:
            ligne = []
            for index, colonne in enumerate(colonnes):
                valeur = resultats[key_individu].get(index, None)
                ligne.append(self.FormateValeur(valeur))
            liste_lignes.append(ligne)

        return liste_colonnes, liste_lignes

    def FormateValeur(self, valeur):
        if isinstance(valeur, datetime.timedelta):
            heures = (valeur.days*24) + (valeur.seconds/3600)
            minutes = valeur.seconds % 3600/60
            return "%dh%02d" % (heures, minutes)
        return valeur
