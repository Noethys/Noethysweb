# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, uuid
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, ProtectedError
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Location, Vacance, Ferie, Produit, TarifProduit, Prestation
from core.utils import utils_dates
from locations.utils import utils_locations
from locations.forms.supprimer_occurences import Formulaire as Formulaire_supprimer_occurences
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
    description_liste = "Consultez et saisissez ici les locations de la famille."
    description_saisie = "Saisissez toutes les informations concernant la location et cliquez sur le bouton Enregistrer."
    objet_singulier = "une location"
    objet_pluriel = "des locations"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Locations"
        context['onglet_actif'] = "locations"
        if self.request.user.has_perm("core.famille_locations_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
            ]
        context['bouton_supprimer'] = self.request.user.has_perm("core.famille_locations_modifier")
        # Ajout l'idfamille à l'URL de suppression groupée
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idfamille': self.kwargs.get('idfamille', None), "listepk": "xxx"})
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.famille_locations_modifier"):
            return False
        return True

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
            if not view.request.user.has_perm("core.famille_locations_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            url_supprimer = view.url_supprimer if not instance.serie else "famille_locations_supprimer_occurence"
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(url_supprimer, kwargs=kwargs)),
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


class Supprimer_occurence(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_locations_delete.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context["nbre_occurences"] = Location.objects.filter(serie=self.object.serie).count()
        context["form_supprimer"] = Formulaire_supprimer_occurences()
        return context

    def post(self, request, **kwargs):
        form = Formulaire_supprimer_occurences(request.POST)
        form.is_valid()
        
        # Suppression des occurences
        resultat = Supprime_occurences(idlocation=kwargs["pk"], donnees=form.cleaned_data["donnees"], periode=form.cleaned_data["periode"], self=self)
        if resultat != True:
            messages.add_message(request, messages.ERROR, resultat)
            return HttpResponseRedirect(self.get_success_url(), status=303)

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppressions effectuées avec succès')

        return HttpResponseRedirect(self.get_success_url())


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
        anomalies = utils_locations.Verifie_dispo_produit(produit=form.cleaned_data["produit"], date_debut=form.cleaned_data["date_debut"], date_fin=form.cleaned_data["date_fin"])
        if anomalies:
            for anomalie in anomalies:
                form.add_error("date_debut", anomalie)
            return form
        object = form.save()
        liste_locations.append(object)

    if form.cleaned_data["selection_periode"] == "RECURRENCE":
        occurences = Calcule_occurences(form.cleaned_data)
        liste_anomalies = []
        for occurence in occurences:
            anomalies = utils_locations.Verifie_dispo_produit(produit=form.cleaned_data["produit"], date_debut=occurence["date_debut"], date_fin=occurence["date_fin"])
            if anomalies:
                for anomalie in anomalies:
                    liste_anomalies.append(anomalie)
                    form.add_error("date_debut", anomalie)
        if liste_anomalies:
            return form

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

    # Recherche dispo produit
    anomalies = utils_locations.Verifie_dispo_produit(produit=form.cleaned_data["produit"], date_debut=form.cleaned_data["date_debut"], date_fin=form.cleaned_data["date_fin"], location_exclue=object)
    if anomalies:
        for anomalie in anomalies:
            form.add_error("date_debut", anomalie)
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


def Supprime_occurences(idlocation=None, donnees=None, periode=None, self=None):
    # Importation des objets à supprimer
    objet_selection = Location.objects.get(pk=idlocation)
    if donnees == "OCCURENCE":
        objets = [objet_selection,]
    elif donnees == "PERIODE":
        date_debut, date_fin = utils_dates.ConvertDateRangePicker(periode)
        objets = Location.objects.filter(serie=objet_selection.serie, date_debut__date__gte=date_debut, date_fin__date__lte=date_fin)
    else:
        objets = Location.objects.filter(serie=objet_selection.serie)

    # Check protections
    protections = []
    prestations_facturees = {}
    for prestation in Prestation.objects.filter(location__in=objets, facture__isnull=False):
        prestations_facturees[prestation.location_id] = True
    for location in objets:
        if location.pk in prestations_facturees:
            protections.append("La location ID%d est déjà facturée" % location.pk)
    if protections:
        return "Suppression impossible : " + ". ".join(protections)

    # Suppression des objets
    for objet in objets:
        pk = objet.pk
        try:
            message_erreur = objet.delete()
            if isinstance(message_erreur, str):
                return message_erreur
        except ProtectedError as e:
            texte_resultats = crud.Formate_liste_objets(objets=e.protected_objects)
            return "La suppression de '%s' est impossible car cet élément est rattaché aux données suivantes : %s." % (objet, texte_resultats)

        # Enregistrement dans l'historique
        objet.pk = pk
        if self:
            self.save_historique(objet)

    return True
