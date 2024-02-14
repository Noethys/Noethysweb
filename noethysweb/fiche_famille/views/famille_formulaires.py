# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import SondageRepondant, SondageReponse, SondageQuestion, SondagePage
from fiche_famille.views.famille import Onglet
from portail.forms.sondage import Formulaire


class Page(Onglet):
    model = SondageRepondant
    url_liste = "famille_formulaires_liste"
    url_supprimer = "famille_formulaires_supprimer"
    description_liste = "Voici ci-dessous la liste des formulaires remplis par cette famille."
    objet_singulier = "un formulaire"
    objet_pluriel = "des formulaires"

    def get_success_url(self):
        return reverse_lazy(self.url_liste, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, crud.Liste):
    model = SondageRepondant
    template_name = "fiche_famille/famille_pieces.html"

    def get_queryset(self):
        return SondageRepondant.objects.select_related("sondage", "individu").filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Formulaires"
        context['onglet_actif'] = "outils"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idrepondant", "date_creation", "date_modification", "sondage__titre", "individu__nom", "individu__prenom"]
        sondage = columns.TextColumn("Sondage", sources=["sondage__titre"])
        individu = columns.TextColumn("Individu", sources=["individu__nom", "individu__prenom"], processor='Formate_individu')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idrepondant", "date_creation", "date_modification", "sondage", "individu", "actions"]
            processors = {
                "date_creation": helpers.format_date("%d/%m/%Y %H:%M"),
                "date_modification": helpers.format_date("%d/%m/%Y %H:%M"),
            }
            ordering = ["date_creation"]

        def Formate_individu(self, instance, **kwargs):
            return instance.individu.Get_nom() if instance.individu else ""

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("famille_voir_formulaire", kwargs={"idfamille": instance.famille_id, "pk": instance.pk}), title="Voir les réponses de ce formulaire", icone="fa-search"),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Voir(Onglet, TemplateView):
    template_name = "fiche_famille/famille_voir_formulaire.html"

    def get_context_data(self, **kwargs):
        context = super(Voir, self).get_context_data(**kwargs)
        context['box_titre'] = "Aperçu des réponses d'un formulaire"
        context['onglet_actif'] = "outils"

        # Importation du répondant et des réponses
        repondant = SondageRepondant.objects.select_related("sondage").get(pk=self.kwargs["pk"])
        context["repondant"] = repondant
        reponses = SondageReponse.objects.select_related("question").filter(repondant=repondant)

        # Création des pages et des formulaires
        liste_pages = []
        questions = SondageQuestion.objects.filter(page__sondage=repondant.sondage).order_by("ordre")
        for page in SondagePage.objects.filter(sondage_id=repondant.sondage).order_by("ordre"):
            liste_pages.append((page, Formulaire(request=self.request, page=page, questions=questions, reponses=reponses, lecture_seule=True)))
        context["pages"] = liste_pages

        return context


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"
