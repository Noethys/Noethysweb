# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime, decimal
from django.http import JsonResponse, QueryDict
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.base import CustomView
from core.utils import utils_dates
from types import SimpleNamespace
from django.db.models import Sum
from core.models import Consommation, Vacance, Parametre, Quotient, Scolarite, Famille, Individu, Unite, Activite, TypeGroupeActivite, Groupe, Caisse, Ecole, \
    Rattachement, Inscription, Information, Ventilation, Deduction
from consommations.utils import utils_frequentation_caf
from core.utils import utils_questionnaires
from consommations.forms.etat_nomin import Formulaire
from consommations.utils import utils_etat_nomin


ETATS_PRESENCE = ("reservation", "present")
ETATS_ABSENCE = ("absentj", "absenti")
CODES_ABSENCES = ("*nbre_absences", "*nbre_absentj", "*nbre_absenti")
CODES_FACTURATION = ("*montant_regle", "*reste_du", "*montant_deductions")
LABELS_REGROUPEMENTS = {"activite": "Activité non renseignée", "ecole": "Sans école", "ville": "Ville non renseignée", "caisse": "Sans caisse"}


def get_data_profil(donnees=None, request=None):
    """ Récupère les données à sauvegarder dans le profil de configuration """
    form = Formulaire(QueryDict(donnees), request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": ["<b>%s</b> : %s " % (form.fields[field_name].label, erreur[0].message) for field_name, erreur in form.errors.as_data().items()]}, status=401)

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
            context['afficher_resultats'] = False

        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))

        resultats = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "liste_colonnes": resultats["colonnes"],
            "liste_colonnes_json": json.dumps(resultats["colonnes"]),
            "liste_lignes": json.dumps(resultats["lignes"]),
            "kpis": resultats["kpis"],
            "est_regroupe": resultats["est_regroupe"],
            "nbre_lignes": len([ligne for ligne in resultats["lignes"] if not ligne.get("regroupement")]),
            "erreurs_colonnes": resultats["erreurs"],
            "resume_parametres": self.Get_resume_parametres(form.cleaned_data),
            "afficher_resultats": "type_submit" in request.POST,
            "titre": form.cleaned_data.get("titre", "Etat nominatif"),
            "date_calcul": datetime.datetime.now(),
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resume_parametres(self, parametres={}):
        """ Rappel des paramètres affiché quand aucun individu ne correspond """
        def Liste_noms(noms=[]):
            noms = sorted(noms)
            return ", ".join(noms[:3]) + (" et %d autre%s" % (len(noms) - 3, "s" if len(noms) > 4 else "") if len(noms) > 3 else "") if noms else "Aucune"

        resume = []
        date_min, date_max = [utils_dates.ConvertDateENGtoDate(date) for date in parametres["periode"].split(";")]
        resume.append(("Période", "du %s au %s" % (date_min.strftime("%d/%m/%Y"), date_max.strftime("%d/%m/%Y"))))
        param_activites = json.loads(parametres["activites"])
        modeles = {"activites": (Activite, "Activités"), "groupes_activites": (TypeGroupeActivite, "Groupes d'activités"), "groupes": (Groupe, "Groupes")}
        if param_activites["type"] in modeles:
            modele, label = modeles[param_activites["type"]]
            resume.append((label, Liste_noms([objet.nom for objet in modele.objects.filter(pk__in=param_activites["ids"])])))
        else:
            resume.append(("Activités", "Toutes les activités"))
        labels_etats = dict(Formulaire.base_fields["etats"].choices)
        resume.append(("États", ", ".join([labels_etats.get(etat, etat) for etat in parametres["etats"]])))
        if parametres.get("filtre_villes") == "SELECTION":
            resume.append(("Villes", Liste_noms(parametres["villes"])))
        if parametres.get("filtre_caisses") == "SELECTION":
            resume.append(("Caisses", Liste_noms([caisse.nom for caisse in Caisse.objects.filter(pk__in=parametres["caisses"])])))
        if parametres.get("filtre_ecoles") == "SELECTION":
            resume.append(("Écoles", Liste_noms([ecole.nom for ecole in Ecole.objects.filter(pk__in=parametres["ecoles"])])))
        return resume

    def Get_condition_activites(self, param_activites={}):
        condition = Q(activite__structure__in=self.request.user.structures.all())
        if param_activites["type"] == "groupes_activites":
            return condition & Q(activite__groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            return condition & Q(activite__in=param_activites["ids"])
        if param_activites["type"] == "groupes":
            return condition & Q(groupe__in=param_activites["ids"])
        return condition

    def Get_resultats(self, parametres={}):
        # Période et activités
        date_min = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_max = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
        conditions = Q(date__gte=date_min) & Q(date__lte=date_max) & self.Get_condition_activites(json.loads(parametres["activites"]))

        # Colonnes
        dict_champs = utils_etat_nomin.Get_dict_champs(self.request.user)
        colonnes = [colonne for colonne in utils_etat_nomin.Normaliser_colonnes(json.loads(parametres.get("colonnes") or "[]")) if colonne["code"] in dict_champs]
        codes_colonnes = {colonne["code"] for colonne in colonnes}

        def Get_type_colonne(index):
            colonne = colonnes[index]
            return utils_etat_nomin.FORMATS_CALCUL[colonne["format"]] if colonne["code"] == "calcul" else dict_champs[colonne["code"]]["type"]

        def Get_total_colonne(index):
            colonne = colonnes[index]
            return utils_etat_nomin.TOTAUX_CALCUL[colonne["total"]] if colonne["code"] == "calcul" else dict_champs[colonne["code"]]["total"]

        def Get_titre_colonne(index):
            return colonnes[index]["nom"] or dict_champs[colonnes[index]["code"]]["label"]

        # Colonnes calculées : analyse des formules
        titres_colonnes = {}
        for index in range(len(colonnes)):
            titres_colonnes.setdefault(Get_titre_colonne(index).strip().lower(), index)
        formules, erreurs = {}, []
        for index, colonne in enumerate(colonnes):
            if colonne["code"] == "calcul":
                try:
                    formules[index] = utils_etat_nomin.Formule_colonne(colonne["formule"], titres_colonnes)
                except utils_etat_nomin.Erreur_formule as erreur:
                    erreurs.append("Colonne « %s » : %s." % (Get_titre_colonne(index), erreur))

        # Les formules qui dépendent l'une de l'autre en boucle ne sont pas calculées
        def Est_circulaire(index, chemin=()):
            if index in chemin:
                return True
            return any(Est_circulaire(reference, chemin + (index,)) for reference in formules.get(index).references if reference in formules) if index in formules else False
        for index in [index for index in formules if Est_circulaire(index)]:
            erreurs.append("Colonne « %s » : la formule fait référence à elle-même (directement ou par une autre colonne)." % Get_titre_colonne(index))
            formules.pop(index)

        def Appliquer_calculs(ligne):
            cache = {}
            def Valeur(index):
                if index in formules:
                    if index not in cache:
                        cache[index] = formules[index].Calculer({reference: Valeur(reference) for reference in formules[index].references})
                    return cache[index]
                valeur = ligne.get(str(index))
                # Dans les formules, les durées valent des heures
                if Get_type_colonne(index) == "duree" and isinstance(valeur, (int, float)):
                    return valeur / 60
                return valeur
            for index in formules:
                resultat = Valeur(index)
                if isinstance(resultat, (int, float)):
                    resultat = round(resultat * 60, 2) if Get_type_colonne(index) == "duree" else round(resultat, 4)
                ligne[str(index)] = resultat
        regroupement = parametres.get("regroupement") or "aucun"

        # Etats : les absences sont toujours importées si une colonne d'absences est demandée
        etats = set(parametres["etats"])
        etats_requete = etats | (set(ETATS_ABSENCE) if codes_colonnes & set(CODES_ABSENCES) else set())
        etats_requete |= {"reservation"} if "*reservations_non_pointees" in codes_colonnes else set()
        etats_requete |= {"attente"} if "*jours_attente" in codes_colonnes else set()
        conditions &= Q(etat__in=etats_requete)
        if parametres.get("filtre_caisses") == "SELECTION":
            conditions &= Q(inscription__famille__caisse_id__in=[int(idcaisse) for idcaisse in parametres["caisses"]])

        consommations = list(Consommation.objects.values("date", "etat", "individu_id", "inscription__famille_id", "heure_debut", "heure_fin", "unite_id",
                                                         "activite_id", "activite__nom", "groupe__nom", "prestation_id", "prestation__temps_facture",
                                                         "prestation__montant", "quantite", "inscription_id", "evenement_id", "evenement__equiv_heures").filter(conditions).exclude(individu__isnull=True).exclude(inscription__famille__isnull=True))

        # Importation des données diverses
        dict_familles = {famille.pk: famille for famille in Famille.objects.select_related("caisse__regime", "allocataire", "secteur").filter(pk__in={conso["inscription__famille_id"] for conso in consommations})}
        dict_individus = {individu.pk: individu for individu in Individu.objects.select_related("secteur").filter(pk__in={conso["individu_id"] for conso in consommations})}
        dict_unites = {unite.pk: unite for unite in Unite.objects.all()}
        liste_vacances = Vacance.objects.filter(date_fin__gte=date_min, date_debut__lte=date_max)

        # Scolarités (triées par date de début : la dernière est la plus récente)
        dict_scolarites = {}
        for scolarite in Scolarite.objects.select_related("ecole", "classe", "niveau").filter(individu__in=dict_individus.keys(), date_debut__lte=date_max, date_fin__gte=date_min).order_by("date_debut"):
            dict_scolarites.setdefault(scolarite.individu_id, []).append(scolarite)
        ecoles_filtre = [int(idecole) for idecole in parametres["ecoles"]] if parametres.get("filtre_ecoles") == "SELECTION" else None

        # Quotients familiaux (le plus récent de la période l'emporte)
        dict_quotients = {}
        for quotient in Quotient.objects.filter(famille__in=dict_familles.keys(), date_debut__lte=date_max, date_fin__gte=date_min).order_by("date_debut"):
            dict_quotients[quotient.famille_id] = quotient.quotient

        # Titulaires des familles (colonnes de contact)
        dict_titulaires = {}
        if codes_colonnes & {"contact_tel_titulaires", "contact_mail_titulaires"}:
            for rattachement in Rattachement.objects.select_related("individu").filter(famille__in=dict_familles.keys(), titulaire=True).order_by("individu__nom", "individu__prenom"):
                dict_titulaires.setdefault(rattachement.famille_id, []).append(rattachement.individu)

        # Inscriptions
        dict_inscriptions = {}
        if codes_colonnes & {"inscription_groupe", "inscription_categorie_tarif", "inscription_date"}:
            dict_inscriptions = {inscription.pk: inscription for inscription in Inscription.objects.select_related("groupe", "categorie_tarif").filter(pk__in={conso["inscription_id"] for conso in consommations})}

        # Santé (les colonnes ne sont présentes que si l'utilisateur a la permission)
        dict_regimes, dict_informations = {}, {}
        if "sante_regimes" in codes_colonnes:
            for individu in Individu.objects.prefetch_related("regimes_alimentaires").filter(pk__in=dict_individus.keys()):
                dict_regimes[individu.pk] = ", ".join(sorted(regime.nom for regime in individu.regimes_alimentaires.all()))
        if "sante_informations" in codes_colonnes:
            conditions_infos = Q(individu__in=dict_individus.keys(), diffusion_listing_conso=True) & (Q(date_debut__lte=date_max) | Q(date_debut__isnull=True)) & (Q(date_fin__gte=date_min) | Q(date_fin__isnull=True))
            for information in Information.objects.select_related("categorie").filter(conditions_infos).order_by("categorie__nom"):
                dict_informations.setdefault(information.individu_id, []).append("%s : %s" % (information.categorie.nom, information.intitule))

        # Règles de calcul des profils de l'état global
        regles_etat_global = {}
        for index, colonne in enumerate(colonnes):
            if colonne["code"] != "*heures_etat_global":
                continue
            conditions_profil = Q(categorie="profil_etat_global") & (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
            profil = Parametre.objects.filter(conditions_profil, pk=colonne.get("profil") or 0).first()
            if not profil:
                erreurs.append("Colonne « %s » : choisissez un profil de l'état global." % Get_titre_colonne(index))
                continue
            try:
                regles_etat_global[index] = utils_etat_nomin.Preparer_regles_etat_global(profil)
            except (utils_frequentation_caf.Erreur_parametres, ValueError, KeyError) as erreur:
                erreurs.append("Colonne « %s » : le profil « %s » contient une règle non valide (%s)." % (Get_titre_colonne(index), profil.nom, erreur))
        calcul_etat_global = utils_frequentation_caf.Calcul({})
        dict_unites_formule = {}
        if any(regle["type"] == "3" for regles in regles_etat_global.values() for regle in regles["unites"].values()):
            for conso in Consommation.objects.values("date", "inscription_id", "unite_id", "heure_debut", "heure_fin", "etat", "quantite").filter(date__gte=date_min, date__lte=date_max, inscription_id__in={c["inscription_id"] for c in consommations}):
                dict_unites_formule[(conso["date"], conso["inscription_id"], conso["unite_id"])] = utils_frequentation_caf.Unite_conso(conso["unite_id"], conso["heure_debut"], conso["heure_fin"], conso["etat"], conso["quantite"])
        temps_journalier, erreurs_formules = {}, set()
        aujourdhui = datetime.date.today()

        # Questionnaires
        questionnaires_individus = utils_questionnaires.ChampsEtReponses(categorie="individu", filtre_reponses=Q(individu_id__in=dict_individus.keys()))
        questionnaires_familles = utils_questionnaires.ChampsEtReponses(categorie="famille", filtre_reponses=Q(famille_id__in=dict_familles.keys()))

        # Filtres sur les villes et les écoles
        def Est_valide(conso):
            individu = dict_individus[conso["individu_id"]]
            if parametres.get("filtre_villes") == "SELECTION" and individu.ville_resid not in parametres["villes"]:
                return False
            if ecoles_filtre is not None:
                if not [s for s in dict_scolarites.get(individu.pk, []) if s.ecole_id in ecoles_filtre and s.date_debut <= conso["date"] <= s.date_fin]:
                    return False
            return True

        consommations = [conso for conso in consommations if Est_valide(conso)]

        def Get_key(conso):
            return (conso["individu_id"], conso["inscription__famille_id"], conso["activite_id"] if regroupement == "activite" else None)

        # Une ligne n'est créée que pour un individu ayant au moins une consommation dans les états cochés
        keys_valides = {Get_key(conso) for conso in consommations if conso["etat"] in etats}

        # Unités filtrées par colonne
        unites_colonnes = {index: {nom.lower().strip() for nom in colonne["unites"]} for index, colonne in enumerate(colonnes)}

        def Get_age(date_naiss=None, date=None):
            if not date_naiss:
                return None
            return date.year - date_naiss.year - ((date.month, date.day) < (date_naiss.month, date_naiss.day))

        def Get_infos(individu, famille, activite_nom):
            scolarite = dict_scolarites.get(individu.pk, [None])[-1]
            infos = {
                "individu_nom_complet": individu.Get_nom(), "individu_nom": individu.nom, "individu_prenom": individu.prenom,
                "individu_sexe": individu.Get_sexe(), "individu_date_naiss": individu.date_naiss, "individu_age": individu.Get_age(),
                "individu_adresse_complete": individu.Get_adresse_complete(), "individu_rue": individu.rue_resid,
                "individu_cp": individu.cp_resid, "individu_ville": individu.ville_resid,
                "famille_nom_complet": famille.nom, "famille_num_allocataire": famille.num_allocataire,
                "famille_allocataire": famille.allocataire.Get_nom() if famille.allocataire else None,
                "famille_caisse": famille.caisse.nom if famille.caisse else None,
                "famille_qf": int(dict_quotients[famille.pk]) if dict_quotients.get(famille.pk) is not None else None,
                "individu_ecole": scolarite.ecole.nom if scolarite else None,
                "individu_classe": scolarite.classe.nom if scolarite and scolarite.classe else None,
                "individu_niveau": scolarite.niveau.nom if scolarite and scolarite.niveau else None,
                "individu_secteur": individu.secteur.nom if individu.secteur else None,
                "individu_tel_mobile": individu.tel_mobile,
                "individu_age_debut": Get_age(individu.date_naiss, date_min),
                "individu_tranche_age": utils_etat_nomin.Get_tranche_age(Get_age(individu.date_naiss, date_min)),
                "famille_regime": famille.caisse.regime.nom if famille.caisse and famille.caisse.regime else None,
                "famille_secteur": famille.secteur.nom if famille.secteur else None,
                "contact_tel_titulaires": " · ".join(filter(None, ["%s : %s" % (titulaire.prenom or titulaire.nom, " / ".join(filter(None, [titulaire.tel_mobile, titulaire.tel_domicile])))
                                                                   for titulaire in dict_titulaires.get(famille.pk, []) if titulaire.tel_mobile or titulaire.tel_domicile])) or None,
                "contact_mail_titulaires": ", ".join(filter(None, [titulaire.mail for titulaire in dict_titulaires.get(famille.pk, [])])) or None,
                "sante_regimes": dict_regimes.get(individu.pk) or None,
                "sante_informations": " · ".join(dict_informations.get(individu.pk, [])) or None,
                "_activite": activite_nom,
            }
            for reponse in questionnaires_individus.GetDonnees(individu.pk) + questionnaires_familles.GetDonnees(famille.pk):
                infos["question_%d" % reponse["IDquestion"]] = reponse["reponse"]
            return infos

        # Calcul des données
        resultats = {}
        montants_prestations = {}
        kpi_individus, kpi_familles, kpi_jours = set(), set(), set()
        kpi_conso, kpi_conso_vacances = 0, 0
        for conso in consommations:
            key = Get_key(conso)
            if key not in keys_valides:
                continue

            if key not in resultats:
                resultats[key] = {"infos": Get_infos(dict_individus[key[0]], dict_familles[key[1]], conso["activite__nom"]),
                                  "valeurs": {}, "ensembles": {}, "activites": set(), "groupes": set(), "inscriptions": set()}
            ligne = resultats[key]
            est_vacances = utils_dates.EstEnVacances(date=conso["date"], liste_vacances=liste_vacances)
            dans_etats = conso["etat"] in etats
            unite = dict_unites.get(conso["unite_id"])

            # Indicateurs généraux
            if dans_etats:
                ligne["activites"].add(conso["activite__nom"] or "")
                ligne["inscriptions"].add(conso["inscription_id"])
                if conso["groupe__nom"]:
                    ligne["groupes"].add(conso["groupe__nom"])
                kpi_individus.add(key[0])
                kpi_familles.add(key[1])
                kpi_conso += 1
                kpi_conso_vacances += 1 if est_vacances else 0
                if conso["etat"] in ETATS_PRESENCE:
                    kpi_jours.add((key[0], conso["date"]))

            # Colonnes de mesures
            for index, colonne in enumerate(colonnes):
                code = colonne["code"]
                if not code.startswith("*"):
                    continue
                valeurs, ensembles = ligne["valeurs"], ligne["ensembles"]
                valeurs.setdefault(index, None if dict_champs[code]["type"] == "date" else 0)
                if colonne["jours"] and conso["date"].weekday() not in colonne["jours"]:
                    continue
                if colonne["periode"] == "vacances" and not est_vacances:
                    continue
                if colonne["periode"] == "hors_vacances" and est_vacances:
                    continue
                if unites_colonnes[index] and (not unite or unite.nom.lower().strip() not in unites_colonnes[index]):
                    continue

                if code == "*nbre_absences" and conso["etat"] in ETATS_ABSENCE:
                    valeurs[index] += 1
                elif code == "*nbre_absentj" and conso["etat"] == "absentj":
                    valeurs[index] += 1
                elif code == "*nbre_absenti" and conso["etat"] == "absenti":
                    valeurs[index] += 1
                elif code == "*reservations_non_pointees" and conso["etat"] == "reservation" and conso["date"] < aujourdhui:
                    valeurs[index] += 1
                elif code == "*jours_attente" and conso["etat"] == "attente":
                    ensembles.setdefault(index, set()).add(conso["date"])
                    valeurs[index] = len(ensembles[index])
                elif not dans_etats:
                    continue
                elif code in ("*premiere_date", "*derniere_date") and conso["etat"] in ETATS_PRESENCE:
                    if valeurs[index] is None or (conso["date"] < valeurs[index] if code == "*premiere_date" else conso["date"] > valeurs[index]):
                        valeurs[index] = conso["date"]
                elif code in CODES_FACTURATION and conso["prestation_id"]:
                    # Calculé après la boucle à partir des prestations distinctes
                    ensembles.setdefault(index, set()).add(conso["prestation_id"])
                    montants_prestations[conso["prestation_id"]] = conso["prestation__montant"] or 0
                elif code == "*heures_etat_global" and index in regles_etat_global:
                    regles = regles_etat_global[index]
                    regle = regles["unites"].get(conso["unite_id"])
                    if not regle:
                        continue
                    objet_conso = SimpleNamespace(date=conso["date"], heure_debut=conso["heure_debut"], heure_fin=conso["heure_fin"], inscription_id=conso["inscription_id"],
                                                  prestation_id=conso["prestation_id"], prestation=SimpleNamespace(temps_facture=conso["prestation__temps_facture"]),
                                                  unite=unite, evenement_id=conso["evenement_id"], evenement=SimpleNamespace(equiv_heures=conso["evenement__equiv_heures"]))
                    try:
                        valeur = calcul_etat_global.Calculer_valeur(objet_conso, regle, ensembles.setdefault(index, set()), dict_unites_formule) * (conso["quantite"] or 1)
                    except utils_frequentation_caf.Erreur_parametres as erreur:
                        erreurs_formules.add("Colonne « %s » : %s" % (Get_titre_colonne(index), erreur))
                        continue
                    # Plafond journalier par individu du profil
                    if regles["plafond_journalier"] > 0:
                        plafond = datetime.timedelta(minutes=regles["plafond_journalier"])
                        deja = temps_journalier.get((index, key[0], conso["date"]), datetime.timedelta(0))
                        valeur = max(min(valeur, plafond - deja), datetime.timedelta(0))
                        temps_journalier[(index, key[0], conso["date"])] = deja + valeur
                    valeurs[index] += valeur.total_seconds() / 60
                elif code == "*nbre_conso":
                    valeurs[index] += 1
                elif code == "*jours_presence" and conso["etat"] in ETATS_PRESENCE:
                    ensembles.setdefault(index, set()).add(conso["date"])
                    valeurs[index] = len(ensembles[index])
                elif code == "*temps_conso" and conso["heure_debut"] and conso["heure_fin"]:
                    valeurs[index] += (conso["heure_fin"].hour * 60 + conso["heure_fin"].minute) - (conso["heure_debut"].hour * 60 + conso["heure_debut"].minute)
                elif code in ("*temps_facture", "*montant_facture") and conso["prestation_id"]:
                    # Une prestation peut être associée à plusieurs consommations : elle n'est comptée qu'une fois
                    deja_comptees = ensembles.setdefault(index, set())
                    if conso["prestation_id"] in deja_comptees:
                        continue
                    deja_comptees.add(conso["prestation_id"])
                    if code == "*temps_facture" and conso["prestation__temps_facture"]:
                        valeurs[index] += conso["prestation__temps_facture"].total_seconds() / 60
                    if code == "*montant_facture" and conso["prestation__montant"]:
                        valeurs[index] += conso["prestation__montant"]
                elif code == "*equiv_journees" and unite and unite.equiv_journees:
                    valeurs[index] += unite.equiv_journees
                elif code == "*equiv_heures" and unite and unite.equiv_heures:
                    valeurs[index] += unite.equiv_heures.hour * 60 + unite.equiv_heures.minute

        erreurs.extend(sorted(erreurs_formules))

        # Facturation : montants réglés et déductions des prestations distinctes
        if codes_colonnes & set(CODES_FACTURATION):
            ventilations = dict(Ventilation.objects.filter(prestation_id__in=montants_prestations.keys()).values_list("prestation_id").annotate(total=Sum("montant")))
            deductions = dict(Deduction.objects.filter(prestation_id__in=montants_prestations.keys()).values_list("prestation_id").annotate(total=Sum("montant")))
            for ligne in resultats.values():
                for index, colonne in enumerate(colonnes):
                    if colonne["code"] in CODES_FACTURATION:
                        prestations = ligne["ensembles"].get(index, set())
                        if colonne["code"] == "*montant_regle":
                            ligne["valeurs"][index] = sum(ventilations.get(idprestation) or 0 for idprestation in prestations)
                        elif colonne["code"] == "*reste_du":
                            ligne["valeurs"][index] = sum((montants_prestations[idprestation] or 0) - (ventilations.get(idprestation) or 0) for idprestation in prestations)
                        else:
                            ligne["valeurs"][index] = sum(deductions.get(idprestation) or 0 for idprestation in prestations)

        # Nombre d'individus de chaque famille présents dans la liste
        individus_familles = {}
        for (idindividu, idfamille, idactivite) in resultats.keys():
            individus_familles.setdefault(idfamille, set()).add(idindividu)

        # Tri des lignes
        def Get_valeur_tri(key):
            valeur = resultats[key]["infos"].get(parametres.get("tri") or "individu_nom_complet")
            if isinstance(valeur, str):
                return valeur.lower().strip()
            return valeur

        def Trier(keys):
            avec_valeur = [key for key in keys if Get_valeur_tri(key) not in (None, "")]
            sans_valeur = [key for key in keys if Get_valeur_tri(key) in (None, "")]
            avec_valeur.sort(key=lambda key: resultats[key]["infos"]["individu_nom_complet"].lower())
            try:
                avec_valeur.sort(key=Get_valeur_tri, reverse=parametres.get("ordre") == "decroissant")
            except TypeError:
                avec_valeur.sort(key=lambda key: str(Get_valeur_tri(key)), reverse=parametres.get("ordre") == "decroissant")
            sans_valeur.sort(key=lambda key: resultats[key]["infos"]["individu_nom_complet"].lower())
            return avec_valeur + sans_valeur

        # Création des lignes
        def Get_ligne(key):
            ligne = {}
            for index, colonne in enumerate(colonnes):
                code, type_valeur = colonne["code"], Get_type_colonne(index)
                if code == "calcul":
                    valeur = None
                elif code.startswith("*"):
                    valeur = resultats[key]["valeurs"].get(index, 0)
                elif code == "conso_activites":
                    valeur = ", ".join(sorted(resultats[key]["activites"]))
                elif code == "conso_groupes":
                    valeur = ", ".join(sorted(resultats[key]["groupes"]))
                elif code == "famille_nbre_enfants":
                    valeur = len(individus_familles.get(key[1], []))
                elif code in ("inscription_groupe", "inscription_categorie_tarif", "inscription_date"):
                    inscriptions = [dict_inscriptions[idinscription] for idinscription in resultats[key]["inscriptions"] if idinscription in dict_inscriptions]
                    if code == "inscription_date":
                        valeur = min([inscription.date_debut for inscription in inscriptions], default=None)
                    elif code == "inscription_groupe":
                        valeur = ", ".join(sorted({inscription.groupe.nom for inscription in inscriptions if inscription.groupe}))
                    else:
                        valeur = ", ".join(sorted({inscription.categorie_tarif.nom for inscription in inscriptions if inscription.categorie_tarif}))
                else:
                    valeur = resultats[key]["infos"].get(code)
                ligne[str(index)] = self.Formate_valeur(valeur, type_valeur)
            Appliquer_calculs(ligne)
            return ligne

        def Get_label_groupe(key):
            infos = resultats[key]["infos"]
            valeur = {"activite": infos["_activite"], "ecole": infos["individu_ecole"], "ville": infos["individu_ville"], "caisse": infos["famille_caisse"]}.get(regroupement)
            return valeur or LABELS_REGROUPEMENTS.get(regroupement, "")

        lignes = []
        if regroupement in LABELS_REGROUPEMENTS:
            groupes = {}
            for key in resultats:
                groupes.setdefault(Get_label_groupe(key), []).append(key)
            id_ligne = 0
            for index_groupe, label_groupe in enumerate(sorted(groupes.keys(), key=lambda x: x.lower()), start=1):
                lignes_groupe = [Get_ligne(key) for key in Trier(groupes[label_groupe])]
                ligne_groupe = {"id": index_groupe, "pid": 0, "regroupement": True}
                for index, colonne in enumerate(colonnes):
                    if Get_total_colonne(index) == "somme":
                        ligne_groupe[str(index)] = round(sum(ligne[str(index)] for ligne in lignes_groupe if isinstance(ligne[str(index)], (int, float))), 2)
                ligne_groupe["0"] = "%s (%d)" % (label_groupe, len(lignes_groupe))
                lignes.append(ligne_groupe)
                for ligne in lignes_groupe:
                    id_ligne += 1
                    ligne.update({"id": 100000 + id_ligne, "pid": index_groupe, "regroupement": False})
                    lignes.append(ligne)
        else:
            lignes = [Get_ligne(key) for key in Trier(list(resultats.keys()))]

        # Indicateurs clés
        nbre_individus = len(kpi_individus)
        kpis = [
            {"label": "Individus", "aide": "Nombre d'individus ayant au moins une consommation dans les états cochés", "valeur": nbre_individus, "detail": "%d famille%s" % (len(kpi_familles), "s" if len(kpi_familles) > 1 else "")},
            {"label": "Consommations", "aide": "Nombre de consommations dans les états cochés, toutes unités confondues", "valeur": kpi_conso, "detail": "dont %d en vacances" % kpi_conso_vacances},
            {"label": "Jours de présence", "aide": "Total des journées avec au moins une réservation ou présence, par individu", "valeur": len(kpi_jours), "detail": ("%s jours / individu" % str(round(len(kpi_jours) / nbre_individus, 1)).replace(".", ",")) if nbre_individus else ""},
            {"label": "Période", "aide": "Nombre de jours calendaires de la période sélectionnée", "valeur": (date_max - date_min).days + 1, "detail": "jours, du %s au %s" % (date_min.strftime("%d/%m/%Y"), date_max.strftime("%d/%m/%Y"))},
        ]

        # Description des colonnes pour le tableau
        liste_colonnes = [{"index": str(index), "nom": Get_titre_colonne(index), "type": Get_type_colonne(index), "total": Get_total_colonne(index),
                           "description": ("Formule : %s" % colonne["formule"]) if colonne["code"] == "calcul" else dict_champs[colonne["code"]]["description"]}
                          for index, colonne in enumerate(colonnes)]

        return {"colonnes": liste_colonnes, "lignes": lignes, "kpis": kpis, "est_regroupe": regroupement in LABELS_REGROUPEMENTS, "erreurs": erreurs}

    def Formate_valeur(self, valeur, type_valeur="texte"):
        """ Les durées sont envoyées en minutes et formatées dans le navigateur """
        if valeur is None:
            return None
        if isinstance(valeur, datetime.date):
            return valeur.strftime("%d/%m/%Y")
        if isinstance(valeur, decimal.Decimal):
            return float(round(valeur, 2))
        if isinstance(valeur, float):
            return round(valeur, 2)
        return valeur
