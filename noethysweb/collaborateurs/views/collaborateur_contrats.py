# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ContratCollaborateur
from collaborateurs.forms.collaborateur_contrats import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Page(Onglet):
    model = ContratCollaborateur
    url_liste = "collaborateur_contrats_liste"
    url_ajouter = "collaborateur_contrats_ajouter"
    url_modifier = "collaborateur_contrats_modifier"
    url_supprimer = "collaborateur_contrats_supprimer"
    url_supprimer_plusieurs = "collaborateur_contrats_supprimer_plusieurs"
    description_liste = "Retrouvez ici les contrats successifs du collaborateur. Le contrat en cours détermine le poste du collaborateur et l'objectif de temps de travail suivi dans le planning individuel."
    description_saisie = "Renseignez le type de contrat, le poste, la période et le temps de travail, puis cliquez sur le bouton Enregistrer. La rubrique Objectif de temps de travail définit le calcul du solde d'heures."
    objet_singulier = "un contrat"
    objet_pluriel = "des contrats"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Contrats"
        context['onglet_actif'] = "contrats"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)}), "icone": "fa fa-plus"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idcollaborateur"] = self.Get_idcollaborateur()
        return form_kwargs

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)})


MAX_JOURS_APPLICATION = 731      # Période maximale d'application d'un modèle depuis un contrat (2 ans)


def Peut_appliquer_modele(user=None, idcollaborateur=None):
    """ L'utilisateur peut modifier le planning de ce collaborateur """
    from collaborateurs.views import planning_individuel
    from collaborateurs.utils import utils_planning
    return planning_individuel.Peut_acceder(user) and planning_individuel.Collaborateurs_accessibles(user).filter(pk=idcollaborateur).exists() \
           and idcollaborateur in utils_planning.Get_ids_modifiables(user)


def Fins_proposees(date_debut=None):
    """ Raccourcis de date de fin d'application : fin de l'année civile et fin de l'année scolaire qui suivent le début du contrat """
    from collaborateurs.utils import utils_objectif
    mois = int(utils_objectif.Get_parametres()["mois_debut_scolaire"])
    fin_annee = datetime.date(date_debut.year, 12, 31)
    debut_annee_scolaire_suivante = datetime.date(date_debut.year + (1 if date_debut.month >= mois else 0), mois, 1)
    return {"annee": fin_annee, "scolaire": debut_annee_scolaire_suivante - datetime.timedelta(days=1)}


def Appliquer_modele_contrat(request):
    """ Applique le modèle de planning par défaut d'un contrat sur sa période (ou jusqu'à la date de fin indiquée si le contrat n'en a pas).
        Avec apercu=true, renvoie seulement le nombre d'évènements qui seraient créés. """
    from collaborateurs.utils import utils_planning
    from collaborateurs.utils.utils_modeles_planning import Generateur, Repartir, Memoriser_recents
    from collaborateurs.utils.utils_planning import Parse_date
    contrat = ContratCollaborateur.objects.select_related("modele_planning", "collaborateur").filter(pk=int(request.POST.get("idcontrat") or 0)).first()
    if not contrat or not contrat.modele_planning or not Peut_appliquer_modele(request.user, contrat.collaborateur_id):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier le planning de ce collaborateur"}, status=403)
    try:
        date_fin = contrat.date_fin or Parse_date(request.POST.get("date_fin"))
    except ValueError:
        date_fin = None
    if not date_fin:
        return JsonResponse({"erreur": "Saisissez la date de fin d'application"}, status=400)
    if date_fin < contrat.date_debut:
        return JsonResponse({"erreur": "La date de fin doit être postérieure au début du contrat (%s)" % contrat.date_debut.strftime("%d/%m/%Y")}, status=400)
    if (date_fin - contrat.date_debut).days >= MAX_JOURS_APPLICATION:
        return JsonResponse({"erreur": "La période d'application ne peut pas dépasser 2 ans. Choisissez une date de fin plus proche, vous pourrez prolonger le planning plus tard."}, status=400)
    dates = [contrat.date_debut + datetime.timedelta(days=n) for n in range((date_fin - contrat.date_debut).days + 1)]
    apercu = request.POST.get("apercu") == "true"
    conflit = request.POST.get("conflit") if request.POST.get("conflit") in ("ignorer", "remplacer") else "ignorer"
    modeles = [contrat.modele_planning_id]
    generateur = Generateur(modeles=modeles, dates=dates, departs={})
    # Le modèle a été choisi explicitement pour ce contrat : ses éventuelles restrictions (groupes, postes) ne s'appliquent pas
    repartition, _ = Repartir(modeles=modeles, collaborateurs=[contrat.collaborateur_id], date=dates[0], forcer=True)
    nouveaux, hors_contrat = utils_planning.Generer_depuis_modeles(generateur=generateur, repartition=repartition, modeles=modeles, collaborateurs=[contrat.collaborateur_id], dates=dates)
    with transaction.atomic():
        resultat = utils_planning.Creer_par_lot(nouveaux=nouveaux, collaborateurs=[contrat.collaborateur_id], dates=dates, conflit=conflit, apercu=apercu,
                                                user=request.user, libelle="modèle de planning")
        if not apercu:
            generateur.Memoriser_ancrages()
            Memoriser_recents(request.user, modeles)
    resultat["nbre_hors_contrat"] = hors_contrat
    resultat["periode"] = "du %s au %s" % (contrat.date_debut.strftime("%d/%m/%Y"), date_fin.strftime("%d/%m/%Y"))
    return JsonResponse(resultat)


class Liste(Page, crud.Liste):
    model = ContratCollaborateur
    template_name = "collaborateurs/contrats_liste.html"

    def get_queryset(self):
        return ContratCollaborateur.objects.select_related("type_contrat", "type_poste").filter(Q(collaborateur_id=self.Get_idcollaborateur()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""

        # Contrat qui vient d'être créé avec un modèle de planning : proposition d'appliquer le modèle
        try:
            idcontrat = int(self.request.GET.get("appliquer_modele") or 0)
        except ValueError:
            idcontrat = 0
        contrat = ContratCollaborateur.objects.select_related("modele_planning", "collaborateur").filter(pk=idcontrat, collaborateur_id=self.Get_idcollaborateur()).first() if idcontrat else None
        if contrat and contrat.modele_planning and Peut_appliquer_modele(self.request.user, contrat.collaborateur_id):
            from collaborateurs.utils import utils_modeles_planning, utils_objectif
            info = {modele["id"]: modele for modele in utils_modeles_planning.Get_liste_modeles()["modeles"]}.get(contrat.modele_planning_id, {})
            fins = Fins_proposees(contrat.date_debut)
            context['contrat_modele'] = {
                "contrat": contrat, "heures": utils_objectif.Format_heures(info.get("heures", 0)), "cycle": info.get("cycle", ""),
                "fin_annee": fins["annee"], "fin_scolaire": fins["scolaire"],
            }
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcontrat", "date_debut", "date_fin"]
        nom_type_contrat = columns.TextColumn("Type de contrat", sources=["type_contrat__nom"], processor='Get_nom_type_contrat')
        nom_type_poste = columns.TextColumn("Poste", sources=["type_poste__nom"], processor='Get_nom_type_poste')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcontrat", "date_debut", "date_fin", "nom_type_contrat", "nom_type_poste", "actions"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_nom_type_contrat(self, instance, *args, **kwargs):
            return instance.type_contrat.nom if instance.type_contrat else ""

        def Get_nom_type_poste(self, instance, *args, **kwargs):
            return instance.type_poste.nom

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                self.Create_bouton_word(url=reverse("collaborateur_voir_contrat", kwargs={"idcollaborateur": kwargs["idcollaborateur"], "idcontrat": instance.pk})), ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"

    def get_success_url(self):
        """ Après la création d'un contrat avec un modèle de planning, la liste propose d'appliquer le modèle """
        url = super(Ajouter, self).get_success_url()
        if "SaveAndNew" not in self.request.POST and self.object and self.object.modele_planning_id and Peut_appliquer_modele(self.request.user, self.object.collaborateur_id):
            url = "%s?appliquer_modele=%d" % (url, self.object.pk)
        return url


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "collaborateurs/collaborateur_delete.html"
