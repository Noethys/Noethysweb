# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, importlib
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PrelevementsLot, Prelevements, Facture, Mandat, FiltreListe
from core.utils import utils_texte
from facturation.forms.lots_prelevements import Formulaire, Formulaire_creation, Formulaire_piece


class Page(crud.Page):
    model = PrelevementsLot
    url_liste = "lots_prelevements_liste"
    url_ajouter = "lots_prelevements_creer"
    url_modifier = "lots_prelevements_modifier"
    url_supprimer = "lots_prelevements_supprimer"
    url_consulter = "lots_prelevements_consulter"
    description_liste = "Voici ci-dessous la liste des prélèvements."
    description_saisie = "Saisissez toutes les informations concernant le lot à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un lot de prélèvements"
    objet_pluriel = "des lots de prélèvements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = PrelevementsLot

    def get_queryset(self):
        return PrelevementsLot.objects.select_related("modele").filter(self.Get_filtres("Q")).annotate(nbre_pieces=Count("prelevements"), montant_pieces=Sum("prelevements__montant"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idlot", "date", "nom", "format"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nbre_pieces = columns.TextColumn("Nbre", sources="nbre_pieces")
        montant_pieces = columns.TextColumn("Total", sources="montant_pieces", processor="Formate_montant")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idlot", "date", "nom", "nbre_pieces", "montant_pieces", "modele", "observations"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["date"]

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant_pieces)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_consulter, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Creer(Page, crud.Ajouter):
    form_class = Formulaire_creation
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Creer, self).get_context_data(**kwargs)
        context['box_introduction'] = "Vous devez sélectionner un modèle."
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("lots_prelevements_ajouter", kwargs={"idmodele": request.POST.get("modele"), "assistant": request.POST.get("assistant")}))


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idmodele"] = self.kwargs.get("idmodele", None)
        form_kwargs["assistant"] = self.kwargs.get("assistant", None)
        return form_kwargs

    def get_success_url(self):
        # Assistant d'insertion automatique des factures
        assistant = self.kwargs.get("assistant", None)
        factures = []

        # Insertion des dernières factures générées
        if assistant == 999999:
            filtre = FiltreListe.objects.filter(nom="facturation.views.lots_prelevements_factures", parametres__contains="Dernières factures générées", utilisateur=self.request.user).first()
            if filtre:
                parametres_filtre = json.loads(filtre.parametres)
                idmin, idmax = parametres_filtre["criteres"]
                factures = Facture.objects.filter(pk__gte=idmin, pk__lte=idmax)

        # Insertion d'un lot de factures
        elif assistant and assistant > 0:
            factures = Facture.objects.filter(lot_id=assistant)

        if factures:
            # Création automatique des pièces
            from facturation.views.lots_prelevements_factures import Generation_pieces
            Generation_pieces(idlot=self.object.idlot, liste_idfacture=[facture.pk for facture in factures])

        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.idlot})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, crud.Liste):
    template_name = "facturation/lots_prelevements.html"
    mode = "CONSULTATION"
    model = Prelevements
    boutons_liste = []
    url_supprimer_plusieurs = "lots_prelevements_supprimer_plusieurs_pieces"

    def get_queryset(self):
        return Prelevements.objects.select_related("famille", "facture", "mandat").filter(self.Get_filtres("Q"), lot_id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Consulter un lot"
        context['box_introduction'] = "Vous pouvez ici ajouter des pièces au lot, modifier les paramètres de l'export ou générer le fichier d'export du format sélectionné."
        context['onglet_actif'] = "lots_prelevements_liste"
        context['active_checkbox'] = True
        # context["hauteur_table"] = "400px"
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idlot": self.kwargs["pk"], "listepk": "xxx"})
        context['lot'] = PrelevementsLot.objects.select_related("modele").get(pk=self.kwargs["pk"])
        context["stats"] = Prelevements.objects.filter(lot_id=self.kwargs["pk"]).aggregate(total=Sum("montant"), nbre=Count("idprelevement"))
        return context

    class datatable_class(MyDatatable):
        filtres = ["fpresent:famille", "fscolarise:famille", "idprelevement", "famille", "montant", "statut", "sequence", "facture"]
        check = columns.CheckBoxSelectColumn(label="")
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        montant = columns.TextColumn("Montant", sources=["montant"], processor="Formate_montant")
        statut = columns.TextColumn("Statut", sources=["statut"], processor="Formate_statut")
        mandat = columns.TextColumn("Mandat", sources=["mandat__rum"])
        facture = columns.TextColumn("Facture", sources=["facture__numero"])
        iban = columns.TextColumn("IBAN", sources=[], processor='Get_iban')
        bic = columns.TextColumn("BIC", sources=[], processor='Get_bic')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idprelevement", "famille", "montant", "facture", "statut", "sequence", "mandat", "iban", "bic", "actions"]
            hidden_columns = ["iban", "bic"]
            processors = {
                "montant": "Formate_montant",
            }
            ordering = ["famille"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("lots_prelevements_modifier_piece", kwargs={"idlot": instance.lot_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("lots_prelevements_supprimer_piece", kwargs={"idlot": instance.lot_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)

        def Get_iban(self, instance, *args, **kwargs):
            return instance.mandat.iban if instance.mandat else None

        def Get_bic(self, instance, *args, **kwargs):
            return instance.mandat.bic if instance.mandat else None

        def Formate_statut(self, instance, **kwargs):
            return instance.get_statut_display()

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant)


class Modifier_piece(Page, crud.Modifier):
    model = Prelevements
    form_class = Formulaire_piece
    objet_singulier = "un prélèvement"
    description_saisie = "Renseignez les informations demandées et cliquez sur le bouton Enregistrer."

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['idlot']})


class Supprimer_piece(Page, crud.Supprimer):
    model = Prelevements
    objet_singulier = "un prélèvement"

    def Apres_suppression(self, objet=None):
        if objet.mandat:
            objet.mandat.Actualiser()

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idlot"]})


class Supprimer_plusieurs_pieces(Page, crud.Supprimer_plusieurs):
    model = Prelevements
    objet_pluriel = "des prélèvements"

    def Apres_suppression(self, objets=None):
        """ Actualisation du mandat si besoin """
        [objet.mandat.Actualiser() for objet in objets if objet.mandat]

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idlot"]})


def Exporter(request):
    """ Générer le fichier d'export """
    lot = PrelevementsLot.objects.get(pk=int(request.POST["idlot"]))
    from facturation.utils import utils_export_prelevements
    export = utils_export_prelevements.Exporter(idlot=lot.pk, request=request)
    resultat = export.Generer()
    if not resultat:
        return JsonResponse({"erreurs": export.Get_erreurs_html()}, status=401)
    return JsonResponse({"resultat": "ok", "nom_fichier": resultat})


def Impression_pdf(request):
    """ Impression du lot """
    from facturation.utils import utils_impression_lot_prelevements
    impression = utils_impression_lot_prelevements.Impression(titre="Prélèvements", dict_donnees={"idlot": int(request.POST.get("idlot"))})
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})
