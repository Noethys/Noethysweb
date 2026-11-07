# -*- coding: utf-8 -*-
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Tests de non-régression : disparition de consommations à l'enregistrement de la grille
- plusieurs inscriptions du même individu sur la même activité (groupes différents)
- unités masquées sur le portail
- sécurité des données envoyées par le portail famille

Deux simulateurs de la grille JS (grille.js) :
- mode "portail" : passe par les vraies vues (grille.Facturer en AJAX, puis planning.View.post) avec un compte famille ;
- mode "gestion" : Facturation + Save_grille directement, comme la grille de la fiche famille.
"""

import datetime, json, uuid, os
from django.test import TestCase, RequestFactory
from core.models import Structure, Activite, Groupe, CategorieTarif, Unite, Famille, Individu, Inscription, NomTarif, Tarif, CombiTarif, TarifLigne, \
                        Consommation, Prestation, Facture, Ouverture, PortailPeriode, Utilisateur, Historique
from consommations.views import grille as vue_grille
from consommations.views.grille import Facturation, Save_grille
from portail.views import planning

D1, D2, D3 = "2026-12-02", "2026-12-09", "2026-12-16"
DATES = [D1, D2, D3]
AUJOURDHUI = datetime.date.today()


class Grille:
    """ Simule la grille JS (dict_cases, dict_prestations, dict_suppressions) """
    def __init__(self, test, inscriptions, mode="portail", periode=None):
        self.test, self.inscriptions, self.mode, self.periode = test, inscriptions, mode, periode
        self.suppressions = {"consommations": [], "prestations": [], "memos": []}
        self.cases, self.prestations = {}, {}

        if mode == "portail":
            # Données de la page (comme le template)
            individu = inscriptions[0].individu
            data = self.Get_vue(individu).Get_data_planning()
            self.inscriptions = list(data["liste_inscriptions"])
            for date in data["liste_dates"]:
                for inscription in data["liste_inscriptions"]:
                    for unite in data["liste_unites_visibles"]:
                        self.cases["%s_%s_%s" % (date, inscription.pk, unite.pk)] = []
            for conso in data["liste_conso"]:
                key = "%s_%s_%s" % (conso.date, conso.inscription_id, conso.unite_id)
                if key in self.cases:
                    self.cases[key].append(self._dict_conso(conso.inscription, str(conso.date), conso.unite_id, conso.pk, conso.prestation_id, conso.etat))
            self.prestations = json.loads(data["dict_prestations_json"])
        else:
            for conso in Consommation.objects.filter(inscription__in=inscriptions):
                self.cases.setdefault("%s_%s_%s" % (conso.date, conso.inscription_id, conso.unite_id), []).append(
                    self._dict_conso(conso.inscription, str(conso.date), conso.unite_id, conso.pk, conso.prestation_id, conso.etat))
            for p in Prestation.objects.filter(famille=test.famille, individu=test.enfant, activite=test.activite):
                self.prestations[str(p.pk)] = {
                    "date": str(p.date), "categorie": p.categorie, "label": p.label, "montant_initial": float(p.montant_initial), "montant": float(p.montant),
                    "activite": p.activite_id, "tarif": p.tarif_id, "facture": p.facture_id, "famille": p.famille_id, "individu": p.individu_id,
                    "categorie_tarif": p.categorie_tarif_id, "temps_facture": None, "quantite": p.quantite, "tarif_ligne": p.tarif_ligne_id, "tva": None,
                    "code_compta": None, "aides": [], "forfait_date_debut": None, "forfait_date_fin": None, "forfait": p.forfait, "dirty": False}

    def Get_vue(self, individu):
        vue = planning.View()
        vue.request = self.Get_request()
        vue.kwargs = {"idindividu": individu.pk, "idactivite": self.test.activite.pk, "idperiode": self.periode.pk}
        return vue

    def Get_request(self, donnees=None, ajax=False):
        kwargs = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"} if ajax else {}
        request = RequestFactory().post("/", {"donnees": json.dumps(donnees or {})}, **kwargs)
        request.user = self.test.utilisateur
        request.session = {}
        return request

    def _dict_conso(self, inscription, date, idunite, pk, prestation, etat="reservation"):
        return {"pk": pk, "individu": inscription.individu_id, "inscription": inscription.pk, "activite": inscription.activite_id, "famille": inscription.famille_id,
                "date": date, "unite": idunite, "groupe": inscription.groupe_id, "heure_debut": None, "heure_fin": None, "etat": etat,
                "categorie_tarif": inscription.categorie_tarif_id, "prestation": prestation, "quantite": 1, "evenement": None, "badgeage_debut": None,
                "badgeage_fin": None, "forfait": None, "dirty": False, "facture": None, "options": None, "extra": None}

    def ajouter(self, inscription, date, unite, **valeurs):
        conso = self._dict_conso(inscription, date, unite.pk, str(uuid.uuid4()), None)
        conso.update(valeurs)
        self.cases["%s_%s_%s" % (date, inscription.pk, unite.pk)] = [conso]
        return conso

    def supprimer(self, inscription, date, unite):
        key = "%s_%s_%s" % (date, inscription.pk, unite.pk)
        for conso in self.cases[key]:
            if "-" not in str(conso["pk"]):
                self.suppressions["consommations"].append(conso["pk"])
        self.cases[key] = []  # La case reste dans dict_cases (vide), comme dans le JS

    def get_donnees_facturation(self):
        """ tout_recalculer() + get_donnees_for_facturation() de grille.js """
        if os.environ.get("ORDRE_INVERSE"):
            self.cases = dict(reversed(list(self.cases.items())))
        cases_touchees, vus = {}, set()
        for key in self.cases.keys():
            date, idinscription, _ = key.split("_")
            if (date, idinscription) not in vus:
                vus.add((date, idinscription))
                ins = [i for i in self.inscriptions if i.pk == int(idinscription)][0]
                cases_touchees[key] = {"date": date, "inscription": ins.pk, "activite": ins.activite_id, "categorie_tarif": ins.categorie_tarif_id,
                                       "famille": ins.famille_id, "individu": ins.individu_id, "groupe": ins.groupe_id}
        consommations = {}
        for key, consos in self.cases.items():
            for conso in consos:
                conso["key_case"] = key
                consommations.setdefault("%s_%s" % (conso["date"], conso["inscription"]), []).append(conso)
        keys_lignes = ["%s_%s_%s_%s" % (c["date"], c["famille"], c["individu"], c["activite"]) for c in cases_touchees.values()]
        prestations = {k: p for k, p in self.prestations.items() if "%s_%s_%s_%s" % (p["date"], p["famille"], p["individu"], p["activite"]) in keys_lignes or p["forfait_date_debut"]}
        return {"consommations": consommations, "prestations": prestations, "dict_aides": [], "cases_touchees": cases_touchees,
                "liste_vacances": [], "dict_suppressions": self.suppressions, "mode": self.mode if self.mode == "portail" else "individu", "activite": self.test.activite.pk}

    def facturer(self, donnees=None):
        donnees = json.loads(json.dumps(donnees or self.get_donnees_facturation()))
        if self.mode == "portail":
            reponse = vue_grille.Facturer(self.Get_request(donnees, ajax=True))
            return json.loads(reponse.content)
        return json.loads(json.dumps(Facturation(donnees=donnees).Facturer()))

    def enregistrer(self, alterer=None):
        retour = self.facturer()

        # Traitement du retour (ajax_facturer)
        self.prestations.update(retour["nouvelles_prestations"])
        for idprestation in retour["anciennes_prestations"]:
            if "-" not in str(idprestation):
                self.suppressions["prestations"].append(int(idprestation))
            self.prestations.pop(str(idprestation), None)
        for key, idprestation in retour["modifications_idprestation"].items():
            if self.cases.get(key):
                self.cases[key][0].update({"prestation": idprestation, "dirty": True})

        # Submit (validation_form)
        donnees = {"activite": self.test.activite.pk, "ancienne_activite": self.test.activite.pk, "consommations": self.cases,
                   "memos": {}, "suppressions": self.suppressions, "prestations": self.prestations}
        if alterer:
            alterer(donnees)
        donnees = json.loads(json.dumps(donnees))
        if self.mode == "portail":
            vue = self.Get_vue(self.inscriptions[0].individu)
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
        self.cat_reduite = CategorieTarif.objects.create(nom="Réduite", activite=self.activite)
        kw = dict(activite=self.activite, type="Unitaire", date_debut=datetime.date(2020, 1, 1), date_fin=datetime.date(2999, 1, 1))
        self.journee = Unite.objects.create(nom="Journée", abrege="J", ordre=1, **kw)
        self.repas = Unite.objects.create(nom="Repas", abrege="R", ordre=2, **kw)
        self.tarif_journee = self.creer_tarif("Journée", [self.journee], 10)
        self.tarif_repas = self.creer_tarif("Repas", [self.repas], 4)
        self.tarif_journee_repas = self.creer_tarif("Journée + repas", [self.journee, self.repas], 13)
        self.tarif_reduit = self.creer_tarif("Journée réduite", [self.journee], 1, categorie=self.cat_reduite)
        for date in DATES:
            for groupe in (self.g1, self.g2):
                for unite in (self.journee, self.repas):
                    Ouverture.objects.create(date=date, activite=self.activite, groupe=groupe, unite=unite)
        self.periode = PortailPeriode.objects.create(activite=self.activite, nom="Période", date_debut=datetime.date(2026, 11, 1), date_fin=datetime.date(2026, 12, 31))

        # Famille connectée
        self.famille, self.enfant, self.utilisateur = self.creer_famille("famille1")
        self.ins1 = self.creer_inscription(self.famille, self.enfant, self.g1)
        self.ins2 = self.creer_inscription(self.famille, self.enfant, self.g2)

        # Autre famille (cible des attaques)
        self.famille_b, self.enfant_b, self.utilisateur_b = self.creer_famille("famille2")
        self.ins_b = self.creer_inscription(self.famille_b, self.enfant_b, self.g1)

    def creer_famille(self, identifiant):
        famille = Famille.objects.create()
        utilisateur = Utilisateur.objects.create_user(username=identifiant, password="123456", categorie="famille")
        famille.utilisateur = utilisateur
        famille.save()
        enfant = Individu.objects.create(civilite=4, nom="TEST", prenom=identifiant)
        return famille, enfant, utilisateur

    def creer_inscription(self, famille, individu, groupe):
        return Inscription.objects.create(activite=self.activite, groupe=groupe, categorie_tarif=self.cat, famille=famille, individu=individu, date_debut=datetime.date(2026, 1, 1))

    def creer_tarif(self, nom, unites, montant, categorie=None):
        nom_tarif = NomTarif.objects.create(activite=self.activite, nom=nom)
        tarif = Tarif.objects.create(activite=self.activite, nom_tarif=nom_tarif, date_debut=datetime.date(2020, 1, 1), type="JOURN", methode="montant_unique", etats=["reservation", "present", "absenti"])
        tarif.categories_tarifs.add(categorie or self.cat)
        combi = CombiTarif.objects.create(tarif=tarif, type="JOURN")
        combi.unites.set(unites)
        TarifLigne.objects.create(activite=self.activite, tarif=tarif, code="montant_unique", num_ligne=0, montant_unique=montant)
        return tarif

    def grille(self, inscriptions=None, mode=None):
        return Grille(self, inscriptions or [self.ins1, self.ins2], mode=mode or self.MODE, periode=self.periode)

    def grille_gestion(self, inscriptions=None):
        """ Saisie par le personnel (toutes les unités) """
        return self.grille(inscriptions, mode="gestion")

    def masquer(self, unite):
        Unite.objects.filter(pk=unite.pk).update(visible_portail=False)

    def creer_conso(self, inscription, date, unite, etat="reservation"):
        """ Saisie par le personnel avec calcul de la prestation """
        g = self.grille_gestion([inscription]); g.ajouter(inscription, date, unite, etat=etat); g.enregistrer()

    def etat(self, famille=None):
        famille = famille or self.famille
        consos = sorted((str(c.date), c.inscription_id, c.unite.nom, c.etat) for c in Consommation.objects.filter(inscription__famille=famille))
        prestations = sorted((str(p.date), p.label, float(p.montant)) for p in Prestation.objects.filter(famille=famille))
        orphelines = Consommation.objects.filter(inscription__famille=famille, prestation__isnull=True).exclude(etat__in=("refus", "demande", "attente")).count()
        mauvais_lien = Consommation.objects.filter(inscription__famille=famille).exclude(prestation__isnull=True).exclude(prestation_id__in=Prestation.objects.values("pk")).count()
        return consos, prestations, orphelines, mauvais_lien

    def montants(self):
        return sorted(float(p.montant) for p in Prestation.objects.filter(famille=self.famille))


class Communs:
    """ Scénarios fonctionnels exécutés en mode portail et en mode gestion """

    # ---------------- Double inscription ----------------

    def test_01_deux_groupes_unites_differentes(self):
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.repas); g.enregistrer()
        g = self.grille(); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 3)
        self.assertEqual(self.montants(), [4.0, 10.0, 10.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_02_deux_groupes_meme_unite(self):
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        g = self.grille(); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 3)
        self.assertEqual(len(prestations), 3)
        self.assertEqual(Consommation.objects.filter(date=D1).values("prestation").distinct().count(), 2)
        self.assertEqual((orph, ml), (0, 0))

    def test_03_suppression_sur_une_ligne(self):
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.repas); g.enregistrer()
        g = self.grille(); g.supprimer(self.ins2, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(consos, [(D1, self.ins1.pk, "Journée", "reservation")])
        self.assertEqual(prestations, [(D1, "Journée", 10.0)])

    def test_04_enregistrements_successifs_stables(self):
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.ajouter(self.ins2, D2, self.repas); g.enregistrer()
        avant = self.etat(); ids_avant = sorted(Prestation.objects.values_list("pk", flat=True))
        for _ in range(3):
            self.grille().enregistrer()
        self.assertEqual(self.etat(), avant)
        self.assertEqual(sorted(Prestation.objects.values_list("pk", flat=True)), ids_avant)

    def test_05_une_inscription_combinaison(self):
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 2)
        self.assertEqual(prestations, [(D1, "Journée + repas", 13.0)])
        self.assertEqual((orph, ml), (0, 0))

    def test_06_une_inscription_suppression(self):
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        g = self.grille([self.ins1]); g.supprimer(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(consos, [(D1, self.ins1.pk, "Journée", "reservation")])
        self.assertEqual(prestations, [(D1, "Journée", 10.0)])

    def test_07_deux_groupes_combinaison_sur_une_ligne(self):
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        g = self.grille(); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 3)
        self.assertEqual(self.montants(), [10.0, 13.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_08_prestation_facturee(self):
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        p2 = Consommation.objects.get(inscription=self.ins2).prestation
        facture = Facture.objects.create(famille=self.famille, numero=1, date_edition=datetime.date(2026, 12, 31), date_debut=datetime.date(2026, 12, 1), date_fin=datetime.date(2026, 12, 31))
        Prestation.objects.filter(pk=p2.pk).update(facture=facture)
        g = self.grille(); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        self.assertTrue(Prestation.objects.filter(pk=p2.pk).exists())
        self.assertEqual(Consommation.objects.get(inscription=self.ins2).prestation_id, p2.pk)
        self.assertEqual(len(self.etat()[0]), 3)
        self.assertEqual(self.etat()[2:], (0, 0))

    def test_10_donnees_existantes_prestation_partagee(self):
        """ Données abîmées par l'ancien bug : une seule prestation pour les journées des 2 groupes """
        p = Prestation.objects.create(date=D1, categorie="consommation", label="Journée", montant_initial=10, montant=10, activite=self.activite, tarif=self.tarif_journee,
                                      famille=self.famille, individu=self.enfant, categorie_tarif=self.cat, quantite=1, tarif_ligne=self.tarif_journee.tarifligne_set.first())
        for ins in (self.ins1, self.ins2):
            Consommation.objects.create(individu=self.enfant, inscription=ins, activite=self.activite, date=D1, unite=self.journee, groupe=ins.groupe,
                                        categorie_tarif=self.cat, etat="reservation", prestation=p, date_saisie=datetime.datetime.now())
        self.grille().enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 2)
        self.assertEqual(prestations, [(D1, "Journée", 10.0), (D1, "Journée", 10.0)])
        self.assertEqual(Consommation.objects.values("prestation").distinct().count(), 2)
        self.assertEqual((orph, ml), (0, 0))


class Portail(Communs, Base):
    MODE = "portail"

    # ---------------- Unités masquées sur le portail ----------------

    def test_11_unite_masquee_combinaison(self):
        self.creer_conso(self.ins1, D1, self.journee); self.creer_conso(self.ins1, D1, self.repas)
        avant = self.etat()
        self.masquer(self.repas)
        self.grille([self.ins1]).enregistrer()
        self.assertEqual(self.etat(), avant)
        self.assertEqual(avant[1], [(D1, "Journée + repas", 13.0)])

    def test_12_unite_masquee_sans_combinaison(self):
        self.tarif_journee_repas.delete()
        self.creer_conso(self.ins1, D1, self.journee); self.creer_conso(self.ins1, D1, self.repas)
        avant = self.etat()
        self.masquer(self.repas)
        self.grille([self.ins1]).enregistrer()
        self.assertEqual(self.etat(), avant)
        self.assertEqual(self.montants(), [4.0, 10.0])

    def test_13_unite_masquee_modifications(self):
        self.creer_conso(self.ins1, D1, self.journee); self.creer_conso(self.ins1, D1, self.repas)
        self.masquer(self.repas)
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        g = self.grille([self.ins1]); g.supprimer(self.ins1, D1, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(consos, [(D1, self.ins1.pk, "Repas", "reservation"), (D2, self.ins1.pk, "Journée", "reservation")])
        self.assertEqual(prestations, [(D1, "Repas", 4.0), (D2, "Journée", 10.0)])
        self.assertEqual((orph, ml), (0, 0))

    def test_14_unite_masquee_ajout_combinaison(self):
        self.creer_conso(self.ins1, D1, self.repas)
        self.masquer(self.repas)
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 2)
        self.assertEqual(prestations, [(D1, "Journée + repas", 13.0)])
        self.assertEqual(Consommation.objects.values("prestation").distinct().count(), 1)

    def test_15_unite_masquee_et_double_inscription(self):
        self.creer_conso(self.ins1, D1, self.journee); self.creer_conso(self.ins1, D1, self.repas); self.creer_conso(self.ins2, D1, self.journee)
        self.masquer(self.repas)
        g = self.grille(); g.ajouter(self.ins2, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 4)
        self.assertEqual(self.montants(), [10.0, 10.0, 13.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_16_unite_masquee_prestation_facturee(self):
        self.creer_conso(self.ins1, D1, self.journee); self.creer_conso(self.ins1, D1, self.repas)
        facture = Facture.objects.create(famille=self.famille, numero=1, date_edition=datetime.date(2026, 12, 31), date_debut=datetime.date(2026, 12, 1), date_fin=datetime.date(2026, 12, 31))
        Prestation.objects.update(facture=facture)
        avant = self.etat()
        self.masquer(self.repas)
        self.grille([self.ins1]).enregistrer()
        self.assertEqual(self.etat(), avant)

    # ---------------- Sécurité ----------------

    def test_20_supprimer_conso_autre_famille(self):
        self.creer_conso(self.ins_b, D1, self.journee)
        avant = self.etat(self.famille_b)
        cible = Consommation.objects.get(inscription=self.ins_b)
        g = self.grille(); g.suppressions["consommations"].append(cible.pk); g.suppressions["prestations"].append(cible.prestation_id); g.enregistrer()
        self.assertEqual(self.etat(self.famille_b), avant)

    def test_21_modifier_conso_autre_famille(self):
        self.creer_conso(self.ins_b, D1, self.journee)
        cible = Consommation.objects.get(inscription=self.ins_b)
        def alterer(donnees):
            donnees["consommations"]["x"] = [dict(Grille._dict_conso(None, self.ins_b, D1, self.journee.pk, cible.pk, None), etat="refus", dirty=True)]
        self.grille().enregistrer(alterer)
        cible.refresh_from_db()
        self.assertEqual((cible.etat, cible.prestation_id is not None), ("reservation", True))

    def test_22_ajout_sur_inscription_autre_famille(self):
        def alterer(donnees):
            donnees["consommations"]["x"] = [dict(Grille._dict_conso(None, self.ins_b, D1, self.journee.pk, str(uuid.uuid4()), None), dirty=True)]
        self.grille().enregistrer(alterer)
        self.assertEqual(Consommation.objects.filter(inscription=self.ins_b).count(), 0)

    def test_23_prestation_a_zero_euro(self):
        """ La famille remplace le montant calculé par 0 € """
        def alterer(donnees):
            for dict_prestation in donnees["prestations"].values():
                dict_prestation.update({"montant": 0, "montant_initial": 0})
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.enregistrer(alterer)
        self.assertEqual(self.montants(), [10.0])

    def test_24_reservation_sans_prestation(self):
        """ La famille retire la prestation de sa nouvelle réservation, ou la déclare 'forfait' """
        def alterer(donnees):
            for liste in donnees["consommations"].values():
                for conso in liste:
                    conso.update({"prestation": None, "forfait": 1})
            donnees["prestations"] = {}
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.enregistrer(alterer)
        self.assertEqual(self.montants(), [10.0])
        self.assertEqual(self.etat()[2:], (0, 0))

    def test_25_categorie_tarif_frauduleuse(self):
        g = self.grille(); c = g.ajouter(self.ins1, D1, self.journee, categorie_tarif=self.cat_reduite.pk)
        def alterer(donnees):
            for liste in donnees["consommations"].values():
                for conso in liste:
                    conso["categorie_tarif"] = self.cat_reduite.pk
        g.enregistrer(alterer)
        self.assertEqual(self.montants(), [10.0])
        self.assertEqual(Consommation.objects.get().categorie_tarif_id, self.cat.pk)

    def test_26_ajax_mode_pointeuse(self):
        """ Le mode pointeuse de l'AJAX de facturation enregistre directement : interdit aux familles """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee)
        donnees = g.get_donnees_facturation(); donnees["mode"] = "pointeuse"
        g.facturer(donnees)
        self.assertEqual(Consommation.objects.count(), 0)
        self.assertEqual(Prestation.objects.count(), 0)

    def test_27_ajax_inscription_autre_famille(self):
        """ L'AJAX de facturation ne doit rien révéler des consommations d'une autre famille """
        self.creer_conso(self.ins_b, D1, self.journee)
        g = self.grille()
        donnees = g.get_donnees_facturation()
        donnees["cases_touchees"] = {"x": {"date": D1, "inscription": self.ins_b.pk, "activite": self.activite.pk, "categorie_tarif": self.cat.pk,
                                           "famille": self.famille_b.pk, "individu": self.enfant_b.pk, "groupe": self.g1.pk}}
        retour = g.facturer(donnees)
        self.assertEqual(retour["modifications_conso_masquees"], {})
        self.assertEqual(retour["nouvelles_prestations"], {})

    def test_28_supprimer_conso_pointee(self):
        self.creer_conso(self.ins1, D1, self.journee, etat="present")
        g = self.grille(); g.supprimer(self.ins1, D1, self.journee); g.enregistrer()
        self.assertEqual(self.etat()[0], [(D1, self.ins1.pk, "Journée", "present")])
        self.assertEqual(self.montants(), [10.0])

    def test_29_ajout_etat_interdit(self):
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee, etat="present"); g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 0)

    def test_30_validation_manuelle(self):
        Activite.objects.filter(pk=self.activite.pk).update(validation_type="MANUELLE")
        self.activite.refresh_from_db()
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee, etat="reservation"); g.enregistrer()
        self.assertEqual(Consommation.objects.get().etat, "demande")

    def test_31_conso_omise_par_le_navigateur(self):
        """ Le navigateur n'envoie pas une conso existante (sans la supprimer) : elle doit rester facturée """
        self.creer_conso(self.ins1, D1, self.journee)
        def alterer(donnees):
            donnees["consommations"] = {k: v for k, v in donnees["consommations"].items() if not k.startswith(D1)}
        self.grille().enregistrer(alterer)
        self.assertEqual(len(self.etat()[0]), 1)
        self.assertEqual(self.montants(), [10.0])

    def test_32_suppression_hors_delai(self):
        self.creer_conso(self.ins1, D1, self.journee)
        Activite.objects.filter(pk=self.activite.pk).update(portail_reservations_limite="999#08:00", portail_reservations_limite_suppr="999#08:00")
        g = self.grille(); g.supprimer(self.ins1, D1, self.journee); g.enregistrer()
        self.assertEqual(len(self.etat()[0]), 1)
        self.assertEqual(self.montants(), [10.0])

    def test_33_ajout_hors_delai(self):
        Activite.objects.filter(pk=self.activite.pk).update(portail_reservations_limite="999#08:00")
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 0)

    def test_34_ajout_unite_masquee(self):
        self.masquer(self.repas)
        g = self.grille(); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        self.assertEqual(Consommation.objects.count(), 0)

    def test_35_historique(self):
        """ L'historique trace les ajouts et suppressions faits sur le portail """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        g = self.grille(); g.supprimer(self.ins1, D1, self.journee); g.enregistrer()
        titres = list(Historique.objects.filter(famille=self.famille).values_list("titre", flat=True))
        self.assertIn("Ajout d'une consommation", titres)
        self.assertIn("Suppression d'une consommation", titres)

    def test_40_performance(self):
        """ Période d'un mois, 2 inscriptions, journée + repas tous les jours """
        import time
        dates = [datetime.date(2026, 12, 1) + datetime.timedelta(days=i) for i in range(31)]
        for date in dates:
            for groupe in (self.g1, self.g2):
                for unite in (self.journee, self.repas):
                    Ouverture.objects.get_or_create(date=date, activite=self.activite, groupe=groupe, unite=unite)
        g = self.grille()
        for date in dates:
            for ins in (self.ins1, self.ins2):
                g.ajouter(ins, str(date), self.journee); g.ajouter(ins, str(date), self.repas)
        chrono = time.time(); g.enregistrer(); duree1 = time.time() - chrono
        chrono = time.time(); self.grille().enregistrer(); duree2 = time.time() - chrono
        print("\nPERF : création de 124 conso %.2f s, réenregistrement %.2f s" % (duree1, duree2))
        self.assertEqual(Consommation.objects.count(), 124)
        self.assertEqual(Prestation.objects.count(), 62)


class Gestion(Communs, Base):
    """ Grille de la fiche famille (personnel) : non-régression """
    MODE = "gestion"

    def test_09_performance_mode_date(self):
        """ 400 enfants (dont 50 sur 2 groupes), recalcul complet """
        import time
        consommations, cases = {}, {}
        for i in range(400):
            individu = Individu.objects.create(civilite=4, nom="T", prenom=str(i))
            inscriptions = [Inscription.objects.create(activite=self.activite, groupe=self.g1, categorie_tarif=self.cat, famille=self.famille, individu=individu, date_debut=datetime.date(2026, 1, 1))]
            if i < 50:
                inscriptions.append(Inscription.objects.create(activite=self.activite, groupe=self.g2, categorie_tarif=self.cat, famille=self.famille, individu=individu, date_debut=datetime.date(2026, 1, 1)))
            for ins in inscriptions:
                key = "%s_%s_%s" % (D1, ins.pk, self.journee.pk)
                consommations["%s_%s" % (D1, ins.pk)] = [{"pk": str(uuid.uuid4()), "individu": individu.pk, "inscription": ins.pk, "activite": self.activite.pk, "famille": self.famille.pk,
                    "date": D1, "unite": self.journee.pk, "groupe": ins.groupe_id, "etat": "reservation", "categorie_tarif": self.cat.pk, "prestation": None, "quantite": 1,
                    "evenement": None, "forfait": None, "key_case": key, "options": None, "heure_debut": None, "heure_fin": None}]
                cases[key] = {"date": D1, "inscription": ins.pk, "activite": self.activite.pk, "categorie_tarif": self.cat.pk, "famille": self.famille.pk, "individu": individu.pk, "groupe": ins.groupe_id}
        donnees = {"consommations": consommations, "prestations": {}, "cases_touchees": cases, "mode": "date", "dict_aides": [], "liste_vacances": []}
        chrono = time.time()
        retour = Facturation(donnees=json.loads(json.dumps(donnees))).Facturer()
        print("\nPERF mode date : %d lignes en %.2f s" % (len(cases), time.time() - chrono))
        self.assertEqual(len(retour["nouvelles_prestations"]), 450)

    def test_17_conso_masquees_hors_portail(self):
        f = Facturation(donnees={"mode": "individu", "cases_touchees": {"x": {"date": D1, "inscription": self.ins1.pk}}, "consommations": {}})
        f.Ajouter_conso_masquees()
        self.assertEqual(f.conso_masquees, {})

    def test_18_grille_filtree_sur_un_groupe(self):
        """ Gestionnaire filtré sur le groupe 2 : la journée du groupe 1 ne doit pas disparaître """
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        g = self.grille([self.ins2]); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        g = self.grille([self.ins2]); g.ajouter(self.ins2, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 3)
        self.assertEqual(self.montants(), [10.0, 13.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_19_grille_virtuelle(self):
        """ Traitement par lot / recalcul des prestations : suppression d'une conso puis recalcul complet """
        from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D2, self.journee); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        grille = Grille_virtuelle(request=None, idfamille=self.famille.pk, idindividu=self.enfant.pk, idactivite=self.activite.pk, date_min=datetime.date(2026, 12, 1), date_max=datetime.date(2026, 12, 31))
        grille.Supprimer(criteres={"date": datetime.date(2026, 12, 9)})
        grille.Enregistrer()
        consos, prestations, orph, ml = self.etat()
        self.assertEqual(len(consos), 2)
        self.assertEqual(prestations, [(D1, "Journée", 10.0), (D1, "Journée", 10.0)])
        self.assertEqual((orph, ml), (0, 0))
        avant = self.etat()
        grille = Grille_virtuelle(request=None, idfamille=self.famille.pk, idindividu=self.enfant.pk, idactivite=self.activite.pk, date_min=datetime.date(2026, 12, 1), date_max=datetime.date(2026, 12, 31))
        grille.Recalculer_tout()
        grille.Enregistrer()
        self.assertEqual(self.etat(), avant)
