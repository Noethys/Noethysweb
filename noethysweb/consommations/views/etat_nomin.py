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
from core.models import Consommation, Vacance, Parametre, Quotient, Scolarite, Famille, Individu, Unite
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
        if not form.is_valid():
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

        consommations = Consommation.objects.values("date", "individu_id", "inscription__famille_id", "heure_debut", "heure_fin", "unite_id", "prestation__temps_facture").filter(conditions)

        # Importation des données diverses
        dict_familles = {famille.pk: famille for famille in Famille.objects.select_related("caisse", "allocataire").filter(pk__in=[conso["inscription__famille_id"] for conso in consommations])}
        dict_individus = {individu.pk: individu for individu in Individu.objects.filter(pk__in=[conso["individu_id"] for conso in consommations])}
        dict_unites = {unite.pk: unite for unite in Unite.objects.all()}

        # Importation des scolarités
        dict_scolarites = {}
        if parametres.get("filtre_ecoles") == "SELECTION":
            for scolarite in Scolarite.objects.filter(ecole_id__in=[int(idecole) for idecole in parametres["ecoles"]], date_debut__lte=date_max, date_fin__gte=date_min):
                dict_scolarites.setdefault(scolarite.individu_id, [])
                dict_scolarites[scolarite.individu_id].append((scolarite.date_debut, scolarite.date_fin))

        # Importation des vacances
        liste_vacances = Vacance.objects.filter(date_fin__gte=date_min, date_debut__lte=date_max)

        # Importation des QF
        conditions_qf = Q(famille__in=[conso["inscription__famille_id"] for conso in consommations]) & Q(date_debut__lte=date_max) & Q(date_fin__gte=date_min)
        dict_quotients = {quotient.famille_id: quotient.quotient for quotient in Quotient.objects.filter(conditions_qf)}

        # Importation des questionnaires
        questionnaires_individus = utils_questionnaires.ChampsEtReponses(categorie="individu", filtre_reponses=Q(individu_id__in=[conso["individu_id"] for conso in consommations]))
        questionnaires_familles = utils_questionnaires.ChampsEtReponses(categorie="famille", filtre_reponses=Q(famille_id__in=[conso["inscription__famille_id"] for conso in consommations]))

        # Récupération des colonnes
        colonnes = json.loads(parametres["colonnes"])

        # Calcul des données
        resultats = {}
        for conso in consommations:
            individu = dict_individus[conso["individu_id"]]
            famille = dict_familles[conso["inscription__famille_id"]]

            # Filtre ville (placé ici car crypté)
            if parametres.get("filtre_villes") == "SELECTION":
                if individu.ville_resid not in parametres["villes"]:
                    continue

            # Filtre écoles
            if parametres.get("filtre_ecoles") == "SELECTION":
                valide = False
                for date_debut_scolarite, date_fin_scolarite in dict_scolarites.get(individu.pk, []):
                    if date_debut_scolarite <= conso["date"] <= date_fin_scolarite:
                        valide = True
                if not valide:
                    continue

            # Création des valeurs des colonnes
            key_individu = (individu, famille)

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
                                if dict_unites[conso["unite_id"]].nom.lower().strip() == nom_unite.lower().strip():
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
                Memorise_valeur("individu_nom_complet", individu.Get_nom())
                Memorise_valeur("individu_nom", individu.nom)
                Memorise_valeur("individu_prenom", individu.prenom)
                Memorise_valeur("individu_sexe", individu.Get_sexe())
                Memorise_valeur("individu_date_naiss", utils_dates.ConvertDateToFR(str(individu.date_naiss)))
                Memorise_valeur("individu_age", individu.Get_age())
                Memorise_valeur("individu_adresse_complete", individu.Get_adresse_complete())
                Memorise_valeur("individu_rue", individu.rue_resid)
                Memorise_valeur("individu_cp", individu.cp_resid)
                Memorise_valeur("individu_ville", individu.ville_resid)

                # Famille
                Memorise_valeur("famille_nom_complet", famille.nom)
                Memorise_valeur("famille_num_allocataire", famille.num_allocataire)
                Memorise_valeur("famille_allocataire", famille.allocataire.Get_nom() if famille.allocataire else None)
                Memorise_valeur("famille_caisse", famille.caisse.nom if famille.caisse else None)
                Memorise_valeur("famille_qf", int(dict_quotients[famille.pk]) if famille.pk in dict_quotients and dict_quotients[famille.pk] else None)

                # Ajout des questionnaires
                for reponse in questionnaires_individus.GetDonnees(individu.pk):
                    Memorise_valeur("question_%d" % reponse["IDquestion"], reponse["reponse"])
                for reponse in questionnaires_familles.GetDonnees(famille.pk):
                    Memorise_valeur("question_%d" % reponse["IDquestion"], reponse["reponse"])

            # Recherche si date durant les vacances
            est_vacances = utils_dates.EstEnVacances(date=conso["date"], liste_vacances=liste_vacances)
            for suffixe in ("", "_vacances", "_hors_vacances"):
                condition_suffixe = suffixe == "" or (suffixe == "_vacances" and est_vacances) or (suffixe == "_hors_vacances" and not est_vacances)

                # Nombre de conso
                code_colonne = "*nbre_conso" + suffixe
                if condition_suffixe:
                    Memorise_valeur(code_colonne, ajouter_valeur=1, valeur_defaut=0, conso=conso)

                # Durée réelle de la conso
                code_colonne = "*temps_conso" + suffixe
                if condition_suffixe and conso["heure_debut"] and conso["heure_fin"]:
                    valeur = datetime.timedelta(hours=conso["heure_fin"].hour, minutes=conso["heure_fin"].minute) - datetime.timedelta(hours=conso["heure_debut"].hour, minutes=conso["heure_debut"].minute)
                    Memorise_valeur(code_colonne, ajouter_valeur=valeur, valeur_defaut=datetime.timedelta(hours=0, minutes=0), conso=conso)

                # Temps facturé
                code_colonne = "*temps_facture" + suffixe
                if condition_suffixe and conso["prestation__temps_facture"]:
                    Memorise_valeur(code_colonne, ajouter_valeur=conso["prestation__temps_facture"], valeur_defaut=datetime.timedelta(hours=0, minutes=0), conso=conso)

                # Equivalence journées
                code_colonne = "*equiv_journees" + suffixe
                if condition_suffixe and dict_unites[conso["unite_id"]].equiv_journees:
                    Memorise_valeur(code_colonne, ajouter_valeur=dict_unites[conso["unite_id"]].equiv_journees, valeur_defaut=0.0, conso=conso)

                # Equivalence heures
                code_colonne = "*equiv_heures" + suffixe
                if condition_suffixe and dict_unites[conso["unite_id"]].equiv_heures:
                    Memorise_valeur(code_colonne, ajouter_valeur=utils_dates.TimeEnDelta(dict_unites[conso["unite_id"]].equiv_heures), valeur_defaut=datetime.timedelta(0), conso=conso)

        # Création des colonnes
        liste_colonnes = [colonne["nom"] for colonne in colonnes]

        # Création des lignes
        keys_individus = sorted(list(resultats.keys()), key=lambda x: str(resultats[x].get(parametres["tri"], None)), reverse=parametres["ordre"]=="decroissant")

        liste_lignes = []
        for key_individu in keys_individus:
            ligne = []
            for index, colonne in enumerate(colonnes):
                valeur = resultats[key_individu].get(index, None)
                ligne.append(self.FormateValeur(valeur, mode=parametres.get("format_durees", "horaire")))
            liste_lignes.append(ligne)

        return liste_colonnes, liste_lignes

    def FormateValeur(self, valeur, mode="horaire"):
        if isinstance(valeur, datetime.timedelta):
            heures = (valeur.days*24) + (valeur.seconds//3600)
            minutes = valeur.seconds % 3600/60
            if mode == "decimal":
                minDecimal = int(int(minutes) * 100 / 60)
                return float("%s.%s" % (heures, minDecimal))
            return "%dh%02d" % (heures, minutes)
        return valeur
