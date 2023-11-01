# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.views.generic import TemplateView
from django.db.models import Sum
from core.views.base import CustomView
from core.models import Reglement
from core.utils import utils_dates
from reglements.forms.reglements_lot_factures import Formulaire


class View(CustomView, TemplateView):
    menu_code = "reglements_lot_factures"
    template_name = "reglements/reglements_lot_factures.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Règlements associés à un lot de factures"
        context['afficher_menu_brothers'] = True
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        titre = form.cleaned_data["lot_factures"].nom if form.cleaned_data["lot_factures"] else ""
        context = {
            "form_parametres": form,
            "liste_lignes": json.dumps(liste_lignes),
            "titre": titre,
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        lot_factures = parametres["lot_factures"]
        if not lot_factures:
            return []

        # Importation des règlements
        reglements = Reglement.objects.select_related("famille", "mode", "emetteur", "payeur").filter(ventilation__prestation__facture__lot=lot_factures).annotate(part_lot=Sum("ventilation__montant"))

        liste_lignes = []
        for reglement in reglements:
            liste_lignes.append({
                "idreglement": reglement.pk,
                "date": utils_dates.ConvertDateToFR(reglement.date),
                "mode": reglement.mode.label,
                "emetteur": reglement.emetteur.nom if reglement.emetteur else "",
                "numero_piece": reglement.numero_piece,
                "famille": reglement.famille.nom,
                "payeur": reglement.payeur.nom,
                "montant": float(reglement.montant),
                "part_lot": float(reglement.part_lot)
            })

        return liste_lignes
