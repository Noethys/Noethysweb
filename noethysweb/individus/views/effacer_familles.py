# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime, time
logger = logging.getLogger(__name__)
from decimal import Decimal
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Max, Sum
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Prestation, Reglement, Rattachement
from core.utils import utils_texte
from individus.utils import utils_anonymisation


def Effacer(request):
    time.sleep(1)

    # Récupération des comptes cochés
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins une famille dans la liste"}, status=401)

    # Vérifications
    liste_anomalies = []
    for famille in Famille.objects.filter(pk__in=coches).annotate(derniere_prestation=Max("prestation__date"), derniere_facture=Max("facture__date_edition")):
        if famille not in liste_anomalies and famille.derniere_prestation and (datetime.date.today() - famille.derniere_prestation).days < 60:
            liste_anomalies.append(famille)
        if famille not in liste_anomalies and famille.derniere_facture and (datetime.date.today() - famille.derniere_facture).days < 60:
            liste_anomalies.append(famille)
    if liste_anomalies:
        return JsonResponse({"erreur": "Procédure annulée : Les familles suivantes ont une activité trop récente : %s." % ", ".join([famille.nom for famille in liste_anomalies])}, status=401)

    # Effacer les fiches familles
    for famille in Famille.objects.filter(pk__in=coches):
        utils_anonymisation.Anonymiser_famille(famille=famille)

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "%d fiches familles ont été effacées avec succès" % len(coches))
    return JsonResponse({"url": reverse_lazy("effacer_familles")})


class Page(crud.Page):
    model = Famille
    url_liste = "effacer_familles"
    menu_code = "effacer_familles"


class Liste(Page, crud.Liste):
    template_name = "individus/effacer_familles.html"
    model = Famille

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q")).annotate(derniere_action=Max("historique__horodatage"), derniere_prestation=Max("prestation__date"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Effacer des familles"
        context['box_titre'] = "Liste des familles"
        context['box_introduction'] = "Conformément au RGPD, effacez ici les données personnelles des familles qui ne fréquentent plus la structure. Les fiches ne sont pas supprimées mais anonymisées : les consommations, prestations et règlements sont conservés pour ne pas fausser les statistiques et la comptabilité. <b>Attention, cette opération est irréversible.</b>"
        context['onglet_actif'] = "effacer_familles"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context["hauteur_table"] = "400px"
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille", "derniere_action"]
        check = columns.CheckBoxSelectColumn(label="")
        solde = columns.TextColumn("Solde", sources=None, processor="Get_solde")
        rattachements = columns.TextColumn("Individus rattachés", sources=None, processor="Get_rattachements")
        derniere_prestation = columns.TextColumn("Dernière prestation", sources=None, processor=helpers.format_date('%d/%m/%Y'))
        derniere_action = columns.TextColumn("Dernière action", sources=None, processor=helpers.format_date('%d/%m/%Y'))
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idfamille", "nom", "rattachements", "solde", "derniere_action", "derniere_prestation", "actions"]
            ordering = ["nom"]

        def Get_rattachements(self, instance, *args, **kwargs):
            if not hasattr(self, "dict_rattachements"):
                self.dict_rattachements = {}
                for rattachement in Rattachement.objects.select_related("individu").all().order_by("categorie"):
                    self.dict_rattachements.setdefault(rattachement.famille_id, [])
                    self.dict_rattachements[rattachement.famille_id].append(rattachement.individu)
            return ", ".join([individu.Get_nom() for individu in self.dict_rattachements.get(instance.pk, [])])

        def Get_solde(self, instance, *args, **kwargs):
            if not hasattr(self, "dict_prestations"):
                self.dict_prestations = {temp["famille_id"]: temp["total"] for temp in Prestation.objects.values("famille_id").annotate(total=Sum("montant"))}
                self.dict_reglements = {temp["famille_id"]: temp["total"] for temp in Reglement.objects.values("famille_id").annotate(total=Sum("montant"))}
            solde = self.dict_reglements.get(instance.pk, Decimal(0)) - self.dict_prestations.get(instance.pk, Decimal(0))
            if solde == Decimal(0):
                couleur = "success"
            elif solde > Decimal(0):
                couleur = "info"
            else:
                couleur = "danger"
            return """<span class='badge badge-%s'>%s</span>""" % (couleur, utils_texte.Formate_montant(solde))

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("famille_resume", args=[instance.pk]), title="Ouvrir la fiche famille", icone="fa-users", args="target='_blank'"),
            ]
            return self.Create_boutons_actions(html)
