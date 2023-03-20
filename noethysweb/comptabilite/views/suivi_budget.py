# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from collections import Counter
from django.views.generic import TemplateView
from django.db.models import Q, Sum
from core.views.base import CustomView
from core.models import ComptaVentilation, ComptaOperationBudgetaire, ComptaCategorieBudget, ComptaCategorie
from comptabilite.forms.suivi_budget import Formulaire


class View(CustomView, TemplateView):
    menu_code = "suivi_budget"
    template_name = "comptabilite/suivi_budget.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Suivi du budget"
        context['afficher_menu_brothers'] = True
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "afficher_categories_non_budgetees": form.cleaned_data["afficher_categories_non_budgetees"],
            "liste_lignes": json.dumps(liste_lignes),
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        budget = parametres["budget"]
        afficher_categories_non_budgetees = parametres["afficher_categories_non_budgetees"]

        # Importation des catégories
        dict_categories = {categorie.pk: categorie for categorie in ComptaCategorie.objects.all()}

        # Importation des ventilations
        condition = Q(analytique__in=budget.analytiques.all(), date_budget__range=[budget.date_debut, budget.date_fin])
        ventilations_tresorerie = Counter({ventilation["categorie"]: ventilation["total"] for ventilation in ComptaVentilation.objects.values("categorie").filter(condition).annotate(total=Sum("montant"))})
        ventilations_budgetaires = Counter({ventilation["categorie"]: ventilation["total"] for ventilation in ComptaOperationBudgetaire.objects.values("categorie").filter(condition).annotate(total=Sum("montant"))})
        dict_realise = {dict_categories[idcategorie]: montant for idcategorie, montant in dict(ventilations_tresorerie + ventilations_budgetaires).items()}

        # Importation des catégories budgétaires
        categories_budget = list(ComptaCategorieBudget.objects.select_related("categorie").filter(budget=budget))
        dict_budgete = {categorie_budget.categorie: categorie_budget.montant for categorie_budget in categories_budget}

        # Création des lignes de catégories
        categories = {**dict_budgete, **dict_realise}.keys() if afficher_categories_non_budgetees else dict_budgete.keys()
        categories = sorted(categories, key=lambda x: (x.type, x.nom))

        # Création des lignes
        lignes = []
        regroupements = {}
        for categorie in categories:
            # Création du regroupement (débit ou crédit)
            if not categorie.type in regroupements:
                regroupements[categorie.type] = {"id": 1000000 + len(regroupements), "realise": decimal.Decimal(0), "budgete": decimal.Decimal(0)}
                lignes.append({"id": regroupements[categorie.type]["id"], "pid": 0, "regroupement": True, "label": categorie.get_type_display()})

            # Calcul des données de la ligne
            realise = dict_realise.get(categorie, decimal.Decimal(0))
            budgete = dict_budgete.get(categorie, decimal.Decimal(0))
            pourcentage = (float(realise) * 100 / float(budgete)) if budgete else None
            ecart = (budgete - realise) if categorie.type == "debit" else (realise - budgete)

            # Mémorisation pour ligne de total
            regroupements[categorie.type]["realise"] += realise
            regroupements[categorie.type]["budgete"] += budgete

            # Création de la ligne
            lignes.append({"id": categorie.pk, "pid": regroupements[categorie.type]["id"], "regroupement": False,
                           "label": categorie.nom,
                           "realise": float(realise),
                           "budgete": float(budgete),
                           "pourcentage": pourcentage if pourcentage else None,
                           "ecart": float(ecart),
                           })

        # Ligne de total
        total_realise = (regroupements["credit"]["realise"] if "credit" in regroupements else decimal.Decimal(0)) - (regroupements["debit"]["realise"] if "debit" in regroupements else decimal.Decimal(0))
        total_budgete = (regroupements["credit"]["budgete"] if "credit" in regroupements else decimal.Decimal(0)) - (regroupements["debit"]["budgete"] if "debit" in regroupements else decimal.Decimal(0))
        total_pourcentage = (float(total_realise) * 100 / float(total_budgete)) if total_budgete else None
        total_ecart = total_realise - total_budgete

        lignes.append({"id": 99999999, "regroupement": True, "label": "Total"})
        lignes.append({"id": 99999998, "pid": 99999999, "regroupement": False, "label": "", "realise": float(total_realise), "budgete": float(total_budgete),
                       "pourcentage": total_pourcentage if total_pourcentage else None, "ecart": float(total_ecart)})

        return lignes
