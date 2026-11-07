# -*- coding: utf-8 -*-
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Tests de la grille des consommations sur les fonctions avancées :
forfaits-crédits (manuels et automatiques), événements, multihoraires, tarifs fratries,
unités dépendantes et solidaires. Chaque scénario est joué en mode portail (vraies vues) et en mode gestion.

Le simulateur reproduit grille.js : cases événement (event_...), cases multihoraires (multi_...),
search_unites_liees() (portail), relance de tout_recalculer() quand la facturation le demande,
get_donnees_for_facturation() et validation_form().
"""

import datetime, json, uuid
from django.test import TestCase, RequestFactory
from core.models import Structure, Activite, Groupe, CategorieTarif, Unite, Famille, Individu, Inscription, NomTarif, Tarif, CombiTarif, TarifLigne, \
                        Consommation, Prestation, Ouverture, PortailPeriode, Utilisateur, Evenement
from consommations.views import grille as vue_grille
from consommations.views.grille import Facturation, Save_grille
from portail.views import planning

D1, D2, D3 = "2026-12-02", "2026-12-09", "2026-12-16"
DATES = [D1, D2, D3]


class Grille:
    def __init__(self, test, individu, mode="portail"):
        self.test, self.mode, self.individu = test, mode, individu
        self.suppressions = {"consommations": [], "prestations": [], "memos": []}
        self.cases = {}      # key -> {"type", "date", "inscription", "unite", "evenement", "consos"}
        self.prestations = {}

        if mode == "portail":
            data = self.Get_vue().Get_data_planning()
            self.inscriptions = list(data["liste_inscriptions"])
            unites = list(data["liste_unites_visibles"])
            dates = [str(date) for date in data["liste_dates"]]
            liste_conso = list(data["liste_conso"])
            self.prestations = json.loads(data["dict_prestations_json"])
        else:
            self.inscriptions = list(Inscription.objects.filter(individu=individu, activite=test.activite))
            unites = list(Unite.objects.filter(activite=test.activite).order_by("ordre"))
            dates = DATES
            liste_conso = list(Consommation.objects.filter(inscription__in=self.inscriptions))
            for p in Prestation.objects.filter(famille=test.famille, activite=test.activite):
                self.prestations[str(p.pk)] = self.dict_prestation(p)

        # Cases (comme le template + Case_evenement + Case_multihoraires)
        for date in dates:
            for ins in self.inscriptions:
                for unite in unites:
                    key = "%s_%s_%s" % (date, ins.pk, unite.pk)
                    type_case = {"Evenement": "evenement", "Multihoraires": "multihoraires"}.get(unite.type, "standard")
                    self.cases[key] = {"type": type_case, "date": date, "inscription": ins, "unite": unite.pk, "evenement": None, "consos": []}
                    if unite.type == "Evenement":
                        for evenement in Evenement.objects.filter(date=date, unite=unite, groupe=ins.groupe):
                            self.cases["event_%s_%s" % (key, evenement.pk)] = {"type": "event", "date": date, "inscription": ins, "unite": unite.pk, "evenement": evenement.pk, "consos": []}

        # Import des conso existantes
        for conso in liste_conso:
            key = "%s_%s_%s" % (conso.date, conso.inscription_id, conso.unite_id)
            if conso.evenement_id:
                key = "event_%s_%s" % (key, conso.evenement_id)
            if key in self.cases:
                self.cases[key]["consos"].append(self.dict_conso(conso.inscription, str(conso.date), conso.unite_id, conso.pk, prestation=conso.prestation_id, etat=conso.etat,
                    evenement=conso.evenement_id, heure_debut=str(conso.heure_debut)[:5] if conso.heure_debut else None, heure_fin=str(conso.heure_fin)[:5] if conso.heure_fin else None, forfait=conso.forfait))

    # ---------------- Utilitaires ----------------

    def Get_vue(self):
        vue = planning.View()
        vue.request = self.Get_request()
        vue.kwargs = {"idindividu": self.individu.pk, "idactivite": self.test.activite.pk, "idperiode": self.test.periode.pk}
        return vue

    def Get_request(self, donnees=None, ajax=False):
        request = RequestFactory().post("/", {"donnees": json.dumps(donnees or {})}, **({"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"} if ajax else {}))
        request.user = self.test.utilisateur
        request.session = {}
        return request

    def dict_prestation(self, p):
        return {"date": str(p.date), "categorie": p.categorie, "label": p.label, "montant_initial": float(p.montant_initial), "montant": float(p.montant),
                "activite": p.activite_id, "tarif": p.tarif_id, "facture": p.facture_id, "famille": p.famille_id, "individu": p.individu_id,
                "categorie_tarif": p.categorie_tarif_id, "temps_facture": None, "quantite": p.quantite, "tarif_ligne": p.tarif_ligne_id, "tva": None,
                "code_compta": None, "aides": [], "forfait_date_debut": str(p.forfait_date_debut) if p.forfait_date_debut else None,
                "forfait_date_fin": str(p.forfait_date_fin) if p.forfait_date_fin else None, "forfait": p.forfait, "dirty": False}

    def dict_conso(self, ins, date, idunite, pk, prestation=None, etat="reservation", **valeurs):
        conso = {"pk": pk, "individu": ins.individu_id, "inscription": ins.pk, "activite": ins.activite_id, "famille": ins.famille_id,
                 "date": date, "unite": idunite, "groupe": ins.groupe_id, "heure_debut": None, "heure_fin": None, "etat": etat,
                 "categorie_tarif": ins.categorie_tarif_id, "prestation": prestation, "quantite": 1, "evenement": None, "badgeage_debut": None,
                 "badgeage_fin": None, "forfait": None, "dirty": False, "facture": None, "options": None, "extra": None}
        conso.update(valeurs)
        return conso

    def key(self, ins, date, unite, evenement=None):
        key = "%s_%s_%s" % (date, ins.pk, unite.pk)
        return "event_%s_%s" % (key, evenement.pk) if evenement else key

    # ---------------- Actions (clics) ----------------

    def ajouter(self, ins, date, unite, evenement=None, **valeurs):
        key = self.key(ins, date, unite, evenement)
        conso = self.dict_conso(ins, date, unite.pk, str(uuid.uuid4()), evenement=evenement.pk if evenement else None, dirty=True, **valeurs)
        if self.cases[key]["type"] == "multihoraires":
            self.cases[key]["consos"].append(conso)
        else:
            self.cases[key]["consos"] = [conso]
        self.apres_clic(date, ins)
        return conso

    def supprimer(self, ins, date, unite, evenement=None, index=0):
        key = self.key(ins, date, unite, evenement)
        conso = self.cases[key]["consos"].pop(index)
        if "-" not in str(conso["pk"]):
            self.suppressions["consommations"].append(conso["pk"])
        self.apres_clic(date, ins)

    def apres_clic(self, date, ins):
        """ facturer(case) en mode portail : search_unites_liees() (version corrigée de grille.js) """
        if self.mode != "portail":
            return
        dict_unites = {u.pk: u for u in Unite.objects.filter(activite=self.test.activite).prefetch_related("dependances", "solidaires")}
        for key, case in list(self.cases.items()):
            if case["date"] != date or case["inscription"].pk != ins.pk:
                continue
            for conso in list(case["consos"]):
                unite = dict_unites[conso["unite"]]
                dependances = [u.pk for u in unite.dependances.all()]
                if dependances:
                    keys_dep = ["%s_%s_%s" % (date, ins.pk, iddep) for iddep in dependances]
                    if all(k in self.cases for k in keys_dep) and not any(self.cases[k]["consos"] for k in keys_dep):
                        for c in case["consos"]:
                            if "-" not in str(c["pk"]):
                                self.suppressions["consommations"].append(c["pk"])
                        case["consos"] = []
                for solidaire in unite.solidaires.all():
                    key_sol = "%s_%s_%s" % (date, ins.pk, solidaire.pk)
                    if key_sol in self.cases and not self.cases[key_sol]["consos"]:
                        self.cases[key_sol]["consos"] = [self.dict_conso(ins, date, solidaire.pk, str(uuid.uuid4()), etat=conso["etat"], dirty=True)]

    # ---------------- Facturation et enregistrement ----------------

    def get_donnees_facturation(self):
        """ tout_recalculer() + get_donnees_for_facturation() """
        consommations, cases_touchees, vus, self.index_keys = {}, {}, set(), {}
        for key, case in self.cases.items():
            ins = case["inscription"]
            if (case["date"], ins.pk) not in vus:
                vus.add((case["date"], ins.pk))
                cases_touchees[key] = {"date": case["date"], "inscription": ins.pk, "activite": ins.activite_id, "categorie_tarif": ins.categorie_tarif_id,
                                       "famille": ins.famille_id, "individu": ins.individu_id, "groupe": ins.groupe_id}
            if case["type"] == "evenement":
                continue
            if case["type"] == "multihoraires":
                liste = [("multi_%s_%d" % (key, index), [conso]) for index, conso in enumerate(case["consos"])]
            else:
                liste = [(key, case["consos"])]
            for key_case, consos in liste:
                self.index_keys[key_case] = consos
                for conso in consos:
                    conso["key_case"] = key_case
                    consommations.setdefault("%s_%s" % (case["date"], ins.pk), []).append(conso)
        keys_lignes = ["%s_%s_%s_%s" % (c["date"], c["famille"], c["individu"], c["activite"]) for c in cases_touchees.values()]
        prestations = {k: p for k, p in self.prestations.items() if "%s_%s_%s_%s" % (p["date"], p["famille"], p["individu"], p["activite"]) in keys_lignes or p["forfait_date_debut"]}
        return {"consommations": consommations, "prestations": prestations, "dict_aides": [], "cases_touchees": cases_touchees, "liste_vacances": [],
                "dict_suppressions": self.suppressions, "mode": "portail" if self.mode == "portail" else "individu", "activite": self.test.activite.pk}

    def facturer(self):
        donnees = json.loads(json.dumps(self.get_donnees_facturation()))
        if self.mode == "portail":
            return json.loads(vue_grille.Facturer(self.Get_request(donnees, ajax=True)).content)
        return json.loads(json.dumps(Facturation(donnees=donnees).Facturer()))

    def enregistrer(self):
        for _ in range(5):
            retour = self.facturer()
            self.prestations.update(retour["nouvelles_prestations"])
            for idprestation in retour["anciennes_prestations"]:
                if "-" not in str(idprestation):
                    self.suppressions["prestations"].append(int(idprestation))
                self.prestations.pop(str(idprestation), None)
            for key, idprestation in retour["modifications_idprestation"].items():
                for conso in self.index_keys.get(key, []):
                    conso.update({"prestation": idprestation, "dirty": True})
            if not retour.get("tout_recalculer"):
                break

        # validation_form : toutes les cases sauf "evenement" et "multi" (les conso multihoraires sont dans la case parente)
        consommations = {key: case["consos"] for key, case in self.cases.items() if case["type"] != "evenement"}
        for consos in consommations.values():
            for conso in consos:
                conso.pop("key_case", None)
        donnees = json.loads(json.dumps({"activite": self.test.activite.pk, "ancienne_activite": self.test.activite.pk, "consommations": consommations,
                                         "memos": {}, "suppressions": self.suppressions, "prestations": self.prestations}))
        if self.mode == "portail":
            vue = self.Get_vue()
            vue.request = self.Get_request(donnees)
            vue.post(vue.request)
        else:
            Save_grille(request=None, donnees=donnees)


class Base(TestCase):
    MODE = "portail"

    def setUp(self):
        self.structure = Structure.objects.create(nom="Structure")
        self.activite = Activite.objects.create(structure=self.structure, nom="ALSH", date_debut=datetime.date(2020, 1, 1), date_fin=datetime.date(2999, 12, 31))
        self.g1 = Groupe.objects.create(nom="Maternels", ordre=1, activite=self.activite)
        self.g2 = Groupe.objects.create(nom="Primaires", ordre=2, activite=self.activite)
        self.cat = CategorieTarif.objects.create(nom="Unique", activite=self.activite)
        self.unites = {}
        for ordre, (nom, type_unite) in enumerate([("Journée", "Unitaire"), ("Repas", "Unitaire"), ("Garderie", "Unitaire"), ("Sortie", "Evenement"), ("Accueil", "Multihoraires")]):
            self.unites[nom] = Unite.objects.create(nom=nom, abrege=nom[:3], ordre=ordre, type=type_unite, activite=self.activite, date_debut=datetime.date(2020, 1, 1), date_fin=datetime.date(2999, 1, 1))
        self.journee, self.repas, self.garderie, self.sortie, self.accueil = [self.unites[nom] for nom in ("Journée", "Repas", "Garderie", "Sortie", "Accueil")]
        for date in DATES:
            for groupe in (self.g1, self.g2):
                for unite in self.unites.values():
                    Ouverture.objects.create(date=date, activite=self.activite, groupe=groupe, unite=unite)
        self.periode = PortailPeriode.objects.create(activite=self.activite, nom="Période", date_debut=datetime.date(2026, 11, 1), date_fin=datetime.date(2026, 12, 31))

        self.famille = Famille.objects.create()
        self.utilisateur = Utilisateur.objects.create_user(username="famille", password="123456", categorie="famille")
        self.famille.utilisateur = self.utilisateur
        self.famille.save()
        self.enfant = Individu.objects.create(civilite=4, nom="TEST", prenom="Aîné", date_naiss=datetime.date(2016, 1, 1))
        self.ins1 = self.inscrire(self.enfant, self.g1)

    def inscrire(self, individu, groupe):
        return Inscription.objects.create(activite=self.activite, groupe=groupe, categorie_tarif=self.cat, famille=self.famille, individu=individu, date_debut=datetime.date(2026, 1, 1))

    def tarif(self, nom, unites, montant=None, methode="montant_unique", type_tarif="JOURN", ligne={}, **kwargs):
        nom_tarif = NomTarif.objects.create(activite=self.activite, nom=nom)
        tarif = Tarif.objects.create(activite=self.activite, nom_tarif=nom_tarif, date_debut=datetime.date(2020, 1, 1), type=type_tarif, methode=methode,
                                     etats=["reservation", "present", "absenti"], **kwargs)
        tarif.categories_tarifs.add(self.cat)
        combi = CombiTarif.objects.create(tarif=tarif, type=type_tarif)
        combi.unites.set(unites)
        valeurs = {"montant_unique": montant} if montant is not None else {}
        valeurs.update(ligne)
        TarifLigne.objects.create(activite=self.activite, tarif=tarif, code=methode, num_ligne=0, **valeurs)
        return tarif

    def grille(self, individu=None, mode=None):
        return Grille(self, individu or self.enfant, mode=mode or self.MODE)

    def creer_conso(self, ins, date, unite, **valeurs):
        """ Saisie par le personnel """
        g = self.grille(ins.individu, mode="gestion"); g.ajouter(ins, date, unite, **valeurs); g.enregistrer()

    def etat(self):
        consos = sorted((str(c.date), c.inscription_id, c.unite.nom, c.evenement_id or 0, str(c.heure_debut or "")) for c in Consommation.objects.all())
        prestations = sorted((str(p.date), p.label, float(p.montant), p.individu_id) for p in Prestation.objects.all())
        orphelines = Consommation.objects.filter(prestation__isnull=True).count()
        mauvais_lien = Consommation.objects.exclude(prestation__isnull=True).exclude(prestation_id__in=Prestation.objects.values("pk")).count()
        return consos, prestations, orphelines, mauvais_lien

    def montants(self):
        return sorted(float(p.montant) for p in Prestation.objects.all())

    def assertStable(self, individu=None, fois=2):
        """ Des enregistrements sans modification ne changent rien (ni conso, ni prestation, ni ID) """
        avant, ids = self.etat(), sorted(Prestation.objects.values_list("pk", flat=True))
        for _ in range(fois):
            self.grille(individu).enregistrer()
        self.assertEqual(self.etat(), avant)
        self.assertEqual(sorted(Prestation.objects.values_list("pk", flat=True)), ids, "Les prestations ont été supprimées puis recréées")


class Scenarios:

    # ======================= Forfaits-crédits manuels =======================

    def preparer_forfait_manuel(self):
        self.tarif("Journée", [self.journee], 10)
        self.tarif_forfait = self.tarif("Forfait 10 journées", [self.journee], 50, type_tarif="CREDIT", forfait_beneficiaire="individu")
        self.forfait = Prestation.objects.create(date="2026-12-01", categorie="consommation", label="Forfait 10 journées", montant_initial=50, montant=50,
                                                 activite=self.activite, tarif=self.tarif_forfait, famille=self.famille, individu=self.enfant, categorie_tarif=self.cat,
                                                 forfait_date_debut="2026-12-01", forfait_date_fin="2026-12-31", quantite=1)

    def test_forfait_manuel_ajout(self):
        self.preparer_forfait_manuel()
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        self.assertEqual(set(Consommation.objects.values_list("prestation_id", flat=True)), {self.forfait.pk})
        self.assertEqual(self.montants(), [50.0])
        self.assertStable()

    def test_forfait_manuel_suppression_conso(self):
        self.preparer_forfait_manuel()
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        g = self.grille(); g.supprimer(self.ins1, D2, self.journee); g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 1)
        self.assertTrue(Prestation.objects.filter(pk=self.forfait.pk).exists())
        self.assertEqual(self.montants(), [50.0])

    def test_forfait_manuel_deux_groupes(self):
        self.preparer_forfait_manuel()
        ins2 = self.inscrire(self.enfant, self.g2)
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(ins2, D1, self.journee); g.ajouter(ins2, D2, self.journee); g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 3)
        self.assertEqual(set(Consommation.objects.values_list("prestation_id", flat=True)), {self.forfait.pk})
        self.assertEqual(self.montants(), [50.0])
        self.assertStable()

    # ======================= Forfaits-crédits automatiques =======================

    def preparer_forfait_auto(self):
        self.tarif("Journée", [self.journee], 10)
        self.tarif_forfait = self.tarif("Forfait mois", [self.journee], 25, type_tarif="CREDIT", forfait_beneficiaire="individu",
                                        forfait_auto=json.dumps({"nbre_conso_min": 2, "debut": "PREC_MOIS_PREMIER_JOUR", "fin": "SUIV_MOIS_DERNIER_JOUR"}))

    def test_forfait_auto_creation(self):
        self.preparer_forfait_auto()
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        self.assertEqual(self.montants(), [10.0])
        g = self.grille(); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 2)
        self.assertEqual(self.montants(), [25.0])
        self.assertEqual((orph, ml), (0, 0))
        self.assertStable()

    def test_forfait_auto_retrait(self):
        """ Sous le seuil, le forfait automatique doit disparaître et la journée restante être facturée normalement """
        self.preparer_forfait_auto()
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        self.assertEqual(self.montants(), [25.0])
        g = self.grille(); g.supprimer(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 1)
        self.assertEqual(self.montants(), [10.0])
        self.assertEqual((orph, ml), (0, 0))

    # ======================= Événements =======================

    def preparer_evenements(self):
        self.tarif("Sortie", [self.sortie], methode="montant_evenement")
        self.tarif("Journée", [self.journee], 10)
        self.zoo = Evenement.objects.create(activite=self.activite, unite=self.sortie, groupe=self.g1, date=D1, nom="Zoo", montant=15)
        self.piscine = Evenement.objects.create(activite=self.activite, unite=self.sortie, groupe=self.g1, date=D1, nom="Piscine", montant=8)
        self.zoo_g2 = Evenement.objects.create(activite=self.activite, unite=self.sortie, groupe=self.g2, date=D1, nom="Zoo", montant=15)

    def test_evenement_ajout(self):
        self.preparer_evenements()
        g = self.grille(); g.ajouter(self.ins1, D1, self.sortie, evenement=self.zoo); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 2)
        self.assertEqual(sorted((p[1], p[2]) for p in prestations), [("Journée", 10.0), ("Zoo", 15.0)])
        self.assertEqual((orph, ml), (0, 0))
        self.assertStable()

    def test_evenement_deux_evenements_meme_jour(self):
        self.preparer_evenements()
        g = self.grille(); g.ajouter(self.ins1, D1, self.sortie, evenement=self.zoo); g.ajouter(self.ins1, D1, self.sortie, evenement=self.piscine); g.enregistrer()
        self.assertEqual(self.montants(), [8.0, 15.0])
        g = self.grille(); g.supprimer(self.ins1, D1, self.sortie, evenement=self.zoo); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 1)
        self.assertEqual(self.montants(), [8.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_evenement_deux_groupes(self):
        self.preparer_evenements()
        ins2 = self.inscrire(self.enfant, self.g2)
        g = self.grille(); g.ajouter(self.ins1, D1, self.sortie, evenement=self.zoo); g.ajouter(ins2, D1, self.sortie, evenement=self.zoo_g2); g.enregistrer()
        g = self.grille(); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 3)
        self.assertEqual(self.montants(), [10.0, 15.0, 15.0])
        self.assertEqual((orph, ml), (0, 0))

    # ======================= Multihoraires =======================

    def preparer_multihoraires(self):
        self.tarif("Accueil", [self.accueil], 3)

    def test_multihoraires_ajout(self):
        self.preparer_multihoraires()
        g = self.grille(); g.ajouter(self.ins1, D1, self.accueil, heure_debut="07:30", heure_fin="08:30"); g.ajouter(self.ins1, D1, self.accueil, heure_debut="17:00", heure_fin="18:00"); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 2)
        self.assertEqual(self.montants(), [3.0])
        self.assertEqual(Consommation.objects.values("prestation").distinct().count(), 1)
        self.assertEqual((orph, ml), (0, 0))
        self.assertStable()

    def test_multihoraires_suppression(self):
        self.preparer_multihoraires()
        g = self.grille(); g.ajouter(self.ins1, D1, self.accueil, heure_debut="07:30", heure_fin="08:30"); g.ajouter(self.ins1, D1, self.accueil, heure_debut="17:00", heure_fin="18:00"); g.enregistrer()
        g = self.grille(); g.supprimer(self.ins1, D1, self.accueil, index=0); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 1)
        self.assertEqual(self.montants(), [3.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_multihoraires_deux_groupes(self):
        self.preparer_multihoraires()
        ins2 = self.inscrire(self.enfant, self.g2)
        g = self.grille(); g.ajouter(self.ins1, D1, self.accueil, heure_debut="07:30", heure_fin="08:30"); g.ajouter(ins2, D1, self.accueil, heure_debut="17:00", heure_fin="18:00"); g.enregistrer()
        g = self.grille(); g.ajouter(self.ins1, D2, self.accueil, heure_debut="07:30", heure_fin="08:30"); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 3)
        self.assertEqual(self.montants(), [3.0, 3.0, 3.0])
        self.assertEqual((orph, ml), (0, 0))

    # ======================= Tarifs fratries =======================

    def preparer_fratrie(self):
        self.tarif("Journée fratrie", [self.journee], methode="montant_unique_nbre_ind", ligne={"montant_enfant_1": 10, "montant_enfant_2": 7})
        self.cadet = Individu.objects.create(civilite=4, nom="TEST", prenom="Cadet", date_naiss=datetime.date(2019, 1, 1))
        self.ins_cadet = self.inscrire(self.cadet, self.g1)

    def test_fratrie(self):
        self.preparer_fratrie()
        g = self.grille(self.enfant); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        self.assertEqual(self.montants(), [10.0])
        g = self.grille(self.cadet); g.ajouter(self.ins_cadet, D1, self.journee); g.enregistrer()
        self.assertEqual(self.montants(), [7.0, 7.0])
        consos, prestations, orph, ml = self.etat()
        self.assertEqual((orph, ml), (0, 0))

    def test_fratrie_stabilite(self):
        """ Réenregistrer la page d'un enfant ne doit ni changer les montants ni recréer les prestations (règlements ventilés perdus) """
        self.preparer_fratrie()
        g = self.grille(self.enfant); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        g = self.grille(self.cadet); g.ajouter(self.ins_cadet, D1, self.journee); g.enregistrer()
        self.assertStable(self.enfant)
        self.assertStable(self.cadet)

    def test_fratrie_retrait(self):
        self.preparer_fratrie()
        g = self.grille(self.enfant); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        g = self.grille(self.cadet); g.ajouter(self.ins_cadet, D1, self.journee); g.enregistrer()
        g = self.grille(self.cadet); g.supprimer(self.ins_cadet, D1, self.journee); g.enregistrer()
        self.assertEqual(self.montants(), [10.0])

    # ======================= Unités dépendantes =======================

    def test_dependance_retrait(self):
        """ Repas dépend de Journée : retirer la journée retire le repas (portail : grille.js) """
        self.tarif("Journée", [self.journee], 10); self.tarif("Repas", [self.repas], 4)
        self.repas.dependances.add(self.journee)
        self.creer_conso(self.ins1, D1, self.journee); self.creer_conso(self.ins1, D1, self.repas)
        g = self.grille(); g.supprimer(self.ins1, D1, self.journee)
        if self.MODE == "gestion":
            g.supprimer(self.ins1, D1, self.repas)
        g.enregistrer()
        self.assertEqual(self.etat()[:2], ([], []))

    # ======================= Unités solidaires =======================

    def test_solidaires(self):
        """ Journée entraîne Repas ; plusieurs clics sur la ligne ne doivent pas créer de doublons """
        self.tarif("Journée", [self.journee], 10); self.tarif("Repas", [self.repas], 4); self.tarif("Journée + repas", [self.journee, self.repas], 13); self.tarif("Garderie", [self.garderie], 2)
        self.journee.solidaires.add(self.repas)
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee)
        if self.MODE == "gestion":
            g.ajouter(self.ins1, D1, self.repas)
        g.ajouter(self.ins1, D1, self.garderie); g.supprimer(self.ins1, D1, self.garderie); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual([c[2] for c in consos], ["Journée", "Repas"])
        self.assertEqual(self.montants(), [13.0])
        self.assertStable()


class Portail(Scenarios, Base):
    MODE = "portail"

    def test_dependance_unite_masquee(self):
        """ Repas dépend de Garderie, masquée sur le portail : la famille ajoute une journée, le repas doit rester """
        self.tarif("Journée", [self.journee], 10); self.tarif("Repas", [self.repas], 4); self.tarif("Garderie", [self.garderie], 2)
        self.repas.dependances.add(self.garderie)
        self.creer_conso(self.ins1, D1, self.garderie); self.creer_conso(self.ins1, D1, self.repas)
        Unite.objects.filter(pk=self.garderie.pk).update(visible_portail=False)
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        self.assertEqual(sorted(c[2] for c in self.etat()[0]), ["Garderie", "Journée", "Repas"])
        self.assertEqual(self.montants(), [2.0, 4.0, 10.0])

    def test_doublon_envoye_par_le_navigateur(self):
        """ Ancien grille.js (unités solidaires) : plusieurs conso sur la même case -> une seule enregistrée """
        self.tarif("Repas", [self.repas], 4)
        g = self.grille(); g.ajouter(self.ins1, D1, self.repas)
        key = g.key(self.ins1, D1, self.repas)
        g.cases[key]["consos"] += [g.dict_conso(self.ins1, D1, self.repas.pk, str(uuid.uuid4()), dirty=True) for _ in range(2)]
        g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 1)
        self.assertEqual(self.montants(), [4.0])
        # Et pas de doublon d'une conso déjà en base
        g = self.grille(); g.cases[key]["consos"].append(g.dict_conso(self.ins1, D1, self.repas.pk, str(uuid.uuid4()), dirty=True)); g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 1)

    def test_evenement_non_visible_ou_autre_groupe(self):
        self.preparer_evenements()
        Evenement.objects.filter(pk=self.piscine.pk).update(visible_portail=False)
        g = self.grille(); g.ajouter(self.ins1, D1, self.sortie, evenement=self.piscine)
        key = g.key(self.ins1, D1, self.sortie, self.zoo)
        g.cases[key]["consos"] = [g.dict_conso(self.ins1, D1, self.sortie.pk, str(uuid.uuid4()), evenement=self.zoo_g2.pk, dirty=True)]
        g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 0)


class Gestion(Scenarios, Base):
    MODE = "gestion"
