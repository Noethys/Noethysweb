# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import AchatArticle
from comptabilite.forms.achats_articles import Formulaire


def Modifier_achete(request):
    idarticle = int(request.POST["idarticle"])
    article = AchatArticle.objects.get(pk=idarticle)
    article.achete = not article.achete
    article.save()
    return JsonResponse({"succes": True})


class Page(crud.Page):
    model = AchatArticle
    url_liste = "achats_articles_liste"
    url_modifier = "achats_articles_modifier"
    url_supprimer = "achats_articles_supprimer"
    description_liste = "Voici ci-dessous la liste des articles. Vous pouvez cliquer sur le symbole de la colonne Acheté pour indiquer que l'article est acheté."
    description_saisie = "Saisissez toutes les informations concernant l'article et cliquez sur le bouton Enregistrer."
    objet_singulier = "un article"
    objet_pluriel = "des articles"

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)

        # Sauvegarde
        self.object = form.save()

        # MAJ de l'état de la demande
        if self.object.demande:
            self.object.demande.Maj_etat()

        return super().form_valid(form)


class Liste(Page, crud.Liste):
    model = AchatArticle
    template_name = "comptabilite/achats_articles.html"

    def get_queryset(self):
        condition_structure = Q(demande__structure__in=self.request.user.structures.all()) | Q(demande__structure__isnull=True)
        return AchatArticle.objects.select_related("categorie", "fournisseur", "demande", "demande__collaborateur").filter(self.Get_filtres("Q"), condition_structure)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idarticle", "libelle", "quantite", "fournisseur", "categorie", "demande__date", "demande__date_echeance", "demande__collaborateur", "demande__libelle", "demande__observations"]
        demande__collaborateur = columns.TextColumn("Collaborateur", sources=["demande__collaborateur__nom", "demande__collaborateur__prenom"], processor="Get_nom_collaborateur")
        demande__date = columns.TextColumn("Date demande", sources=["demande__date"], processor=helpers.format_date("%d/%m/%Y"))
        demande__date_echeance = columns.TextColumn("Date échéance", sources=["demande__date_echeance"], processor=helpers.format_date("%d/%m/%Y"))
        demande__libelle = columns.TextColumn("Libellé demande", sources=["demande__libelle"])
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idarticle", "achete", "libelle", "quantite", "fournisseur", "categorie", "observations", "demande__date", "demande__date_echeance", "demande__collaborateur", "demande__libelle"]
            ordering = ["libelle"]
            processors = {"achete": "Get_achete"}

        def Get_achete(self, instance, *args, **kwargs):
            return "<i class='fa %s' style='cursor: pointer;' onclick='modifier_achete(%d)' title='Cliquez ici pour modifier'></i>" % ("fa-check-circle-o text-green" if instance.achete else "fa-times-circle text-red", instance.pk)

        def Get_nom_collaborateur(self, instance, *args, **kwargs):
            return instance.demande.collaborateur.Get_nom() if instance.demande.collaborateur else ""


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass

    def delete(self, request, *args, **kwargs):
        article = self.get_object()
        article.delete()
        if article.demande:
            article.demande.Maj_etat()
        return HttpResponseRedirect(self.get_success_url())
