# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.template.context_processors import csrf
from django.db.models import Count
from crispy_forms.utils import render_crispy_form
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import AchatDemande, AchatArticle
from core.utils import utils_parametres
from comptabilite.forms.achats_demandes import Formulaire
from comptabilite.forms.achats_demandes_articles import Formulaire as Formulaire_article


def Get_form_article(request):
    action = request.POST.get("action", None)
    index = request.POST.get("index", None)

    initial_data = {}
    if "valeur" in request.POST:
        initial_data = json.loads(request.POST["valeur"])
        initial_data["index"] = index

    # Création et rendu html du formulaire
    if action in ("ajouter", "modifier"):
        form = Formulaire_article(request=request, initial=initial_data)
        return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})

    # Validation du formulaire
    form = Formulaire_article(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["<b>%s</b> : %s " % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": messages_erreurs}, status=401)

    # Mémorisation du fournisseur et de la catégorie
    if form.cleaned_data["fournisseur"]:
        utils_parametres.Set(nom="fournisseur", categorie="achats_demandes_articles", utilisateur=request.user, valeur=form.cleaned_data["fournisseur"].pk)
    if form.cleaned_data["categorie"]:
        utils_parametres.Set(nom="categorie", categorie="achats_demandes_articles", utilisateur=request.user, valeur=form.cleaned_data["categorie"].pk)

    # Transformation en chaîne
    dict_retour = {
        "idarticle": form.cleaned_data["idarticle"],
        "fournisseur": form.cleaned_data["fournisseur"].pk if form.cleaned_data["fournisseur"] else None,
        "categorie": form.cleaned_data["categorie"].pk if form.cleaned_data["categorie"] else None,
        "libelle": form.cleaned_data["libelle"],
        "quantite": form.cleaned_data["quantite"],
        "observations": form.cleaned_data["observations"],
        "achete": form.cleaned_data["achete"],
    }
    return JsonResponse({"valeur": dict_retour, "index": form.cleaned_data["index"]})


class Page(crud.Page):
    model = AchatDemande
    url_liste = "achats_demandes_liste"
    url_ajouter = "achats_demandes_ajouter"
    url_modifier = "achats_demandes_modifier"
    url_supprimer = "achats_demandes_supprimer"
    description_liste = "Voici ci-dessous la liste des demandes d'achats."
    description_saisie = "Saisissez toutes les informations concernant la demande d'achats à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une demande d'achats"
    objet_pluriel = "des demandes d'achats"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)

        resultat = Form_valid(form=form, request=self.request, object=self.object)
        if resultat == True:
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=resultat))


def Form_valid(form=None, request=None, object=None):
    # Vérification du formulaire
    if not form.is_valid():
        return form

    # Récupération des articles
    articles = json.loads(form.cleaned_data.get("articles", "[]"))

    # Sauvegarde
    object = form.save()

    # Récupération des articles existants
    articles_existants = list(AchatArticle.objects.filter(demande=object))

    # Sauvegarde des articles
    for article in articles:
        idarticle = article["idarticle"] if article["idarticle"] else None
        AchatArticle.objects.update_or_create(pk=idarticle, defaults={"demande": object, "fournisseur_id": article[
            "fournisseur"], "categorie_id": article["categorie"], "libelle": article["libelle"], "quantite": article[
            "quantite"], "observations": article["observations"], "achete": article["achete"], })

    # Suppression des articles supprimés
    for article in articles_existants:
        if article.pk not in [int(a["idarticle"]) for a in articles if a["idarticle"]]:
            article.delete()

    # MAJ de l'état de la demande
    object.Maj_etat()

    return True


class Liste(Page, crud.Liste):
    model = AchatDemande

    def get_queryset(self):
        return AchatDemande.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_articles=Count("achatarticle"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["iddemande", "date", "etat", "date_echeance", "collaborateur", "libelle", "observations"]
        etat = columns.TextColumn("Etat", sources=["etat"], processor="Get_etat")
        collaborateur = columns.TextColumn("Collaborateur", sources=["collaborateur__nom", "collaborateur__prenom"], processor='Get_nom_collaborateur')
        nbre_articles = columns.TextColumn("Articles", sources="nbre_articles")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["iddemande", "etat", "date", "date_echeance", "collaborateur", "libelle", "nbre_articles", "observations"]
            ordering = ["date"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
                "date_echeance": helpers.format_date("%d/%m/%Y"),
            }

        def Get_nom_collaborateur(self, instance, *args, **kwargs):
            return instance.collaborateur.Get_nom() if instance.collaborateur else ""

        def Get_etat(self, instance, *args, **kwargs):
            if instance.etat == 100: return "<small class='badge badge-success'>100 %</small>"
            elif instance.etat == 0: return "<small class='badge badge-danger'>0 %</small>"
            else: return "<small class='badge badge-warning'>%d %%</small>" % instance.etat


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
