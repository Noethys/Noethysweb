# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging, time
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_dates
from core.models import Rattachement, Unite
from consommations.forms.consommations_traitement_lot import Formulaire_activite
from consommations.forms.grille_traitement_lot import Formulaire as Formulaire_options


def Appliquer(request):
    logger.debug("Appliquer le traitement par lot...")
    time.sleep(1)

    # Récupération des paramètres
    form = Formulaire_options(request.POST)
    if not form.is_valid():
        messages_erreurs = [erreur[0].message for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ". ".join(messages_erreurs)}, status=401)

    # Récupération des rattachements cochés
    rattachements_coches = Rattachement.objects.filter(pk__in=json.loads(form.cleaned_data["individus_coches"]))
    if not rattachements_coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins un individu dans la liste"}, status=401)

    # Calcul des dates à impacter
    from consommations.utils import utils_traitement_lot
    resultat = utils_traitement_lot.Calculer(request=request, parametres=form.cleaned_data)
    if "erreur" in resultat:
        return JsonResponse(resultat, status=401)

    # Application dans la grille virtuelle
    from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
    for rattachement in rattachements_coches:
        grille = Grille_virtuelle(request=request, idfamille=rattachement.famille_id, idindividu=rattachement.individu_id, idactivite=int(form.cleaned_data["idactivite"]), date_min=min(resultat["dates"]), date_max=max(resultat["dates"]))
        for date in resultat["dates"]:
            for idunite, parametres_unite in resultat["unites"].items():
                if resultat["action"] == "SAISIE":
                    grille.Ajouter(criteres={"date": date, "unite": idunite}, parametres=parametres_unite)
                if resultat["action"] == "EFFACER":
                    grille.Supprimer(criteres={"date": date, "unite": idunite})
        grille.Enregistrer()

    logger.debug("Application du traitement par lot terminé.")
    return JsonResponse({"success": True})


class Page(crud.Page):
    model = Rattachement
    url_liste = "consommations_traitement_lot"
    menu_code = "consommations_traitement_lot"


class Liste(Page, crud.Liste):
    template_name = "consommations/consommations_traitement_lot.html"
    model = Rattachement

    def get_queryset(self):
        return Rattachement.objects.select_related("individu", "famille").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Traitement par lot"
        context["box_titre"] = "Sélection des paramètres"
        context["box_introduction"] = "Cette fonctionnalité permet d'ajouter ou de supprimer des consommations par lot. Renseignez les paramètres de l'action à réaliser et cochez les individus concernés."
        context["onglet_actif"] = "consommations_traitement_lot"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["active_checkbox"] = True
        context["bouton_supprimer"] = False
        context["hauteur_table"] = "400px"
        context["form_options"] = Formulaire_options(mode="consommations_traitement_lot")
        context["data"] = {"liste_unites": Unite.objects.filter(activite=self.kwargs.get("idactivite", None)).distinct().order_by("ordre")}
        context["idactivite"] = self.kwargs.get("idactivite", None)
        context["afficher_menu_brothers"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille"]
        check = columns.CheckBoxSelectColumn(label="")
        nom = columns.TextColumn("Nom", sources=['individu__nom'])
        prenom = columns.TextColumn("Prénom", sources=['individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        date_naiss = columns.TextColumn("Date naiss.", processor="Get_date_naiss")
        age = columns.TextColumn("Age", sources=['Get_age'], processor="Get_age")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idrattachement", "nom", "prenom", "age", "date_naiss", "famille"]
            ordering = ["nom", "prenom"]

        def Get_age(self, instance, *args, **kwargs):
            return instance.individu.Get_age()

        def Get_date_naiss(self, instance, *args, **kwargs):
            return utils_dates.ConvertDateToFR(instance.individu.date_naiss)


class Selection_activite(Page, crud.Ajouter):
    form_class = Formulaire_activite
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_activite, self).get_context_data(**kwargs)
        context["box_introduction"] = "Vous devez sélectionner une activité."
        context["page_titre"] = "Traitement par lot"
        context["box_titre"] = "Sélection de l'activité"
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("consommations_traitement_lot_liste", kwargs={"idactivite": request.POST.get("activite")}))
