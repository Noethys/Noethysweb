# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, importlib, datetime, time
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PesLot, PesPiece, Facture, FiltreListe, Reglement, Payeur, Ventilation, Prestation
from core.utils import utils_texte
from facturation.forms.lots_pes import Formulaire, Formulaire_creation, Formulaire_piece


def Actions(request):
    """ Appliquer une action """
    num_action = int(request.POST["action"])
    liste_pk = json.loads(request.POST["liste_pieces"])

    # Importation des pièces
    liste_pieces = PesPiece.objects.select_related("facture", "lot", "lot__modele", "famille").filter(pk__in=liste_pk)

    # Changement de statut du prélèvement
    if num_action in (1, 2, 3):
        statuts = {1: "attente", 2: "valide", 3: "refus"}
        liste_pieces.update(prelevement_statut=statuts[num_action])

    # Si règlement automatique
    if num_action == 2:
        if liste_pieces.first().lot.modele.reglement_auto:
            num_action = 4

    # Régler
    if num_action == 4:
        for piece in liste_pieces:

            if not piece.lot.modele.mode:
                return JsonResponse({"erreur": "Vous devez définir un mode de règlement dans le modèle de l'export"}, status=401)

            if not piece.prelevement_reglement:

                # Récupération du payeur de la famille
                dernier_reglement = Reglement.objects.select_related("payeur").filter(famille=piece.famille).last()
                if dernier_reglement:
                    payeur = dernier_reglement.payeur
                else:
                    payeur = Payeur.objects.create(famille=piece.famille, nom=piece.famille.nom)

                # Création du règlement
                reglement = Reglement.objects.create(
                    famille=piece.famille, date=datetime.date.today(), mode=piece.lot.modele.mode,
                    montant=piece.montant, payeur=payeur, observations="Règlement automatique", compte=piece.lot.modele.compte)

                # Associe le règlement à la pièce
                piece.prelevement_reglement = reglement
                piece.save()

                # Création des ventilations
                for prestation in Prestation.objects.filter(facture=piece.facture):
                    Ventilation.objects.create(famille=piece.famille, reglement=reglement, prestation=prestation, montant=prestation.montant)

                # MAJ solde facture
                piece.facture.Maj_solde_actuel()

    # Ne pas régler
    if num_action == 5:
        for piece in liste_pieces:
            if piece.prelevement_reglement:
                piece.prelevement_reglement.delete()
                piece.facture.Maj_solde_actuel()

    return JsonResponse({"resultat": "ok"})


class Page(crud.Page):
    model = PesLot
    url_liste = "lots_pes_liste"
    url_ajouter = "lots_pes_creer"
    url_modifier = "lots_pes_modifier"
    url_supprimer = "lots_pes_supprimer"
    url_consulter = "lots_pes_consulter"
    description_liste = "Voici ci-dessous la liste des exports vers le Trésor Public."
    description_saisie = "Saisissez toutes les informations concernant l'export à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un export"
    objet_pluriel = "des exports"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = PesLot

    def get_queryset(self):
        return PesLot.objects.select_related("modele").filter(self.Get_filtres("Q")).annotate(nbre_pieces=Count("pespiece"), montant_pieces=Sum("pespiece__montant"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idlot", "date_emission", "nom", "format"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nbre_pieces = columns.TextColumn("Nbre", sources="nbre_pieces")
        montant_pieces = columns.TextColumn("Total", sources="montant_pieces", processor="Formate_montant")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idlot", "date_emission", "nom", "nbre_pieces", "montant_pieces", "modele", "observations"]
            processors = {
                "date_emission": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["date_emission"]

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
        context['box_introduction'] = "Vous devez sélectionner un modèle d'export."
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("lots_pes_ajouter", kwargs={"idmodele": request.POST.get("modele"), "assistant": request.POST.get("assistant")}))


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
            filtre = FiltreListe.objects.filter(nom="facturation.views.lots_pes_factures", parametres__contains="Dernières factures générées", utilisateur=self.request.user).first()
            if filtre:
                parametres_filtre = json.loads(filtre.parametres)
                idmin, idmax = parametres_filtre["criteres"]
                factures = Facture.objects.filter(pk__gte=idmin, pk__lte=idmax)

        # Insertion d'un lot de factures
        elif assistant and assistant > 0:
            factures = Facture.objects.filter(lot_id=assistant)

        if factures:
            # Création automatique des pièces
            from facturation.views.lots_pes_factures import Generation_pieces
            Generation_pieces(idlot=self.object.idlot, liste_idfacture=[facture.pk for facture in factures])

        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.idlot})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, crud.Liste):
    template_name = "facturation/lots_pes.html"
    mode = "CONSULTATION"
    model = PesPiece
    boutons_liste = []
    url_supprimer_plusieurs = "lots_pes_supprimer_plusieurs_pieces"

    def get_queryset(self):
        return PesPiece.objects.select_related("famille", "facture", "prelevement_mandat", "titulaire_helios").filter(self.Get_filtres("Q"), lot_id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Consulter un export"
        context['box_introduction'] = "Vous pouvez ici ajouter des pièces à l'export, modifier les paramètres de l'export ou générer le fichier d'export du format sélectionné. Cochez des pièces pour accéder aux actions complémentaires."
        context['onglet_actif'] = "lots_pes_liste"
        context['active_checkbox'] = True
        # context["hauteur_table"] = "400px"
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idlot": self.kwargs["pk"], "listepk": "xxx"})
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_attente", "action": "action_piece(1)", "title": "Mettre en attente", "label": "Attente"},
            {"id": "bouton_valide", "action": "action_piece(2)", "title": "Valider", "label": "Valide"},
            {"id": "bouton_refus", "action": "action_piece(3)", "title": "Refuser", "label": "Refus"},
            {"id": "bouton_regler", "action": "action_piece(4)", "title": "Régler", "label": "Régler"},
            {"id": "bouton_ne_pas_regler", "action": "action_piece(5)", "title": "Ne pas régler", "label": "Ne pas régler"},
        ])
        context['lot'] = PesLot.objects.select_related("modele").get(pk=self.kwargs["pk"])
        context["stats"] = PesPiece.objects.filter(lot_id=self.kwargs["pk"]).aggregate(
            total=Sum("montant"), nbre=Count("idpiece"),
            total_preleve=Sum("montant", filter=Q(prelevement=True)), nbre_preleve=Count("idpiece", filter=Q(prelevement=True)),
            total_non_preleve=Sum("montant", filter=Q(prelevement=False)), nbre_non_preleve=Count("idpiece", filter=Q(prelevement=False)),
        )
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idpiece", "famille", "montant", "prelevement", "prelevement_statut", "prelevement_sequence", "titulaire_helios", "facture"]
        check = columns.CheckBoxSelectColumn(label="")
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        montant = columns.TextColumn("Montant", sources=["montant"], processor="Formate_montant")
        prelevement_statut = columns.TextColumn("Statut", sources=["prelevement_statut"], processor="Formate_prelevement_statut")
        mandat = columns.TextColumn("Mandat", sources=["prelevement_mandat__rum"])
        facture = columns.TextColumn("Facture", sources=["facture__numero"])
        iban = columns.TextColumn("IBAN", sources=[], processor='Get_iban')
        bic = columns.TextColumn("BIC", sources=[], processor='Get_bic')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idpiece", "famille", "montant", "facture", "prelevement", "prelevement_statut", "prelevement_reglement", "mandat", "titulaire_helios", "iban", "bic", "actions"]
            hidden_columns = ["iban", "bic"]
            processors = {
                "montant": "Formate_montant",
                "prelevement": "Formate_prelevement",
                "prelevement_reglement": "Formate_reglement",
            }
            ordering = ["famille"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("lots_pes_modifier_piece", kwargs={"idlot": instance.lot_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("lots_pes_supprimer_piece", kwargs={"idlot": instance.lot_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)

        def Get_iban(self, instance, *args, **kwargs):
            return instance.prelevement_mandat.iban[:-5] + "*****" if instance.prelevement_mandat else None

        def Get_bic(self, instance, *args, **kwargs):
            return instance.prelevement_mandat.bic[:-5] + "*****" if instance.prelevement_mandat else None

        def Formate_prelevement_statut(self, instance, **kwargs):
            return instance.get_prelevement_statut_display()

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant)

        def Formate_prelevement(self, instance, **kwargs):
            if instance.prelevement:
                return "<span class='badge bg-success'><i class='fa fa-check margin-r-5'></i>Activé</span>"
            else:
                return "<span class='badge bg-danger'><i class='fa fa-close margin-r-5'></i>Non activé</span>"

        def Formate_reglement(self, instance, **kwargs):
            if instance.prelevement_reglement:
                return "<span class='badge bg-success'><i class='fa fa-check margin-r-5'></i>Oui</span>"
            else:
                return "<span class='badge bg-danger'><i class='fa fa-close margin-r-5'></i>Non</span>"


class Modifier_piece(Page, crud.Modifier):
    model = PesPiece
    form_class = Formulaire_piece
    objet_singulier = "une pièce d'export"
    description_saisie = "Renseignez les informations demandées et cliquez sur le bouton Enregistrer."

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['idlot']})


class Supprimer_piece(Page, crud.Supprimer):
    model = PesPiece
    objet_singulier = "une pièce d'export"

    def Apres_suppression(self, objet=None):
        if objet.prelevement_mandat:
            objet.prelevement_mandat.Actualiser()

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idlot"]})


class Supprimer_plusieurs_pieces(Page, crud.Supprimer_plusieurs):
    model = PesPiece
    objet_pluriel = "des pièces d'export"

    def Apres_suppression(self, objets=None):
        """ Actualisation du mandat si besoin """
        [objet.prelevement_mandat.Actualiser() for objet in objets if objet.prelevement_mandat]

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idlot"]})


def Exporter(request):
    """ Générer le fichier d'export """
    time.sleep(1)
    lot = PesLot.objects.get(pk=int(request.POST["idlot"]))
    module_export = importlib.import_module("facturation.utils.utils_export_%s" % lot.modele.format)
    export = module_export.Exporter(idlot=lot.pk, request=request)
    resultat = export.Generer()
    if not resultat:
        return JsonResponse({"erreurs": export.Get_erreurs_html()}, status=401)
    return JsonResponse({"resultat": "ok", "nom_fichier": resultat})


def Impression_pdf(request):
    """ Impression du lot """
    from facturation.utils import utils_impression_lot_pes
    impression = utils_impression_lot_pes.Impression(titre="Edition d'un export", dict_donnees={"idlot": int(request.POST.get("idlot"))})
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})
