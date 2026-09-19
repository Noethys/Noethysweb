# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from core.models import *
from core.tests import Classe_commune
from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
from consommations.views.grille import Facturation


class Consommations(Classe_commune):

    def test_urls_ajax(self):
        from consommations.urls import urlpatterns
        for url in urlpatterns:
            if "ajax_" in url.name and "/<" not in url.pattern._route:
                response = self.client.get(reverse(url.name))
                self.assertEqual(response.status_code, 302)


class GrilleVirtuelleSuppressions(TestCase):

    @patch("consommations.utils.utils_grille_virtuelle.Save_grille")
    @patch("consommations.utils.utils_grille_virtuelle.Facturation")
    def test_transmet_les_suppressions_avant_le_recalcul(self, facturation_mock, save_grille_mock):
        grille = object.__new__(Grille_virtuelle)
        grille.request = None
        grille.chrono = 0
        grille.conso_supprimees = [42]
        grille.data_initial = {
            "selection_activite": None,
            "prestations": {},
            "consommations": {},
            "dict_suppressions": {"consommations": [], "prestations": [], "memos": []},
        }
        facturation_mock.return_value.Facturer.return_value = {
            "modifications_idprestation": {},
            "nouvelles_prestations": {},
            "anciennes_prestations": [],
        }

        grille.Enregistrer()

        donnees_facturation = facturation_mock.call_args.kwargs["donnees"]
        self.assertEqual(donnees_facturation["dict_suppressions"]["consommations"], [42])
        save_grille_mock.assert_called_once()


class ForfaitsCredits(Classe_commune):

    def creer_tarif_credit(self, beneficiaire="individu", quantite_max=4):
        nom_tarif = NomTarif.objects.create(activite=self.activite_alsh, nom="Forfait crédit")
        tarif = Tarif.objects.create(
            activite=self.activite_alsh,
            type="CREDIT",
            nom_tarif=nom_tarif,
            date_debut=datetime.date(2020, 1, 1),
            forfait_beneficiaire=beneficiaire,
            methode="montant_unique",
        )
        tarif.categories_tarifs.add(self.categorie_tarif_alsh)
        combinaison = CombiTarif.objects.create(tarif=tarif, type="CREDIT", quantite_max=quantite_max)
        combinaison.unites.add(self.unite_journee)
        tarif.combi_retenue = [self.unite_journee.pk]
        tarif.combinaison = combinaison
        return tarif

    def creer_prestation_forfait(self, tarif, individu=None, date_fin=datetime.date(2020, 1, 4)):
        prestation = Prestation.objects.create(
            date=datetime.date(2020, 1, 1),
            categorie="consommation",
            label="Forfait crédit",
            montant_initial=10,
            montant=10,
            activite=self.activite_alsh,
            tarif=tarif,
            famille=self.famille,
            individu=individu,
            categorie_tarif=self.categorie_tarif_alsh,
            forfait_date_debut=datetime.date(2020, 1, 1),
            forfait_date_fin=date_fin,
        )
        return {
            "date": "2020-01-01",
            "activite": self.activite_alsh.pk,
            "tarif": tarif.pk,
            "famille": self.famille.pk,
            "individu": individu.pk if individu else None,
            "forfait_date_debut": "2020-01-01",
            "forfait_date_fin": date_fin.strftime("%Y-%m-%d"),
        }, prestation

    def creer_conso(self, date, individu, inscription, famille=None, activite=None, unite=None):
        return {
            "date": date.strftime("%Y-%m-%d"),
            "activite": (activite or self.activite_alsh).pk,
            "famille": (famille or self.famille).pk,
            "individu": individu.pk,
            "inscription": inscription.pk,
            "unite": (unite or self.unite_journee).pk,
        }

    def compter(self, tarif, prestation_id, prestations, consommations, dict_suppressions=None):
        facturation = Facturation({
            "prestations": prestations,
            "consommations": consommations,
            "dict_suppressions": dict_suppressions or {},
        })
        return facturation.Compte_quantite_forfait_credit(tarif=tarif, IDprestationForfait=prestation_id)

    def test_periode_reelle_du_forfait_exclut_les_consommations_hors_periode(self):
        tarif = self.creer_tarif_credit()
        dict_prestation, prestation = self.creer_prestation_forfait(tarif, individu=self.enfant)
        consommations = {}
        for jour in range(1, 6):
            conso = self.creer_conso(datetime.date(2020, 1, jour), self.enfant, self.inscription)
            consommations.setdefault("%s_%s" % (conso["date"], self.inscription.pk), []).append(conso)

        quantite = self.compter(tarif, prestation.pk, {str(prestation.pk): dict_prestation}, consommations)

        self.assertEqual(quantite, 4)
        self.assertLessEqual(quantite, tarif.combinaison.quantite_max)

    def test_consommations_deja_enregistrees_respectent_la_periode_et_sont_dedoublonnees(self):
        tarif = self.creer_tarif_credit()
        dict_prestation, prestation = self.creer_prestation_forfait(tarif, individu=self.enfant)
        for jour in range(1, 5):
            valeurs = {
                "individu": self.enfant,
                "inscription": self.inscription,
                "activite": self.activite_alsh,
                "date": datetime.date(2020, 1, jour),
                "etat": "reservation",
                "groupe": self.groupe_alsh,
                "unite": self.unite_journee,
                "prestation": prestation,
                "categorie_tarif": self.categorie_tarif_alsh,
                "date_saisie": datetime.datetime.now(),
            }
            Consommation.objects.create(**valeurs)
            if jour == 1:
                Consommation.objects.create(**valeurs)
        valeurs["date"] = datetime.date(2020, 1, 5)
        Consommation.objects.create(**valeurs)

        quantite = self.compter(tarif, prestation.pk, {str(prestation.pk): dict_prestation}, {})

        self.assertEqual(quantite, 4)

    def test_consommation_supprimee_de_la_grille_n_est_pas_recomptee_depuis_la_base(self):
        tarif = self.creer_tarif_credit()
        dict_prestation, prestation = self.creer_prestation_forfait(tarif, individu=self.enfant)
        consommations_creees = []
        for jour in range(1, 5):
            consommations_creees.append(Consommation.objects.create(
                individu=self.enfant,
                inscription=self.inscription,
                activite=self.activite_alsh,
                date=datetime.date(2020, 1, jour),
                etat="reservation",
                groupe=self.groupe_alsh,
                unite=self.unite_journee,
                prestation=prestation,
                categorie_tarif=self.categorie_tarif_alsh,
                date_saisie=datetime.datetime.now(),
            ))

        quantite = self.compter(
            tarif,
            prestation.pk,
            {str(prestation.pk): dict_prestation},
            {},
            dict_suppressions={"consommations": [consommations_creees[-1].pk]},
        )

        self.assertEqual(quantite, 3)

    def test_consommations_historiques_incompletes_sont_ignorees(self):
        tarif = self.creer_tarif_credit()
        dict_prestation, prestation = self.creer_prestation_forfait(tarif, individu=self.enfant)
        valeurs = {
            "individu": self.enfant,
            "inscription": self.inscription,
            "activite": self.activite_alsh,
            "date": datetime.date(2020, 1, 1),
            "etat": "reservation",
            "groupe": self.groupe_alsh,
            "unite": self.unite_journee,
            "prestation": prestation,
            "categorie_tarif": self.categorie_tarif_alsh,
            "date_saisie": datetime.datetime.now(),
        }
        Consommation.objects.create(**valeurs)
        Consommation.objects.create(**{**valeurs, "unite": None})
        Consommation.objects.create(**{
            **valeurs,
            "date": datetime.date(2020, 1, 2),
            "inscription": None,
        })

        quantite = self.compter(tarif, prestation.pk, {str(prestation.pk): dict_prestation}, {})

        self.assertEqual(quantite, 1)

    def test_cinquieme_consommation_dans_la_periode_epuise_le_forfait(self):
        tarif = self.creer_tarif_credit()
        dict_prestation, prestation = self.creer_prestation_forfait(tarif, individu=self.enfant, date_fin=datetime.date(2020, 1, 5))
        consommations = {}
        for jour in range(1, 6):
            conso = self.creer_conso(datetime.date(2020, 1, jour), self.enfant, self.inscription)
            consommations.setdefault("jour_%d" % jour, []).append(conso)

        quantite = self.compter(tarif, prestation.pk, {str(prestation.pk): dict_prestation}, consommations)

        self.assertEqual(quantite, 5)
        self.assertGreater(quantite, tarif.combinaison.quantite_max)

    def test_forfait_individuel_isole_les_enfants(self):
        enfant_b = Individu.objects.create(civilite=4, nom="TEST", prenom="Léa")
        Rattachement.objects.create(categorie=2, titulaire=False, famille=self.famille, individu=enfant_b)
        inscription_b = Inscription.objects.create(
            activite=self.activite_alsh, groupe=self.groupe_alsh, categorie_tarif=self.categorie_tarif_alsh,
            famille=self.famille, individu=enfant_b, date_debut=datetime.date(1977, 1, 1))
        tarif = self.creer_tarif_credit()
        dict_prestation_a, prestation_a = self.creer_prestation_forfait(tarif, individu=self.enfant)
        dict_prestation_b, prestation_b = self.creer_prestation_forfait(tarif, individu=enfant_b)
        consommations = {}
        for jour in range(1, 5):
            conso_a = self.creer_conso(datetime.date(2020, 1, jour), self.enfant, self.inscription)
            conso_b = self.creer_conso(datetime.date(2020, 1, jour), enfant_b, inscription_b)
            consommations.setdefault("a_%d" % jour, []).append(conso_a)
            consommations.setdefault("b_%d" % jour, []).append(conso_b)

        quantite_a = self.compter(tarif, prestation_a.pk, {str(prestation_a.pk): dict_prestation_a}, consommations)
        quantite_b = self.compter(tarif, prestation_b.pk, {str(prestation_b.pk): dict_prestation_b}, consommations)

        self.assertEqual(quantite_a, 4)
        self.assertEqual(quantite_b, 4)

    def test_forfait_famille_compte_les_consommations_de_tous_les_enfants(self):
        enfant_b = Individu.objects.create(civilite=4, nom="TEST", prenom="Léa")
        Rattachement.objects.create(categorie=2, titulaire=False, famille=self.famille, individu=enfant_b)
        inscription_b = Inscription.objects.create(
            activite=self.activite_alsh, groupe=self.groupe_alsh, categorie_tarif=self.categorie_tarif_alsh,
            famille=self.famille, individu=enfant_b, date_debut=datetime.date(1977, 1, 1))
        tarif = self.creer_tarif_credit(beneficiaire="famille")
        dict_prestation, prestation = self.creer_prestation_forfait(tarif)
        consommations = {}
        for jour in range(1, 5):
            conso_a = self.creer_conso(datetime.date(2020, 1, jour), self.enfant, self.inscription)
            conso_b = self.creer_conso(datetime.date(2020, 1, jour), enfant_b, inscription_b)
            consommations.setdefault("a_%d" % jour, []).append(conso_a)
            consommations.setdefault("b_%d" % jour, []).append(conso_b)

        quantite = self.compter(tarif, prestation.pk, {str(prestation.pk): dict_prestation}, consommations)

        self.assertEqual(quantite, 8)
        self.assertGreater(quantite, tarif.combinaison.quantite_max)
