# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime, logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Inscription, Consommation, Ouverture
from core.utils import utils_dates
from individus.forms.inscriptions_changer_groupe import Formulaire_activite, Formulaire_options


def Appliquer(request):
    logger.debug("Changer le groupe par lot...")

    # Récupération des inscriptions cochées
    inscriptions_cochees = json.loads(request.POST.get("inscriptions_cochees"))
    if not inscriptions_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une inscription à modifier dans la liste"}, status=401)
    inscriptions = Inscription.objects.select_related("individu").filter(pk__in=inscriptions_cochees)

    # Récupération des options
    valeurs_form_options = json.loads(request.POST.get("form_options"))
    form = Formulaire_options(valeurs_form_options, idactivite=request.POST.get("idactivite"))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez renseigner correctement les paramètres"}, status=401)

    # On vérifie que les dates de début des inscriptions sont supérieures à la date d'application
    for inscription in inscriptions:
        if inscription.date_debut > form.cleaned_data["date_application"]:
            return JsonResponse({"erreur": "Modification impossible : La date de début de l'inscription de %s est supérieure à la date d'application souhaitée." % inscription.individu.Get_nom()}, status=401)

    # Importation des consommations
    consommations = Consommation.objects.filter(inscription__in=inscriptions, date__gte=form.cleaned_data["date_application"])

    # Vérifie que les unités et dates souhaitées sont ouvertes sur le nouveau groupe
    if consommations:
        ouvertures = [(ouverture.date, ouverture.unite_id) for ouverture in Ouverture.objects.filter(groupe=form.cleaned_data["groupe"])]
        anomalies = [utils_dates.ConvertDateToFR(conso.date) for conso in consommations if (conso.date, conso.unite_id) not in ouvertures]
        if anomalies:
            return JsonResponse({"erreur": "Modification impossible des consommations ! Les consommations ne peuvent pas être transférées sur les dates suivantes car les unités sont fermées : %s." % ", ".join(anomalies)}, status=401)

    # Modification de la date de fin des inscriptions sélectionnées
    for inscription in inscriptions:
        inscription.date_fin = form.cleaned_data["date_application"] - datetime.timedelta(days=1)
    Inscription.objects.bulk_update(inscriptions, ["date_fin"], batch_size=50)

    # Création des nouvelles inscriptions
    dict_nouvelles_inscriptions = {}
    for inscription in list(inscriptions):
        ancien_id = int(inscription.pk)
        inscription.pk = None
        inscription.groupe = form.cleaned_data["groupe"]
        inscription.date_debut = form.cleaned_data["date_application"]
        inscription.date_fin = None
        inscription.save()
        dict_nouvelles_inscriptions[ancien_id] = inscription

    # Changement du groupe sur les consommations
    if consommations:
        logger.debug("Changement de groupe pour %d consommations..." % len(consommations))
        nouvelles_conso = []
        for conso in consommations:
            conso.groupe = form.cleaned_data["groupe"]
            conso.inscription = dict_nouvelles_inscriptions[conso.inscription_id]
            nouvelles_conso.append(conso)
        Consommation.objects.bulk_update(nouvelles_conso, ["groupe", "inscription"], batch_size=50)

    logger.debug("Application des modifications terminée.")
    return JsonResponse({"success": True})


class Page(crud.Page):
    model = Inscription
    url_liste = "inscriptions_changer_groupe"
    menu_code = "inscriptions_changer_groupe"


class Liste(Page, crud.Liste):
    template_name = "individus/inscriptions_changer_groupe.html"
    model = Inscription

    def get_queryset(self):
        return Inscription.objects.select_related("famille", "individu", "groupe").filter(self.Get_filtres("Q"), activite_id=self.kwargs.get("idactivite", None))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Changer de groupe par lot"
        context["box_titre"] = "Sélection des paramètres"
        context["box_introduction"] = "Cette fonctionnalité permet de changer de groupe à des individus par lot. L'inscription sélectionnée sera clôturée puis une nouvelle inscription sera créée. Les éventuelles consommations seront modifiées en conséquence. Attention, à utiliser avec précaution ! Cette fonctionnalité ne vérifie pas s'il reste de la place et ne recalcule pas les prestations associées, elle ne fait que créer de nouvelles inscriptions et modifier le groupe des consommations."
        context["onglet_actif"] = "inscriptions_changer_groupe"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["active_checkbox"] = True
        context["bouton_supprimer"] = False
        context["hauteur_table"] = "400px"
        context["form_options"] = Formulaire_options(idactivite=self.kwargs.get("idactivite", None))
        context["idactivite"] = self.kwargs.get("idactivite", None)
        context["afficher_menu_brothers"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "igenerique:individu", "idinscription", "date_debut", "date_fin", "groupe__nom", "statut"]
        check = columns.CheckBoxSelectColumn(label="")
        groupe = columns.TextColumn("Groupe", sources=["groupe__nom"])
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        date_naiss = columns.TextColumn("Date naiss.", sources=["individu__date_naiss"], processor=helpers.format_date('%d/%m/%Y'))
        age = columns.TextColumn("Age", sources=['Get_age'], processor="Get_age")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", "individu", "date_naiss", "age", "date_debut", "date_fin", "groupe", "famille"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["individu__nom", "individu__prenom"]

        def Get_age(self, instance, *args, **kwargs):
            return instance.individu.Get_age()


class Selection_activite(Page, crud.Ajouter):
    form_class = Formulaire_activite
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_activite, self).get_context_data(**kwargs)
        context["box_introduction"] = "Vous devez sélectionner une activité."
        context["page_titre"] = "Changer de groupe par lot"
        context["box_titre"] = "Sélection de l'activité"
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("inscriptions_changer_groupe_liste", kwargs={"idactivite": request.POST.get("activite")}))
