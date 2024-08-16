# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from decimal import Decimal
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Depot, Reglement
from core.utils import utils_texte
from reglements.forms.depots_reglements import Formulaire


class Page(crud.Page):
    model = Depot
    url_liste = "depots_reglements_liste"
    url_ajouter = "depots_reglements_ajouter"
    url_modifier = "depots_reglements_modifier"
    url_supprimer = "depots_reglements_supprimer"
    url_consulter = "depots_reglements_consulter"
    description_liste = "Voici ci-dessous la liste des dépôts de règlements."
    description_saisie = "Saisissez toutes les informations concernant le dépôt à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un dépôt de règlements"
    objet_pluriel = "des dépôts de règlements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Depot

    def get_queryset(self):
        return Depot.objects.select_related("compte").filter(self.Get_filtres("Q")).annotate(nbre_reglements=Count("reglement"), montant_reglements=Coalesce(Sum("reglement__montant"), Decimal(0)))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["iddepot", 'verrouillage', 'date', 'nom', 'montant', 'compte__nom', 'observations']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        verrouillage = columns.TextColumn("Verrouillage", sources=["montant"], processor='Get_verrouillage')
        nbre_reglements = columns.TextColumn("Nbre", sources="nbre_reglements")
        montant_reglements = columns.TextColumn("Total", sources="montant_reglements", processor="Formate_montant")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['iddepot', 'verrouillage', 'date', 'nom', 'nbre_reglements', 'montant_reglements', 'compte', 'observations']
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["date"]

        def Formate_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant_reglements)

        def Get_verrouillage(self, instance, **kwargs):
            if instance.verrouillage:
                return "<span class='text-green'><i class='fa fa-lock margin-r-5'></i> Verrouillé</span>"
            else:
                return "<span class='text-red'><i class='fa fa-unlock margin-r-5'></i> Non verrouillé</span>"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_consulter, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.iddepot})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, crud.Liste):
    template_name = "reglements/depots_reglements.html"
    mode = "CONSULTATION"
    model = Reglement
    boutons_liste = []
    url_supprimer_plusieurs = "depots_reglements_supprimer_plusieurs_reglements"

    def get_queryset(self):
        return Reglement.objects.select_related("famille", "depot").filter(self.Get_filtres("Q"), depot_id=self.kwargs["pk"])

    def Get_stats(self, iddepot=None):
        quantite = Reglement.objects.filter(depot_id=iddepot).count()
        stats = Reglement.objects.select_related('mode').values("mode__label").filter(depot_id=iddepot).annotate(total=Sum("montant"), nbre=Count("pk"))
        if not stats:
            texte = "<b>Aucun règlement inclus</b> : Cliquez sur 'Ajouter des règlements' pour commencer..."
        else:
            total = Decimal(0)
            liste_details = []
            for stat in stats:
                liste_details.append("%d %s (%s)" % (stat["nbre"], stat["mode__label"], utils_texte.Formate_montant(stat["total"])))
                total += stat["total"]
            texte = "<b>%d règlements (%s)</b> : %s." % (quantite, utils_texte.Formate_montant(total), utils_texte.Convert_liste_to_texte_virgules(liste_details))
            nbre_avis_a_envoyer = Reglement.objects.filter(depot_id=iddepot, avis_depot__isnull=True, famille__email_depots=True).count()
            if nbre_avis_a_envoyer:
                texte += " <span class='ml-2'><font color='red'><i class='fa fa-exclamation-circle'></i> %d avis de dépôt à envoyer</font></span>" % nbre_avis_a_envoyer
        return texte

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        depot = Depot.objects.get(pk=self.kwargs["pk"])
        context['box_titre'] = "Consulter un dépot"
        context['box_introduction'] = "Vous pouvez ici ajouter des règlements au dépot ou modifier les paramètres du dépôt."
        context['onglet_actif'] = "depots_reglements_liste"
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False if depot.verrouillage else True
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"iddepot": self.kwargs["pk"], "listepk": "xxx"})
        context['depot'] = depot
        context["stats"] = self.Get_stats(iddepot=self.kwargs["pk"])
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idreglement", "date", "mode__label", "emetteur__nom", "numero_piece", "payeur__nom", "montant", "date_differe", "avis_depot"]
        check = columns.CheckBoxSelectColumn(label="")
        mode = columns.TextColumn("Mode", sources=['mode__label'])
        emetteur = columns.CompoundColumn("Emetteur", sources=['emetteur__nom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        payeur = columns.TextColumn("Payeur", sources=['payeur__nom'])
        montant = columns.TextColumn("Montant", sources=["montant"], processor="Formate_montant")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idreglement", "date", "mode", "emetteur", "numero_piece", "montant", "famille", "payeur", "date_differe",
                       "numero_quittancier", "avis_depot", "actions"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "date_differe": helpers.format_date('%d/%m/%Y'),
                "avis_depot": helpers.format_date('%d/%m/%Y'),
                "montant": "Formate_montant",
            }
            labels = {
                "date_differe": "Différé",
                "avis_depot": "Avis dépôt",
            }
            hidden_columns = ["numero_quittancier", "avis_depot"]
            ordering = ["-idreglement"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            if instance.depot.verrouillage:
                return "<span class='text-green' title='Dépôt verrouillé'><i class='fa fa-lock margin-r-5'></i></span>"
            html = [
                self.Create_bouton_supprimer(url=reverse("depots_reglements_supprimer_reglement", kwargs={"iddepot": instance.depot_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)

        def Formate_montant(self, instance, **kwargs):
            return "%0.2f" % instance.montant


class Supprimer_reglement(Page, crud.Supprimer):
    model = Reglement
    objet_singulier = "un règlement"

    def delete(self, request, *args, **kwargs):
        # Modification du dépôt de ce règlement
        reglement = self.get_object()
        reglement.depot = None
        reglement.save()

        # Enregistrement du nouveau montant total du dépôt
        Depot.objects.get(pk=self.kwargs["iddepot"]).Maj_montant()

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppression effectuée avec succès')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["iddepot"]})


class Supprimer_plusieurs_reglements(Page, crud.Supprimer_plusieurs):
    model = Reglement
    objet_pluriel = "des règlements"

    def post(self, request, **kwargs):
        # Modification du dépôt de ces règlements
        for reglement in self.get_objets():
            reglement.depot = None
            reglement.save()

        # Enregistrement du nouveau montant total du dépôt
        Depot.objects.get(pk=self.kwargs["iddepot"]).Maj_montant()

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppressions effectuées avec succès')
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["iddepot"]})


def Impression_pdf(request):
    """ Impression du dépôt """
    from reglements.utils import utils_impression_depot_reglements
    dict_donnees = {"iddepot": int(request.POST.get("iddepot")), "tri_colonne": request.POST.get("tri_colonne"), "tri_sens": request.POST.get("tri_sens")}
    impression = utils_impression_depot_reglements.Impression(titre="Dépôt de règlements", dict_donnees=dict_donnees)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})
