# -*- coding: utf-8 -*-
# Tests de non-régression : disparition de consommations à l'enregistrement de la grille du portail
# - plusieurs inscriptions du même individu sur la même activité (groupes différents)
# - unités masquées sur le portail (non visibles ou absentes des unités de la période)
# Le simulateur reproduit le parcours JS du portail : chargement -> tout_recalculer() -> ajax_facturer() -> submit -> Save_grille()

import datetime, json, uuid
from django.test import TestCase
from core.models import Structure, Activite, Groupe, CategorieTarif, Unite, Famille, Individu, Inscription, NomTarif, Tarif, CombiTarif, TarifLigne, Consommation, Prestation, Facture
from consommations.views.grille import Facturation, Save_grille


D1, D2, D3 = "2026-11-04", "2026-11-12", "2026-11-18"


class Grille:
    """ Simule la grille JS (dict_cases, dict_prestations, dict_suppressions) """
    def __init__(self, famille, individu, activite, inscriptions, unites_masquees=[]):
        self.famille, self.individu, self.activite, self.inscriptions = famille, individu, activite, inscriptions
        self.conso_masquees = {}
        self.suppressions = {"consommations": [], "prestations": [], "memos": []}
        self.cases = {}
        for conso in Consommation.objects.filter(inscription__in=inscriptions).exclude(unite__in=unites_masquees):
            key = "%s_%s_%s" % (conso.date, conso.inscription_id, conso.unite_id)
            self.cases.setdefault(key, []).append(self._dict_conso(conso.inscription, str(conso.date), conso.unite_id, conso.pk, conso.prestation_id))
        self.prestations = {}
        for p in Prestation.objects.filter(famille=famille, individu=individu, activite=activite):
            self.prestations[str(p.pk)] = {
                "date": str(p.date), "categorie": p.categorie, "label": p.label, "montant_initial": float(p.montant_initial), "montant": float(p.montant),
                "activite": p.activite_id, "tarif": p.tarif_id, "facture": p.facture_id, "famille": p.famille_id, "individu": p.individu_id,
                "categorie_tarif": p.categorie_tarif_id, "temps_facture": None, "quantite": p.quantite, "tarif_ligne": p.tarif_ligne_id, "tva": None,
                "code_compta": None, "aides": [], "forfait_date_debut": None, "forfait_date_fin": None, "forfait": p.forfait, "dirty": False}

    def _dict_conso(self, inscription, date, idunite, pk, prestation):
        return {"pk": pk, "individu": inscription.individu_id, "inscription": inscription.pk, "activite": inscription.activite_id, "famille": inscription.famille_id,
                "date": date, "unite": idunite, "groupe": inscription.groupe_id, "heure_debut": None, "heure_fin": None, "etat": "reservation",
                "categorie_tarif": inscription.categorie_tarif_id, "prestation": prestation, "quantite": 1, "evenement": None, "badgeage_debut": None,
                "badgeage_fin": None, "forfait": None, "dirty": False, "facture": None, "options": None, "extra": None}

    def ajouter(self, inscription, date, unite):
        self.cases["%s_%s_%s" % (date, inscription.pk, unite.pk)] = [self._dict_conso(inscription, date, unite.pk, str(uuid.uuid4()), None)]

    def supprimer(self, inscription, date, unite):
        key = "%s_%s_%s" % (date, inscription.pk, unite.pk)
        for conso in self.cases[key]:
            if "-" not in str(conso["pk"]):
                self.suppressions["consommations"].append(conso["pk"])
        self.cases[key] = []  # La case reste dans dict_cases (vide), comme dans le JS

    def enregistrer(self):
        """ Bouton Enregistrer du portail : tout_recalculer() puis submit """
        import os
        if os.environ.get("ORDRE_INVERSE"):
            self.cases = dict(reversed(list(self.cases.items())))
        cases_touchees, vus = {}, set()
        for key, consos in self.cases.items():
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
        donnees = json.loads(json.dumps({"consommations": consommations, "prestations": prestations, "dict_aides": [], "cases_touchees": cases_touchees,
                                         "liste_vacances": [], "dict_suppressions": self.suppressions, "mode": "portail", "activite": self.activite.pk}))
        retour = json.loads(json.dumps(Facturation(donnees=donnees).Facturer()))

        # Traitement du retour (ajax_facturer)
        self.prestations.update(retour["nouvelles_prestations"])
        for idprestation in retour["anciennes_prestations"]:
            if "-" not in str(idprestation):
                self.suppressions["prestations"].append(int(idprestation))
            self.prestations.pop(str(idprestation), None)
        self.conso_masquees.update(retour.get("modifications_conso_masquees", {}))
        for key, idprestation in retour["modifications_idprestation"].items():
            if self.cases.get(key):
                self.cases[key][0].update({"prestation": idprestation, "dirty": True})

        # Submit (validation_form + Save_grille)
        donnees = json.loads(json.dumps({"activite": self.activite.pk, "ancienne_activite": self.activite.pk, "consommations": self.cases,
                                         "memos": {}, "suppressions": self.suppressions, "prestations": self.prestations,
                                         "conso_masquees": self.conso_masquees}))
        Save_grille(request=None, donnees=donnees)


class DoubleInscription(TestCase):

    def setUp(self):
        self.structure = Structure.objects.create(nom="Structure")
        self.activite = Activite.objects.create(structure=self.structure, nom="ALSH", date_debut=datetime.date(2020, 1, 1), date_fin=datetime.date(2999, 12, 31))
        self.g1 = Groupe.objects.create(nom="Maternels", ordre=1, activite=self.activite)
        self.g2 = Groupe.objects.create(nom="Primaires", ordre=2, activite=self.activite)
        self.cat = CategorieTarif.objects.create(nom="Unique", activite=self.activite)
        kw = dict(activite=self.activite, type="Unitaire", date_debut=datetime.date(2020, 1, 1), date_fin=datetime.date(2999, 1, 1))
        self.journee = Unite.objects.create(nom="Journée", abrege="J", ordre=1, **kw)
        self.repas = Unite.objects.create(nom="Repas", abrege="R", ordre=2, **kw)
        self.tarif_journee = self.creer_tarif("Journée", [self.journee], 10)
        self.tarif_repas = self.creer_tarif("Repas", [self.repas], 4)
        self.tarif_journee_repas = self.creer_tarif("Journée + repas", [self.journee, self.repas], 13)
        self.famille = Famille.objects.create()
        self.enfant = Individu.objects.create(civilite=4, nom="TEST", prenom="Kévin")
        self.ins1 = Inscription.objects.create(activite=self.activite, groupe=self.g1, categorie_tarif=self.cat, famille=self.famille, individu=self.enfant, date_debut=datetime.date(2026, 1, 1))
        self.ins2 = Inscription.objects.create(activite=self.activite, groupe=self.g2, categorie_tarif=self.cat, famille=self.famille, individu=self.enfant, date_debut=datetime.date(2026, 1, 1))

    def creer_tarif(self, nom, unites, montant):
        nom_tarif = NomTarif.objects.create(activite=self.activite, nom=nom)
        tarif = Tarif.objects.create(activite=self.activite, nom_tarif=nom_tarif, date_debut=datetime.date(2020, 1, 1), type="JOURN", methode="montant_unique", etats=["reservation", "present", "absenti"])
        tarif.categories_tarifs.add(self.cat)
        combi = CombiTarif.objects.create(tarif=tarif, type="JOURN")
        combi.unites.set(unites)
        TarifLigne.objects.create(activite=self.activite, tarif=tarif, code="montant_unique", num_ligne=0, montant_unique=montant)
        return tarif

    def grille(self, inscriptions=None, unites_masquees=[]):
        return Grille(self.famille, self.enfant, self.activite, inscriptions or [self.ins1, self.ins2], unites_masquees=unites_masquees)

    def etat(self):
        consos = sorted((str(c.date), c.inscription_id, c.unite.nom) for c in Consommation.objects.all())
        prestations = sorted((str(p.date), p.label, float(p.montant)) for p in Prestation.objects.all())
        orphelines = Consommation.objects.filter(prestation__isnull=True).count()
        mauvais_lien = Consommation.objects.exclude(prestation__isnull=True).exclude(prestation_id__in=Prestation.objects.values("pk")).count()
        return consos, prestations, orphelines, mauvais_lien

    # ------------------------------------------------------------------------------------

    def test_1_deux_groupes_unites_differentes(self):
        """ Journée sur le groupe 1, repas sur le groupe 2, même date. Puis la famille ajoute une journée à une autre date. """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.repas); g.enregistrer()
        g = self.grille(); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 1", consos, prestations, orph, ml)
        self.assertEqual(len(consos), 3)
        self.assertEqual(sorted(p[2] for p in prestations), [4.0, 10.0, 10.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_2_deux_groupes_meme_unite(self):
        """ Journée sur les 2 groupes à la même date (même tarif) : 2 prestations attendues. Puis modification ailleurs. """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        etat1 = self.etat()
        g = self.grille(); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 2 après 1er enregistrement", etat1, "\n       après 2e enregistrement", consos, prestations, orph, ml)
        self.assertEqual(len(consos), 3)
        self.assertEqual(len(prestations), 3)
        self.assertEqual(Consommation.objects.filter(date=D1).values("prestation").distinct().count(), 2)
        self.assertEqual((orph, ml), (0, 0))

    def test_3_suppression_sur_une_ligne(self):
        """ Suppression du repas du groupe 2 : sa prestation doit partir, la journée du groupe 1 doit rester. """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.repas); g.enregistrer()
        g = self.grille(); g.supprimer(self.ins2, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 3", consos, prestations, orph, ml)
        self.assertEqual(consos, [(D1, self.ins1.pk, "Journée")])
        self.assertEqual(prestations, [(D1, "Journée", 10.0)])
        self.assertEqual((orph, ml), (0, 0))

    def test_4_enregistrements_successifs_stables(self):
        """ 3 enregistrements sans modification ne doivent rien changer (ni conso, ni prestation). """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.ajouter(self.ins2, D2, self.repas); g.enregistrer()
        avant = self.etat(); ids_avant = sorted(Prestation.objects.values_list("pk", flat=True))
        for _ in range(3):
            self.grille().enregistrer()
        print("\nTEST 4", self.etat())
        self.assertEqual(self.etat(), avant)
        self.assertEqual(sorted(Prestation.objects.values_list("pk", flat=True)), ids_avant)

    # ---------------- Non-régression : un seul groupe ----------------

    def test_5_une_inscription_combinaison(self):
        """ Une seule inscription : journée puis ajout du repas -> la prestation Journée est remplacée par Journée + repas. """
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 5", consos, prestations, orph, ml)
        self.assertEqual(len(consos), 2)
        self.assertEqual(prestations, [(D1, "Journée + repas", 13.0)])
        self.assertEqual((orph, ml), (0, 0))

    def test_6_une_inscription_suppression(self):
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        g = self.grille([self.ins1]); g.supprimer(self.ins1, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 6", consos, prestations, orph, ml)
        self.assertEqual(consos, [(D1, self.ins1.pk, "Journée")])
        self.assertEqual(prestations, [(D1, "Journée", 10.0)])

    def test_7_deux_groupes_combinaison_sur_une_ligne(self):
        """ Groupe 1 : journée + repas (combinaison), groupe 2 : journée. """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        g = self.grille(); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 7", consos, prestations, orph, ml)
        self.assertEqual(len(consos), 3)
        self.assertEqual(sorted(p[2] for p in prestations), [10.0, 13.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_8_prestation_facturee(self):
        """ Prestation du groupe 2 facturée, puis modification sur le groupe 1 le même jour. """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        p2 = Consommation.objects.get(inscription=self.ins2).prestation
        facture = Facture.objects.create(famille=self.famille, numero=1, date_edition=datetime.date(2026, 11, 30), date_debut=datetime.date(2026, 11, 1), date_fin=datetime.date(2026, 11, 30))
        Prestation.objects.filter(pk=p2.pk).update(facture=facture)
        g = self.grille(); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 8", consos, prestations, orph, ml)
        self.assertTrue(Prestation.objects.filter(pk=p2.pk).exists())
        self.assertEqual(Consommation.objects.get(inscription=self.ins2).prestation_id, p2.pk)
        self.assertEqual(len(consos), 3)
        self.assertEqual((orph, ml), (0, 0))

    def test_9_performance(self):
        """ Grille de gestion en mode date : 400 enfants (dont 50 sur 2 groupes), recalcul complet """
        import time
        from consommations.views.grille import Facturation
        consommations, cases = {}, {}
        for i in range(400):
            individu = Individu.objects.create(civilite=4, nom="T", prenom=str(i))
            inscriptions = [Inscription.objects.create(activite=self.activite, groupe=self.g1, categorie_tarif=self.cat, famille=self.famille, individu=individu, date_debut=datetime.date(2026, 1, 1))]
            if i < 50:
                inscriptions.append(Inscription.objects.create(activite=self.activite, groupe=self.g2, categorie_tarif=self.cat, famille=self.famille, individu=individu, date_debut=datetime.date(2026, 1, 1)))
            for ins in inscriptions:
                key = "%s_%s_%s" % (D1, ins.pk, self.journee.pk)
                conso = {"pk": str(uuid.uuid4()), "individu": individu.pk, "inscription": ins.pk, "activite": self.activite.pk, "famille": self.famille.pk, "date": D1,
                         "unite": self.journee.pk, "groupe": ins.groupe_id, "etat": "reservation", "categorie_tarif": self.cat.pk, "prestation": None, "quantite": 1,
                         "evenement": None, "forfait": None, "key_case": key, "options": None, "heure_debut": None, "heure_fin": None}
                consommations["%s_%s" % (D1, ins.pk)] = [conso]
                cases[key] = {"date": D1, "inscription": ins.pk, "activite": self.activite.pk, "categorie_tarif": self.cat.pk, "famille": self.famille.pk, "individu": individu.pk, "groupe": ins.groupe_id}
        donnees = {"consommations": consommations, "prestations": {}, "cases_touchees": cases, "mode": "date", "dict_aides": [], "liste_vacances": []}
        chrono = time.time()
        retour = Facturation(donnees=json.loads(json.dumps(donnees))).Facturer()
        print("\nTEST 9 : %d lignes facturées en %.2f s, %d prestations créées" % (len(cases), time.time() - chrono, len(retour["nouvelles_prestations"])))
        self.assertEqual(len(retour["nouvelles_prestations"]), 450)

    def test_10_donnees_existantes_prestation_partagee(self):
        """ Données abîmées par l'ancien bug : une seule prestation pour les journées des 2 groupes. """
        p = Prestation.objects.create(date=D1, categorie="consommation", label="Journée", montant_initial=10, montant=10, activite=self.activite, tarif=self.tarif_journee,
                                      famille=self.famille, individu=self.enfant, categorie_tarif=self.cat, quantite=1, tarif_ligne=self.tarif_journee.tarifligne_set.first())
        for ins in (self.ins1, self.ins2):
            Consommation.objects.create(individu=self.enfant, inscription=ins, activite=self.activite, date=D1, unite=self.journee, groupe=ins.groupe, categorie_tarif=self.cat, etat="reservation", prestation=p, date_saisie=datetime.datetime.now())
        self.grille().enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 10", consos, prestations, orph, ml)
        self.assertEqual(len(consos), 2)
        self.assertEqual(prestations, [(D1, "Journée", 10.0), (D1, "Journée", 10.0)])
        self.assertEqual(Consommation.objects.values("prestation").distinct().count(), 2)
        self.assertEqual((orph, ml), (0, 0))

    # ---------------- Unités masquées sur le portail ----------------

    def test_11_unite_masquee_combinaison(self):
        """ Journée + repas saisis par le personnel (tarif combiné), repas masqué sur le portail, la famille enregistre sans rien changer """
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        avant = self.etat()
        self.grille([self.ins1], unites_masquees=[self.repas]).enregistrer()
        print("\nTEST 11", self.etat())
        self.assertEqual(self.etat(), avant)
        self.assertEqual(avant[1], [(D1, "Journée + repas", 13.0)])

    def test_12_unite_masquee_sans_combinaison(self):
        self.tarif_journee_repas.delete()
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        avant = self.etat()
        self.grille([self.ins1], unites_masquees=[self.repas]).enregistrer()
        print("\nTEST 12", self.etat())
        self.assertEqual(self.etat(), avant)
        self.assertEqual(sorted(p[2] for p in avant[1]), [4.0, 10.0])

    def test_13_unite_masquee_modifications(self):
        """ La famille ajoute une journée à une autre date puis supprime la journée du D1 : le repas masqué reste, facturé seul """
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        g = self.grille([self.ins1], unites_masquees=[self.repas]); g.ajouter(self.ins1, D2, self.journee); g.enregistrer()
        g = self.grille([self.ins1], unites_masquees=[self.repas]); g.supprimer(self.ins1, D1, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 13", consos, prestations, orph, ml)
        self.assertEqual(consos, [(D1, self.ins1.pk, "Repas"), (D2, self.ins1.pk, "Journée")])
        self.assertEqual(prestations, [(D1, "Repas", 4.0), (D2, "Journée", 10.0)])
        self.assertEqual((orph, ml), (0, 0))

    def test_14_unite_masquee_ajout_combinaison(self):
        """ Repas masqué saisi seul par le personnel, la famille ajoute la journée : bascule sur le tarif combiné """
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        g = self.grille([self.ins1], unites_masquees=[self.repas]); g.ajouter(self.ins1, D1, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 14", consos, prestations, orph, ml)
        self.assertEqual(len(consos), 2)
        self.assertEqual(prestations, [(D1, "Journée + repas", 13.0)])
        self.assertEqual(Consommation.objects.values("prestation").distinct().count(), 1)
        self.assertEqual((orph, ml), (0, 0))

    def test_15_unite_masquee_et_double_inscription(self):
        """ Groupe 1 : journée + repas masqué, groupe 2 : journée. La famille ajoute une journée ailleurs. """
        g = self.grille(); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D1, self.repas); g.ajouter(self.ins2, D1, self.journee); g.enregistrer()
        avant = self.etat()
        g = self.grille(unites_masquees=[self.repas]); g.ajouter(self.ins2, D2, self.journee); g.enregistrer()
        consos, prestations, orph, ml = self.etat()
        print("\nTEST 15", consos, prestations, orph, ml)
        self.assertEqual(len(consos), 4)
        self.assertEqual(sorted(p[2] for p in prestations), [10.0, 10.0, 13.0])
        self.assertEqual((orph, ml), (0, 0))

    def test_16_unite_masquee_prestation_facturee(self):
        """ Prestation Journée + repas facturée : rien ne doit bouger """
        g = self.grille([self.ins1]); g.ajouter(self.ins1, D1, self.journee); g.ajouter(self.ins1, D1, self.repas); g.enregistrer()
        facture = Facture.objects.create(famille=self.famille, numero=1, date_edition=datetime.date(2026, 11, 30), date_debut=datetime.date(2026, 11, 1), date_fin=datetime.date(2026, 11, 30))
        Prestation.objects.update(facture=facture)
        avant = self.etat()
        self.grille([self.ins1], unites_masquees=[self.repas]).enregistrer()
        print("\nTEST 16", self.etat())
        self.assertEqual(self.etat(), avant)

    def test_17_mode_gestion_inchange(self):
        """ Hors portail, aucune conso masquée n'est ajoutée """
        from consommations.views.grille import Facturation
        f = Facturation(donnees={"mode": "individu", "cases_touchees": {"x": {"date": D1, "inscription": self.ins1.pk}}, "consommations": {}})
        f.Ajouter_conso_masquees()
        self.assertEqual(f.conso_masquees, {})
