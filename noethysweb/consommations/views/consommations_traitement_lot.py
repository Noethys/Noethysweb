# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging, time
logger = logging.getLogger(__name__)
from django.db.models import Q
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_dates
from core.models import Inscription, Unite, Activite, JOURS_COMPLETS_SEMAINE
from consommations.forms.consommations_traitement_lot import Formulaire_activite
from consommations.forms.grille_traitement_lot import Formulaire as Formulaire_options


def Appliquer(request):
    logger.debug("Appliquer le traitement par lot...")
    time.sleep(1)

    # Récupération des paramètres
    form = Formulaire_options(request.POST, mode="consommations_traitement_lot")
    if not form.is_valid():
        messages_erreurs = [str(erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ". ".join(messages_erreurs)}, status=401)

    # Récupération des inscriptions cochées (limitées à l'activité et aux structures de l'utilisateur)
    try:
        liste_idinscription = [int(idinscription) for idinscription in json.loads(form.cleaned_data["inscriptions_cochees"] or "[]")]
        idactivite = int(form.cleaned_data["idactivite"])
    except (ValueError, TypeError):
        return JsonResponse({"erreur": "La sélection des individus n'est pas valide. Veuillez recharger la page."}, status=401)
    inscriptions_cochees = Inscription.objects.filter(pk__in=liste_idinscription, activite_id=idactivite, activite__structure__in=request.user.structures.all())
    if not inscriptions_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins un individu dans la liste"}, status=401)

    # Calcul des dates à impacter
    from consommations.utils import utils_traitement_lot
    resultat = utils_traitement_lot.Calculer(request=request, parametres=form.cleaned_data)
    if "erreur" in resultat:
        return JsonResponse(resultat, status=401)
    if not resultat["dates"]:
        return JsonResponse({"erreur": "Aucune date de la période ne correspond aux jours sélectionnés."}, status=401)

    # Regroupement des inscriptions par individu (une grille virtuelle par famille et individu)
    dict_inscriptions = {}
    for inscription in inscriptions_cochees:
        dict_inscriptions.setdefault((inscription.famille_id, inscription.individu_id), []).append(inscription.pk)

    # Application dans la grille virtuelle (uniquement sur les inscriptions cochées)
    from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
    nbre_ajoutees, nbre_supprimees, nbre_conservees = 0, 0, 0
    for (idfamille, idindividu), liste_inscriptions in dict_inscriptions.items():
        grille = Grille_virtuelle(request=request, idfamille=idfamille, idindividu=idindividu, idactivite=idactivite, date_min=min(resultat["dates"]), date_max=max(resultat["dates"]))
        for idinscription in liste_inscriptions:
            for date in resultat["dates"]:
                for idunite, parametres_unite in resultat["unites"].items():
                    criteres = {"date": date, "unite": idunite, "inscription": idinscription}
                    if resultat["action"] == "SAISIE":
                        nbre_ajoutees += grille.Ajouter(criteres=criteres, parametres=parametres_unite)
                    if resultat["action"] == "EFFACER":
                        supprimees, conservees = grille.Supprimer(criteres=criteres)
                        nbre_supprimees += supprimees
                        nbre_conservees += conservees
        grille.Enregistrer()

    logger.debug("Application du traitement par lot terminé.")
    return JsonResponse({"success": True, "action": resultat["action"], "nbre_individus": len(dict_inscriptions),
                         "nbre_ajoutees": nbre_ajoutees, "nbre_supprimees": nbre_supprimees, "nbre_conservees": nbre_conservees})


class Page(crud.Page):
    model = Inscription
    url_liste = "consommations_traitement_lot"
    menu_code = "consommations_traitement_lot"


class Liste(Page, crud.Liste):
    template_name = "consommations/consommations_traitement_lot.html"
    model = Inscription

    def get_queryset(self):
        condition = Q(activite_id=self.kwargs.get("idactivite", None), activite__structure__in=self.request.user.structures.all())
        return Inscription.objects.select_related("individu", "famille", "groupe", "categorie_tarif").filter(self.Get_filtres("Q"), condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        idactivite = self.kwargs.get("idactivite", None)
        activite = Activite.objects.filter(pk=idactivite, structure__in=self.request.user.structures.all()).first()
        context["page_titre"] = "Traitement par lot"
        context["box_titre"] = "Sélection des individus"
        context["box_introduction"] = "Cochez les individus inscrits à l'activité%s pour lesquels le traitement doit être appliqué. Utilisez le bouton Filtrer pour cibler un groupe, une catégorie de tarif ou une période d'inscription." % (" <b>%s</b>" % activite.nom if activite else "")
        context["onglet_actif"] = "consommations_traitement_lot"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["active_checkbox"] = True
        context["bouton_supprimer"] = False
        context["form_options"] = Formulaire_options(mode="consommations_traitement_lot")
        context["jours_complets_semaine"] = JOURS_COMPLETS_SEMAINE
        context["data"] = {"liste_unites": Unite.objects.filter(activite=idactivite).distinct().order_by("ordre")}
        context["idactivite"] = idactivite
        context["afficher_menu_brothers"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idinscription", "date_debut", "date_fin", "groupe__nom", "categorie_tarif__nom", "statut"]
        check = columns.CheckBoxSelectColumn(label="")
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        groupe = columns.TextColumn("Groupe", sources=["groupe__nom"])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=["categorie_tarif__nom"])
        age = columns.TextColumn("Âge", sources=None, processor="Get_age")
        date_naiss = columns.TextColumn("Date naiss.", sources=None, processor="Get_date_naiss")
        individu_ville = columns.TextColumn("Ville de l'individu", processor="Get_ville_individu")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", "individu", "famille", "groupe", "categorie_tarif", "date_debut", "date_fin", "statut", "age", "date_naiss", "individu_ville"]
            hidden_columns = ["date_naiss", "individu_ville"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
                "statut": "Formate_statut",
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["individu"]

        def Get_age(self, instance, *args, **kwargs):
            age = instance.individu.Get_age()
            return "%d ans" % age if age is not None else ""

        def Get_date_naiss(self, instance, *args, **kwargs):
            return utils_dates.ConvertDateToFR(instance.individu.date_naiss)

        def Get_ville_individu(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Formate_statut(self, instance, *args, **kwargs):
            if instance.statut == "attente":
                return "<i class='fa fa-hourglass-2 text-yellow'></i> Attente"
            elif instance.statut == "refus":
                return "<i class='fa fa-times-circle text-red'></i> Refus"
            else:
                return "<i class='fa fa-check-circle-o text-green'></i> Valide"


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
