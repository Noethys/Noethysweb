# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, random
from colorhash import ColorHash
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils.safestring import mark_safe
from core.views.base import CustomView
from core.models import Sondage, SondageRepondant, SondageQuestion, SondageReponse, SondagePage
from portail.forms.sondage import Formulaire


class Element():
    def __init__(self, *args, **kwargs):
        self.id = random.randint(1, 100000)
        self.categorie = ""


class Camembert(Element):
    def __init__(self, titre="", labels=[], valeurs=[], couleurs=[]):
        Element.__init__(self)
        self.categorie = "camembert"
        self.titre = titre
        self.labels = labels
        self.valeurs = valeurs
        self.couleurs = couleurs or [ColorHash(str(label)).hex for label in self.labels]
        self.nbre_reponses = sum(valeurs)


class Histogramme(Element):
    def __init__(self, titre="", labels=[], type_chart="line", valeurs=[], couleurs=[]):
        Element.__init__(self)
        self.categorie = "histogramme"
        self.type_chart = type_chart # "line" ou "bar"
        self.titre = titre
        self.labels = labels
        self.valeurs = valeurs
        self.couleurs = couleurs or [ColorHash(str(label)).hex for label in self.labels]
        self.nbre_reponses = sum(valeurs)


class Table(Element):
    def __init__(self, titre="", colonnes=[], lignes=[], afficher_entetes_colonnes=True):
        Element.__init__(self)
        self.categorie = "tableau"
        self.titre = titre
        self.colonnes = colonnes
        self.lignes = lignes
        self.afficher_entetes_colonnes = afficher_entetes_colonnes
        self.nbre_reponses = len(lignes)


class Base(CustomView, TemplateView):
    template_name = "individus/sondages/sondages_tableau.html"
    menu_code = "individus_toc"
    type_affichage = None

    def get_context_data(self, **kwargs):
        context = super(Base, self).get_context_data(**kwargs)
        context['page_titre'] = "Formulaires"
        context['box_titre'] = "Consulter les réponses d'un formulaire"
        context['box_introduction'] = "Sélectionnez un formulaire dans la liste déroulante puis choisissez un type d'affichage."

        # Importation des sondages
        context["liste_sondages"] = [(None, "--------")] + [(sondage.pk, sondage.titre) for sondage in Sondage.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("pk")]
        context["idsondage"] = self.Get_idsondage()

        # Type affichage
        context["type_affichage"] = self.type_affichage
        return context

    def Get_idsondage(self):
        return self.kwargs.get("idsondage", None)


class Tableau(Base):
    template_name = "individus/sondages/sondages_tableau.html"
    type_affichage = "tableau"

    def get_context_data(self, **kwargs):
        context = super(Tableau, self).get_context_data(**kwargs)

        # Création des colonnes
        colonnes = [
            {"code": "date_creation", "label": "Création"},
            {"code": "date_modification", "label": "Modification"},
            {"code": "famille", "label": "Famille"},
            {"code": "individu", "label": "Individu"},
        ]
        questions = SondageQuestion.objects.filter(page__sondage_id=self.Get_idsondage()).order_by("page__ordre", "ordre")
        for question in questions:
            colonnes.append({"code": "question_%d" % question.pk, "label": question.label})

        context["colonnes"] = colonnes

        # Création des lignes
        dict_reponses = {(reponse.repondant_id, reponse.question_id): reponse.Get_reponse_fr() for reponse in SondageReponse.objects.select_related("question").filter(question__page__sondage_id=self.Get_idsondage())}
        lignes = []
        for repondant in SondageRepondant.objects.select_related("famille", "individu").filter(sondage_id=self.Get_idsondage()):
            ligne = [
                repondant.date_creation.strftime("%d/%m/%Y %H:%M"),
                repondant.date_modification.strftime("%d/%m/%Y %H:%M") if repondant.date_modification else "",
                repondant.famille.nom,
                repondant.individu.Get_nom() if repondant.individu else "",
            ]
            for question in questions:
                ligne.append(dict_reponses.get((repondant.pk, question.pk), ""))
            lignes.append(ligne)
        context["lignes"] = mark_safe(json.dumps(lignes))
        return context


class Resume(Base):
    template_name = "individus/sondages/sondages_resume.html"
    type_affichage = "resume"

    def get_context_data(self, **kwargs):
        context = super(Resume, self).get_context_data(**kwargs)

        # Importation des réponses
        dict_reponses = {}
        for reponse in SondageReponse.objects.select_related("question").filter(question__page__sondage_id=self.Get_idsondage()):
            reponse_fr = reponse.Get_reponse_fr()
            dict_reponses.setdefault(reponse.question, {})
            reponses = reponse_fr.split(",") if reponse.question.controle == "liste_coches" else [reponse_fr,]
            for rep in reponses:
                if isinstance(rep, str):
                    rep = rep.strip()
                dict_reponses[reponse.question].setdefault(rep, 0)
                dict_reponses[reponse.question][rep] += 1

        # Formatage des résultats
        data = []
        for question in SondageQuestion.objects.filter(page__sondage_id=self.Get_idsondage()).order_by("page__ordre", "ordre"):
            liste_choix = [choix.strip() for choix in question.choix.split(";")] if question.choix else None

            if question.controle == "liste_deroulante":
                data.append(Camembert(
                    titre=question.label,
                    labels=[choix for choix in liste_choix],
                    valeurs=[dict_reponses.get(question, {}).get(choix, 0) for choix in liste_choix],
                ))

            if question.controle == "case_coche":
                data.append(Camembert(
                    titre=question.label,
                    labels=[choix for choix in ("oui", "non")],
                    valeurs=[dict_reponses.get(question, {}).get(choix, 0) for choix in ("oui", "non")],
                ))

            if question.controle == "liste_coches":
                data.append(Histogramme(
                    titre=question.label,
                    type_chart="horizontalBar",
                    labels=[choix for choix in liste_choix],
                    valeurs=[dict_reponses.get(question, {}).get(choix, 0) for choix in liste_choix],
                ))

            if question.controle in ("entier", "slider", "decimal", "montant"):
                liste_valeurs = sorted(dict_reponses.get(question, {}).keys())
                data.append(Histogramme(
                    titre=question.label,
                    type_chart="horizontalBar",
                    labels=[valeur for valeur in liste_valeurs],
                    valeurs=[dict_reponses[question][valeur] for valeur in liste_valeurs],
                ))

            if question.controle in ("ligne_texte", "bloc_texte"):
                data.append(Table(
                    titre=question.label,
                    colonnes=["Colonne 1",],
                    lignes=[[valeur,] for valeur in sorted(dict_reponses.get(question, {}).keys())],
                    afficher_entetes_colonnes=False,
                ))

        context["data"] = data
        return context


class Detail(Base):
    template_name = "individus/sondages/sondages_detail.html"
    type_affichage = "detail"

    def get_context_data(self, **kwargs):
        context = super(Detail, self).get_context_data(**kwargs)
        context["index_repondant"] = self.Get_index()

        # Importation du répondant et des réponses
        repondants = SondageRepondant.objects.filter(sondage_id=self.Get_idsondage()).order_by("pk")
        context["nbre_repondants"] = len(repondants)

        repondant = repondants[self.Get_index()-1] if self.Get_index() <= len(repondants) else None
        context["repondant"] = repondant
        reponses = SondageReponse.objects.select_related("question").filter(repondant=repondant)

        # Création des pages et des formulaires
        liste_pages = []
        questions = SondageQuestion.objects.filter(page__sondage_id=self.Get_idsondage()).order_by("ordre")
        for page in SondagePage.objects.filter(sondage_id=self.Get_idsondage()).order_by("ordre"):
            liste_pages.append((page, Formulaire(request=self.request, page=page, questions=questions, reponses=reponses, lecture_seule=True)))
        context["pages"] = liste_pages

        return context

    def Get_index(self):
        return self.kwargs.get("index", 1)
