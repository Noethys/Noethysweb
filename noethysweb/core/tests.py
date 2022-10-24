# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.test import TestCase
from django.urls import reverse
from core.models import *
from django.contrib.auth.models import User


class Classe_commune(TestCase):

    def Connexion_utilisateur(self):
        self.client.login(username="Utilisateur", password="123456")

    def Deconnexion_utilisateur(self):
        self.client.logout()

    def setUp(self):
        """ Remplissage de données fictives """
        # Création d'un utilisateur
        self.utilisateur = User.objects.create_user(username="Utilisateur", password="123456")

        # Création d'une activité
        self.activite_alsh = Activite.objects.create(nom="Accueil de loisirs", date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 12, 31))

        # Création d'un groupe
        self.groupe_alsh = Groupe.objects.create(nom="Groupe unique", ordre=1, activite=self.activite_alsh)

        # Création d'une catégorie de tarif
        self.categorie_tarif_alsh = CategorieTarif.objects.create(nom="Catégorie unique", activite=self.activite_alsh)

        # Création des unités
        self.unite_journee = Unite.objects.create(
            nom="Journée", abrege="J", ordre=1, activite=self.activite_alsh, type="Unitaire",
            date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))

        # Création des ouvertures
        self.ouverture = Ouverture.objects.create(date="2020-01-01", activite=self.activite_alsh, groupe=self.groupe_alsh, unite=self.unite_journee)

        # Création d'une famille
        self.famille = Famille.objects.create()

        # Création des codes pour le portail
        from fiche_famille.utils import utils_internet
        self.famille.internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=self.famille.pk)
        self.famille.internet_mdp = utils_internet.CreationMDP()
        self.famille.save()

        # Création d'un parent titulaire
        self.parent = Individu.objects.create(civilite=1, nom="TEST", prenom="Gérard")
        Rattachement.objects.create(categorie=1, titulaire=True, famille=self.famille, individu=self.parent)

        # Création d'un enfant
        self.enfant = Individu.objects.create(civilite=4, nom="TEST", prenom="Kévin")
        Rattachement.objects.create(categorie=2, titulaire=False, famille=self.famille, individu=self.enfant)
        self.inscription = Inscription.objects.create(
            activite=self.activite_alsh, groupe=self.groupe_alsh, categorie_tarif=self.categorie_tarif_alsh,
            famille=self.famille, individu=self.enfant)

        # Création de consommations
        self.conso = Consommation.objects.create(
            individu=self.enfant, inscription=self.inscription, activite=self.activite_alsh,
            date=datetime.date(2020, 1, 1), etat="reservation", groupe=self.groupe_alsh, unite=self.unite_journee)





class Core(Classe_commune):

    def test_basic_addition(self):
        self.assertEqual(1 + 1, 2)

    def test_accueil_not_authenticated_user(self):
        response = self.client.get(reverse("accueil"))
        # L'utilisateur non authentifié n'est pas renvoyé vers la page d'accueil ?
        self.assertTemplateNotUsed(response, "core/accueil/accueil.html")
        # Un code 302 est renvoyé lorsque l'authentification n'est pas ok
        self.failUnlessEqual(response.status_code, 302)

    def test_accueil_authenticated_user(self):
        # Connexion de l'utilisateur
        self.Connexion_utilisateur()
        # Chargement de la page d'accueil
        response = self.client.get(reverse("accueil"))
        # Un code 200 est bien renvoyé ?
        self.failUnlessEqual(response.status_code, 200)
        # L'utilisateur authentifié est bien renvoyé vers la page d'accueil ?
        self.assertTemplateUsed(response, "core/accueil/accueil.html")
        # Déconnexion de l'utilisateur
        self.Deconnexion_utilisateur()

    def test_urls_ajax(self):
        """ Vérifie la protection des appels ajax """
        from core.urls import urlpatterns
        for url in urlpatterns:
            if "ajax_" in url.name and "/<" not in url.pattern._route:
                response = self.client.get(reverse(url.name))
                self.assertEqual(response.status_code, 302)

