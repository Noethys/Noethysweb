# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views.base import CustomView
from django.views.generic import TemplateView
import json
from reglements.forms.detail_prestations_depot import Formulaire
from core.models import Ventilation, Activite
from decimal import Decimal


class View(CustomView, TemplateView):
    menu_code = "detail_prestations_depot"
    template_name = "reglements/detail_prestations_depot.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Détail des prestations d'un dépôt"
        context['afficher_menu_brothers'] = True
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "afficher_tarif_unitaire": form.cleaned_data["afficher_tarif_unitaire"],
            "liste_lignes": json.dumps(liste_lignes),
            "titre": form.cleaned_data["depot"].nom,
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        depot = parametres["depot"]

        # Importation des noms d'activités
        dict_activites = {activite.pk: activite.nom for activite in Activite.objects.all()}

        # Importation des ventilations
        ventilations = Ventilation.objects.select_related('reglement', 'prestation').filter(reglement__depot=depot)

        total = Decimal(0)
        dict_prestations = {}
        for ventilation in ventilations:
            IDactivite = ventilation.prestation.activite_id
            label = ventilation.prestation.label
            montant = ventilation.montant

            if ventilation.prestation.categorie == "cotisation":
                IDactivite = 90001
            if ventilation.prestation.categorie == "location":
                IDactivite = 90002

            # Mémorisation par prestation
            if IDactivite not in dict_prestations:
                dict_prestations[IDactivite] = {"prestations": {}, "quantite": 0, "total": Decimal(0)}
            if label not in dict_prestations[IDactivite]["prestations"]:
                dict_prestations[IDactivite]["prestations"][label] = {"detail": {}, "quantite": 0, "total": Decimal(0)}
            if montant not in dict_prestations[IDactivite]["prestations"][label]["detail"]:
                dict_prestations[IDactivite]["prestations"][label]["detail"][montant] = {"quantite": 0, "total": Decimal(0)}
            dict_prestations[IDactivite]["prestations"][label]["detail"][montant]["quantite"] += 1
            dict_prestations[IDactivite]["prestations"][label]["detail"][montant]["total"] += montant

            # Total par activité
            dict_prestations[IDactivite]["quantite"] += 1
            dict_prestations[IDactivite]["total"] += montant

            # Total par label de prestation
            dict_prestations[IDactivite]["prestations"][label]["quantite"] += 1
            dict_prestations[IDactivite]["prestations"][label]["total"] += montant

            total += montant

        # Recherche des avoirs
        if (depot.montant or Decimal(0)) > total:
            montant_avoirs = depot.montant - total
            dict_prestations[80000] = {"prestations": {"Non ventilé": {"quantite": 1, "total": montant_avoirs, "detail": {montant_avoirs: {"quantite": 1, "total": montant_avoirs}}}},
                                       "quantite": 1, "total": montant_avoirs}

        # Remplissage
        liste_lignes = []

        # Branches Activités
        listeLabels = []
        for IDactivite, dictActivite in dict_prestations.items():
            if IDactivite in dict_activites: nomActivite = dict_activites[IDactivite]
            elif IDactivite == 90001: nomActivite = "Cotisations"
            elif IDactivite == 90002: nomActivite = "Locations"
            elif IDactivite == 80000: nomActivite = "Non ventilé"
            else: nomActivite = "Autres prestations"
            listeLabels.append((nomActivite, IDactivite, dictActivite))
        listeLabels.sort()

        quantite = 0
        total = Decimal(0)

        # Niveau activité
        for nomActivite, IDactivite, dictActivite in listeLabels:
            id_activite = "activite_%d" % (IDactivite or 0)
            liste_lignes.append({"id": id_activite, "pid": 0, "regroupement": True, "label": nomActivite, "quantite": dictActivite["quantite"], "total": float(dictActivite["total"])})

            # Mémorise total général
            quantite += dictActivite["quantite"]
            total += dictActivite["total"]

            # Niveau prestation
            liste_labels = list(dictActivite["prestations"])
            liste_labels.sort()

            for label in liste_labels:
                dict_label = dictActivite["prestations"][label]

                # Afficher le détail des montants
                if parametres["afficher_tarif_unitaire"] == True:
                    liste_montants = list(dict_label["detail"])
                    liste_montants.sort()
                    for montant in liste_montants:
                        dict_montant = dict_label["detail"][montant]
                        liste_lignes.append({"id": 1, "pid": id_activite, "regroupement": False, "label": label, "tarif_unitaire": float(montant), "quantite": float(dict_montant["quantite"]), "total": float(dict_montant["total"])})
                else:
                    liste_lignes.append({"id": 1, "pid": id_activite, "regroupement": False, "label": label, "quantite": dict_label["quantite"], "total": float(dict_label["total"])})

        return liste_lignes

