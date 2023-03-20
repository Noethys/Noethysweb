# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import decimal, datetime
from django.db.models import Q, Sum
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import CompteBancaire, ComptaOperation


class View(CustomView, TemplateView):
    menu_code = "suivi_tresorerie"
    template_name = "comptabilite/suivi_tresorerie.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Suivi de la trésorerie"
        context["categorie"] = self.Get_categorie()
        context['label_categorie'] = "Compte"
        context['liste_categories'] = [(item.pk, item.nom) for item in CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")]
        if not context['liste_categories']:
            context['box_introduction'] = "<b>Vous devez avoir enregistré au moins un compte bancaire avant de pouvoir ajouter des opérations !</b>"
        context['donnees'] = self.Get_donnees_graphique()
        return context

    def test_func_page(self):
        # Vérifie que l'utilisateur a une permission d'accéder à ce compte
        idcompte = self.Get_categorie()
        if idcompte and idcompte not in [compte.pk for compte in CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))]:
            return False
        return True

    def Get_categorie(self):
        idcompte = self.kwargs.get('categorie', None)
        if idcompte:
            return idcompte
        compte = CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")
        return compte[0].pk if compte else 0

    def Get_donnees_graphique(self):
        idcompte = self.Get_categorie()
        if not idcompte:
            return []

        periode = [datetime.date.today() - datetime.timedelta(days=60), datetime.date.today() + datetime.timedelta(days=60)]

        # Calcul du solde à la date de début de la période
        credit = ComptaOperation.objects.filter(compte_id=idcompte, date__lt=periode[0], type="credit").aggregate(solde=Sum("montant"))
        debit = ComptaOperation.objects.filter(compte_id=idcompte, date__lt=periode[0], type="debit").aggregate(solde=Sum("montant"))
        solde_debut_periode = (credit["solde"] or decimal.Decimal(0)) - (debit["solde"] or decimal.Decimal(0))
        solde = solde_debut_periode

        # Importation des opérations de trésorerie
        dict_soldes = {}
        for operation in ComptaOperation.objects.filter(compte_id=idcompte, date__range=periode).order_by("date"):
            montant_operation = operation.montant if operation.type == "credit" else -operation.montant
            dict_soldes.setdefault(operation.date, solde)
            dict_soldes[operation.date] += montant_operation
            solde += montant_operation

        resultats = [(date, float(solde)) for date, solde in dict_soldes.items()]
        if resultats:
            resultats.append((periode[1], resultats[-1][1]))

        return resultats
