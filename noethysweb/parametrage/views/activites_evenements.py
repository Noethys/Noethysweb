# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import re
from copy import deepcopy
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.utils import utils_preferences, utils_dates
from core.models import Evenement, Ouverture, Tarif, TarifLigne
from parametrage.views.activites import Onglet
from parametrage.forms.activites_evenements import Formulaire


class Page(Onglet):
    model = Evenement
    url_liste = "activites_evenements_liste"
    url_ajouter = "activites_evenements_ajouter"
    url_modifier = "activites_evenements_modifier"
    url_supprimer = "activites_evenements_supprimer"
    description_liste = "Vous pouvez saisir ici des événements pour l'activité. Vous devez avoir au préalable créé au moins une unité de consommation de type 'Evénementiel'."
    description_saisie = "Saisissez toutes les informations concernant l'événement à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un événement"
    objet_pluriel = "des événements"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Evénements"
        context['onglet_actif'] = "evenements"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idactivite': self.Get_idactivite()}), "icone": "fa fa-plus"},
            {"label": "Catégories d'événements", "classe": "btn btn-default", "href": reverse_lazy("activites_evenements_categories_liste", kwargs={'idactivite': self.Get_idactivite()}), "icone": "fa fa-gear"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idactivite"] = self.Get_idactivite()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idactivite': self.Get_idactivite()})

    def Copie_tarifs_evenement_existant(self, evenement=None, copie_evenement=None):
        for tarif in Tarif.objects.filter(evenement=copie_evenement):
            nouveau_tarif = deepcopy(tarif)

            # Duplication d'une tarif existant
            nouveau_tarif.pk = None
            nouveau_tarif.evenement = evenement
            nouveau_tarif.date_debut = evenement.date
            nouveau_tarif.date_fin = evenement.date
            nouveau_tarif.save()

            # Recopie également les champs manytomany
            nouveau_tarif.categories_tarifs.add(*tarif.categories_tarifs.all())
            nouveau_tarif.groupes.add(*tarif.groupes.all())
            nouveau_tarif.cotisations.add(*tarif.cotisations.all())
            nouveau_tarif.caisses.add(*tarif.caisses.all())

            # Recopie les lignes de tarifs
            for ligne_tarif in TarifLigne.objects.filter(tarif=tarif):
                ligne_tarif.pk = None
                ligne_tarif.tarif = nouveau_tarif
                ligne_tarif.save()


class Liste(Page, crud.Liste):
    model = Evenement
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        return Evenement.objects.filter(Q(activite=self.Get_idactivite()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        return context

    class datatable_class(MyDatatable):
        filtres = ['idevenement', 'date', 'groupe__nom', 'nom', 'unite__nom']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        tarification = columns.TextColumn("Tarification", sources=None, processor='Get_tarification')
        groupe = columns.TextColumn("Groupe", sources=["groupe__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idevenement', 'date', 'nom', 'groupe', 'tarification']
            ordering = ['date']
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }

        def Get_tarification(self, instance, *args, **kwargs):
            # Importation des tarifs avancés
            if not hasattr(self, "dict_tarifs"):
                self.dict_tarifs = {}
                for tarif in Tarif.objects.filter(evenement__isnull=False):
                    if tarif.evenement not in self.dict_tarifs:
                        self.dict_tarifs[tarif.evenement] = []
                    self.dict_tarifs[tarif.evenement].append(tarif)

            # Affichage du texte de la colonne tarification
            if instance.montant:
                return "%.2f %s" % (instance.montant, utils_preferences.Get_symbole_monnaie())
            if instance in self.dict_tarifs:
                pluriel = "s" if len(self.dict_tarifs[instance]) > 1 else ""
                texte = "%d tarif%s avancé%s" % (len(self.dict_tarifs[instance]), pluriel, pluriel)
            else:
                texte = "Gratuit"
            url_liste = reverse("activites_evenements_tarifs_liste", args=[instance.activite_id, instance.pk])
            return texte + """&nbsp; <a type='button' class='btn btn-default btn-sm' href='%s' title='Ajouter, modifier ou supprimer des tarifs avancés'><i class="fa fa-gear"></i></a>""" % url_liste

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.pk])),
            ]
            return self.Create_boutons_actions(html)



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def form_valid(self, form):
        # Enregistre d'abord l'événement
        redirect = super(Ajouter, self).form_valid(form)
        liste_evenements = [form.instance]

        # Si dates multiples, création de tous les évènements
        if form.cleaned_data["mode_saisie"] == "MULTIPLE":
            for date in [utils_dates.ConvertDateFRtoDate(datefr.strip()) for datefr in re.split(';|,', form.cleaned_data["dates_multiples"])][1:]:
                nouveau_evenement = deepcopy(form.instance)
                nouveau_evenement.pk = None
                nouveau_evenement.date = date
                nouveau_evenement.save()
                liste_evenements.append(nouveau_evenement)

        # Ouverture du calendrier et duplication de tarifs
        for evenement in liste_evenements:
            # Après l'ajout d'un événement, on ouvre le calendrier si besoin
            if Ouverture.objects.filter(date=evenement.date, groupe=evenement.groupe, unite=evenement.unite).count() == 0:
                Ouverture.objects.create(date=evenement.date, activite=evenement.activite, groupe=evenement.groupe, unite=evenement.unite)
                messages.add_message(self.request, messages.INFO, "Une ouverture a été créée automatiquement dans le calendrier")

            # Copie des tarifs d'un événement existant
            if form.cleaned_data.get("type_tarification") == "EXISTANT":
                copie_evenement = form.cleaned_data.get("copie_evenement")
                self.Copie_tarifs_evenement_existant(evenement=evenement, copie_evenement=copie_evenement)

        return redirect


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def form_valid(self, form):
        # près la modification d'un événement, on vérifie que la date est toujours exacte dans les tarifs avancés associés
        evenement = form.instance
        for tarif in Tarif.objects.filter(evenement=evenement):
            if tarif.date_debut != evenement.date or tarif.date_fin != evenement.date:
                tarif.date_debut = evenement.date
                tarif.date_fin = evenement.date
                tarif.save()

        # Copie des tarifs d'un événement existant
        if form.cleaned_data.get("type_tarification") == "EXISTANT":
            copie_evenement = form.cleaned_data.get("copie_evenement")
            self.Copie_tarifs_evenement_existant(evenement=evenement, copie_evenement=copie_evenement)

        return super(Modifier, self).form_valid(form)


class Supprimer(Page, crud.Supprimer):
    template_name = "parametrage/activite_delete.html"
