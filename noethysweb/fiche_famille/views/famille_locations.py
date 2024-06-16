# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, uuid
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Location, Vacance, Ferie, Produit, TarifProduit, Prestation
from core.utils import utils_dates
from fiche_famille.forms.famille_locations import Formulaire, FORMSET_PRESTATIONS
from fiche_famille.views.famille import Onglet


def Get_tarif_location(request):
    # Récupération des variables
    idproduit = request.POST.get("idproduit")
    if not idproduit:
        return JsonResponse({"erreur": "Vous devez sélectionner un produit"}, status=401)
    quantite = int(request.POST.get("quantite"))
    try:
        date_debut = datetime.datetime.strptime(request.POST.get("date_debut"), "%d/%m/%Y %H:%M").date()
    except:
        return JsonResponse({"erreur": "La date de début semble erronée"}, status=401)

    # Importation du produit
    produit = Produit.objects.get(pk=int(idproduit))
    tarifs_trouves = []
    tarifs_selections = []
    if produit.montant:
        # Si tarif simple
        tarifs_trouves.append({
            "date": utils_dates.ConvertDateToFR(date_debut),
            "label": produit.nom,
            "montant": produit.montant,
            "tva": 0.0,
        })
    else:
        # Si tarifs avancés
        tarifs = TarifProduit.objects.filter(produit=produit).order_by("date_debut")
        index = 0
        for tarif in tarifs:
            if tarif.date_debut <= date_debut and (not tarif.date_fin or tarif.date_fin >= date_debut):
                montant = tarif.montant if tarif.methode == "produit_montant_unique" else tarif.montant * quantite
                tarifs_trouves.append({
                    "date": utils_dates.ConvertDateToFR(date_debut),
                    "label": produit.nom,
                    "montant": montant,
                    "tva": tarif.tva or 0.0,
                })
                tarifs_selections.append({"text" : "%s : %s €" % (produit.nom, montant), "value": index})
                index += 1
    return JsonResponse({"tarifs": tarifs_trouves, "selections": tarifs_selections})


class Page(Onglet):
    model = Location
    url_liste = "famille_locations_liste"
    url_ajouter = "famille_locations_ajouter"
    url_modifier = "famille_locations_modifier"
    url_supprimer = "famille_locations_supprimer"
    url_supprimer_plusieurs = "famille_locations_supprimer_plusieurs"
    description_liste = "Saisissez ici les locations de la famille."
    description_saisie = "Saisissez toutes les informations concernant la location et cliquez sur le bouton Enregistrer."
    objet_singulier = "une location"
    objet_pluriel = "des locations"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Locations"
        context['onglet_actif'] = "locations"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
        ]
        # Ajout l'idfamille à l'URL de suppression groupée
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idfamille': self.kwargs.get('idfamille', None), "listepk": "xxx"})
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idfamille au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, crud.Liste):
    model = Location
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Location.objects.select_related("produit").filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idlocation", "date_debut", "date_fin"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nom_produit = columns.TextColumn("Nom", sources=["produit__nom"], processor='Get_nom_produit')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idlocation", "nom_produit", "date_debut", "date_fin", "actions"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y %H:%M'),
                'date_fin': helpers.format_date('%d/%m/%Y %H:%M'),
            }
            ordering = ['date_debut']

        def Get_nom_produit(self, instance, *args, **kwargs):
            return instance.produit.nom

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                self.Create_bouton_imprimer(url=reverse("famille_voir_location", kwargs={"idfamille": kwargs["idfamille"], "idlocation": instance.pk}), title="Imprimer ou envoyer par email la location"),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_locations.html"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if self.request.POST:
            context["formset_prestations"] = FORMSET_PRESTATIONS(self.request.POST, instance=self.object)
        else:
            context["formset_prestations"] = FORMSET_PRESTATIONS(instance=self.object)
        return context

    def form_valid(self, form):
        resultat = Form_valid_ajouter(form=form, request=self.request, object=self.object)
        if resultat == True:
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=resultat))


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_locations.html"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if self.request.POST:
            context["formset_prestations"] = FORMSET_PRESTATIONS(self.request.POST, instance=self.object)
        else:
            context["formset_prestations"] = FORMSET_PRESTATIONS(instance=self.object)
        return context

    def form_valid(self, form):
        resultat = Form_valid_modifier(form=form, request=self.request, object=self.object)
        if isinstance(resultat, Location):
            self.object = resultat
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=resultat))


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"

    def Check_protections(self, objet=None):
        protections = []
        if Prestation.objects.filter(location=objet, facture__isnull=False):
            protections.append("Vous ne pouvez pas supprimer cette location car au moins une prestation facturée y est associée")
        return protections


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "fiche_famille/famille_delete.html"

    def Check_protections(self, objets=[]):
        protections = []
        prestations_facturees = {}
        for prestation in Prestation.objects.filter(location__in=objets, facture__isnull=False):
            prestations_facturees[prestation.location_id] = True
        for location in objets:
            if location.pk in prestations_facturees:
                protections.append("La location ID%d est déjà facturée" % location.pk)
        return protections


def Form_valid_ajouter(form=None, request=None, object=None):
    # Vérification du formulaire
    if not form.is_valid():
        return form

    # Vérification du formset des prestations
    formset_prestations = FORMSET_PRESTATIONS(request.POST, instance=object)
    if not formset_prestations.is_valid():
        return form

    # Sauvegarde de la location
    liste_locations = []
    if form.cleaned_data["selection_periode"] == "UNIQUE":
        object = form.save()
        liste_locations.append(object)

    if form.cleaned_data["selection_periode"] == "RECURRENCE":
        occurences = Calcule_occurences(form.cleaned_data)
        serie = str(uuid.uuid4())
        for occurence in occurences:
            location = Location.objects.create(
                famille=form.cleaned_data["famille"],
                produit=form.cleaned_data["produit"],
                observations=form.cleaned_data["observations"],
                date_debut=occurence["date_debut"],
                date_fin=occurence["date_fin"],
                quantite=form.cleaned_data["quantite"],
                serie=serie,
            )
            liste_locations.append(location)

    # Sauvegarde des prestations
    if formset_prestations.is_valid():
        for formline in formset_prestations.forms:
            if formline.cleaned_data.get('DELETE') and form.instance.pk and formline.instance.pk:
                formline.instance.delete()
            if formline.cleaned_data and not formline.cleaned_data.get('DELETE'):
                for location in liste_locations:
                    prestation = formline.save(commit=False)
                    prestation.pk = None
                    prestation.location = location
                    prestation.date = location.date_debut.date()
                    prestation.famille = form.cleaned_data["famille"]
                    prestation.montant_initial = prestation.montant
                    prestation.categorie = "location"
                    prestation.save()

    return True


def Form_valid_modifier(form=None, request=None, object=None):
    # Vérification du formulaire
    if not form.is_valid():
        return form

    # Vérification du formset des prestations
    formset_prestations = FORMSET_PRESTATIONS(request.POST, instance=object)
    if not formset_prestations.is_valid():
        return form

    # Sauvegarde de la location
    object = form.save()

    # Sauvegarde des prestations
    if formset_prestations.is_valid():
        for formline in formset_prestations.forms:
            if formline.cleaned_data.get('DELETE') and form.instance.pk and formline.instance.pk:
                formline.instance.delete()
            if formline.cleaned_data and not formline.cleaned_data.get('DELETE'):
                prestation = formline.save(commit=False)
                prestation.location = object
                prestation.date = object.date_debut.date()
                prestation.famille = form.cleaned_data["famille"]
                prestation.montant_initial = prestation.montant
                prestation.categorie = "location"
                prestation.save()

    return object


def Calcule_occurences(cleaned_data={}):
    """ Calcule les occurences """
    liste_resultats = []

    liste_vacances = Vacance.objects.all()
    liste_feries = Ferie.objects.all()

    cleaned_data["recurrence_jours_vacances"] = [int(x) for x in cleaned_data["recurrence_jours_vacances"]]
    cleaned_data["recurrence_jours_scolaires"] = [int(x) for x in cleaned_data["recurrence_jours_scolaires"]]

    # Liste dates
    listeDates = [cleaned_data["recurrence_date_debut"],]
    tmp = cleaned_data["recurrence_date_debut"]
    while tmp < cleaned_data["recurrence_date_fin"]:
        tmp += datetime.timedelta(days=1)
        listeDates.append(tmp)

    date = cleaned_data["recurrence_date_debut"]
    numSemaine = int(cleaned_data["recurrence_frequence_type"])
    dateTemp = date
    for date in listeDates:

        # Vérifie période et jour
        valide = False
        if utils_dates.EstEnVacances(date=date, liste_vacances=liste_vacances):
            if date.weekday() in cleaned_data["recurrence_jours_vacances"]:
                valide = True
        else:
            if date.weekday() in cleaned_data["recurrence_jours_scolaires"]:
                valide = True

        # Calcul le numéro de semaine
        if len(listeDates) > 0:
            if date.weekday() < dateTemp.weekday():
                numSemaine += 1

        # Fréquence semaines
        if cleaned_data["recurrence_frequence_type"] in (2, 3, 4):
            if numSemaine % cleaned_data["recurrence_frequence_type"] != 0:
                valide = False

        # Semaines paires et impaires
        if valide == True and cleaned_data["recurrence_frequence_type"] in (5, 6):
            numSemaineAnnee = date.isocalendar()[1]
            if numSemaineAnnee % 2 == 0 and cleaned_data["recurrence_frequence_type"] == 6:
                valide = False
            if numSemaineAnnee % 2 != 0 and cleaned_data["recurrence_frequence_type"] == 5:
                valide = False

        # Vérifie si férié
        if cleaned_data["recurrence_feries"] and utils_dates.EstFerie(date, liste_feries):
            valide = False

        # Application
        if valide:
            date_debut_final = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=cleaned_data["recurrence_heure_debut"].hour, minute=cleaned_data["recurrence_heure_debut"].minute)
            date_fin_final = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=cleaned_data["recurrence_heure_fin"].hour, minute=cleaned_data["recurrence_heure_fin"].minute)
            liste_resultats.append({"date_debut": date_debut_final, "date_fin": date_fin_final})

        dateTemp = date
    return liste_resultats
