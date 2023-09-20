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
from core.models import Consommation, Vacance, Parametre, Quotient
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
            context['form_parametres'] = Formulaire(request=self.request);print(1)

        # Application du profil de configuration
        profil = Parametre.objects.filter(idparametre=int(self.request.POST.get("profil"))).first() if self.request.POST.get("profil") else False
        if profil and self.request.POST.get("application_profil"):
            request_post = self.request.POST.copy()
            request_post["profil"] = profil.pk
            initial_data = json.loads(profil.parametre)
            [request_post.pop(key) for key in initial_data.keys() if key in request_post]
            request_post.update(initial_data)
            context['form_parametres'] = Formulaire(initial=request_post, request=self.request);print(2)

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

        # Importation des vacances
        liste_vacances = Vacance.objects.filter(date_fin__gte=date_min, date_debut__lte=date_max)

        # Importation des QF
        conditions_qf = Q(famille__in=[conso.inscription.famille for conso in consommations]) & Q(date_debut__lte=date_max) & Q(date_fin__gte=date_min)
        dict_quotients = {quotient.famille_id: quotient.quotient for quotient in Quotient.objects.filter(conditions_qf)}

        # Importation des questionnaires
        questionnaires_individus = utils_questionnaires.ChampsEtReponses(categorie="individu", filtre_reponses=Q(individu__in=[conso.inscription.individu for conso in consommations]))
        questionnaires_familles = utils_questionnaires.ChampsEtReponses(categorie="famille", filtre_reponses=Q(famille__in=[conso.inscription.famille for conso in consommations]))

        # Calcul des données
        resultats = {}
        for conso in consommations:

            # Filtre ville (placé ici car crypté)
            if parametres.get("filtre_villes") == "SELECTION":
                if conso.individu.ville_resid not in parametres["villes"]:
                    continue

            key_individu = (conso.individu, conso.inscription.famille)
            if key_individu not in resultats:
                resultats[key_individu] = {}

                # Individu
                resultats[key_individu]["individu_nom_complet"] = conso.individu.Get_nom()
                resultats[key_individu]["individu_nom"] = conso.individu.nom
                resultats[key_individu]["individu_prenom"] = conso.individu.prenom
                resultats[key_individu]["individu_sexe"] = conso.individu.Get_sexe()
                resultats[key_individu]["individu_date_naiss"] = utils_dates.ConvertDateToFR(str(conso.individu.date_naiss))
                resultats[key_individu]["individu_age"] = conso.individu.Get_age()
                resultats[key_individu]["individu_adresse_complete"] = conso.individu.Get_adresse_complete()
                resultats[key_individu]["individu_rue"] = conso.individu.rue_resid
                resultats[key_individu]["individu_cp"] = conso.individu.cp_resid
                resultats[key_individu]["individu_ville"] = conso.individu.ville_resid

                # Famille
                resultats[key_individu]["famille_nom_complet"] = conso.inscription.famille.nom
                resultats[key_individu]["famille_num_allocataire"] = conso.inscription.famille.num_allocataire
                resultats[key_individu]["famille_allocataire"] = conso.inscription.famille.allocataire.Get_nom() if conso.inscription.famille.allocataire else None
                resultats[key_individu]["famille_caisse"] = conso.inscription.famille.caisse.nom if conso.inscription.famille.caisse else None
                resultats[key_individu]["famille_qf"] = int(dict_quotients.get(conso.inscription.famille_id, 0))

                # Ajout des questionnaires
                for reponse in questionnaires_individus.GetDonnees(conso.individu_id):
                    resultats[key_individu]["question_%d" % reponse["IDquestion"]] = reponse["reponse"]
                for reponse in questionnaires_familles.GetDonnees(conso.inscription.famille_id):
                    resultats[key_individu]["question_%d" % reponse["IDquestion"]] = reponse["reponse"]

            # Recherche si date durant les vacances
            est_vacances = utils_dates.EstEnVacances(date=conso.date, liste_vacances=liste_vacances)
            for suffixe in ("", "_vacances", "_hors_vacances"):
                condition_suffixe = suffixe == "" or (suffixe == "_vacances" and est_vacances) or (suffixe == "_hors_vacances" and not est_vacances)

                # Nombre de conso
                resultats[key_individu].setdefault("nbre_conso" + suffixe, 0)
                if condition_suffixe:
                    resultats[key_individu]["nbre_conso" + suffixe] += 1

                # Durée réelle de la conso
                resultats[key_individu].setdefault("temps_conso" + suffixe, datetime.timedelta(hours=0, minutes=0))
                if condition_suffixe and conso.heure_debut and conso.heure_fin:
                    valeur = datetime.timedelta(hours=conso.heure_fin.hour, minutes=conso.heure_fin.minute) - datetime.timedelta(hours=conso.heure_debut.hour, minutes=conso.heure_debut.minute)
                    resultats[key_individu]["temps_conso" + suffixe] += valeur

                # Equivalence journées
                resultats[key_individu].setdefault("equiv_journees" + suffixe, 0.0)
                if condition_suffixe and conso.unite.equiv_journees:
                    resultats[key_individu]["equiv_journees" + suffixe] += conso.unite.equiv_journees

                # Equivalence heures
                resultats[key_individu].setdefault("equiv_heures" + suffixe, datetime.timedelta(0))
                if condition_suffixe and conso.unite.equiv_heures:
                    resultats[key_individu]["equiv_heures" + suffixe] += utils_dates.TimeEnDelta(conso.unite.equiv_heures)

        # Création des colonnes
        colonnes = json.loads(parametres["colonnes"])
        liste_colonnes = [colonne["nom"] for colonne in colonnes]

        # Création des lignes
        keys_individus = sorted(list(resultats.keys()), key=lambda x: x[0].Get_nom())

        liste_lignes = []
        for key_individu in keys_individus:
            ligne = []
            for colonne in colonnes:
                valeur = resultats[key_individu].get(colonne["code"], None)
                ligne.append(self.FormateValeur(valeur))
            liste_lignes.append(ligne)

        return liste_colonnes, liste_lignes

    def FormateValeur(self, valeur):
        if isinstance(valeur, datetime.timedelta):
            heures = (valeur.days*24) + (valeur.seconds/3600)
            minutes = valeur.seconds % 3600/60
            return "%dh%02d" % (heures, minutes)
        return valeur
