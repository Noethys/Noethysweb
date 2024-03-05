# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging
logger = logging.getLogger(__name__)
from django.urls import reverse
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Facture
from core.utils import utils_preferences
from facturation.forms.factures_modifier import Formulaire


def Appliquer(request):
    logger.debug("Modifier les factures par lot...")

    # Récupération des factures cochées
    factures_cochees = json.loads(request.POST.get("factures_cochees"))
    if not factures_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une facture à modifier dans la liste"}, status=401)
    factures = Facture.objects.filter(pk__in=factures_cochees)

    # Récupération des options
    form = Formulaire(json.loads(request.POST.get("form_options")))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez renseigner correctement les paramètres"}, status=401)

    # Application des modifications
    liste_champs_modifier = []
    for champ in ("date_edition", "date_echeance", "prefixe", "lot", "regie", "date_limite_paiement"):
        if form.cleaned_data["modifier_%s" % champ]:
            liste_champs_modifier.append(champ)
            logger.debug("Changement de %s pour %d factures..." % (champ, len(factures)))
            for facture in factures:
                setattr(facture, champ, form.cleaned_data[champ])

    if not liste_champs_modifier:
        return JsonResponse({"erreur": "Vous n'avez sélectionné aucun paramètre à modifier"}, status=401)

    # Enregistrement des modifications
    Facture.objects.bulk_update(factures, liste_champs_modifier, batch_size=50)

    logger.debug("Application des modifications des factures terminée.")
    return JsonResponse({"success": True})


class Page(crud.Page):
    model = Facture
    url_liste = "factures_modifier"
    menu_code = "factures_modifier"


class Liste(Page, crud.Liste):
    template_name = "facturation/factures_modifier.html"
    model = Facture

    def get_queryset(self):
        return Facture.objects.select_related('famille', 'lot', 'prefixe', 'regie').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Modifier des factures par lot"
        context["box_titre"] = "Sélection des paramètres"
        context["box_introduction"] = "Renseignez les nouveaux paramètres des factures puis cochez les factures à modifier."
        context["onglet_actif"] = "factures_modifier"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["active_checkbox"] = True
        context["bouton_supprimer"] = False
        context["hauteur_table"] = "400px"
        context["form_options"] = Formulaire()
        context["afficher_menu_brothers"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", 'idfacture', 'date_edition', 'prefixe', 'numero', 'date_debut', 'date_fin', 'total', 'solde', 'solde_actuel', 'lot__nom', "regie__nom", "date_limite_paiement"]
        check = columns.CheckBoxSelectColumn(label="")
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        solde_actuel = columns.TextColumn("Solde actuel", sources=['solde_actuel'], processor='Get_solde_actuel')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])
        numero = columns.CompoundColumn("Numéro", sources=['prefixe__prefixe', 'numero'])
        regie = columns.TextColumn("Régie", sources=['regie__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idfacture', 'date_edition', 'numero', 'date_debut', 'date_fin', 'famille', 'total', 'solde', 'solde_actuel', 'lot', 'regie', 'date_limite_paiement']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'date_echeance': helpers.format_date('%d/%m/%Y'),
                'date_limite_paiement': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]
            hidden_columns = ["date_limite_paiement"]

        def Get_solde_actuel(self, instance, **kwargs):
            if instance.etat == "annulation":
                return "<span class='text-red'><i class='fa fa-trash'></i> Annulée</span>"
            icone = "fa-check text-green" if instance.solde_actuel == 0 else "fa-close text-red"
            return "<i class='fa %s margin-r-5'></i>  %0.2f %s" % (icone, instance.solde_actuel, utils_preferences.Get_symbole_monnaie())

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_factures_modifier", kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
                self.Create_bouton_imprimer(url=reverse("famille_voir_facture", kwargs={"idfamille": instance.famille_id, "idfacture": instance.pk}), title="Imprimer ou envoyer par email la facture"),
            ]
            return self.Create_boutons_actions(html)
