# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Inscription, Individu, Activite, Groupe, CategorieTarif, Consommation
from fiche_individu.forms.individu_inscriptions import Formulaire
from fiche_individu.views.individu import Onglet
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Template, RequestContext
from django.db.models import Q
from django.contrib import messages
from individus.utils import utils_forfaits
import datetime


def Get_groupes(request):
    idactivite = request.POST.get('idactivite')
    if idactivite == "":
        resultat = ""
    else:
        groupes = Groupe.objects.filter(activite_id=idactivite).order_by('ordre')
        html = """
        <option value="">---------</option>
        {% for groupe in groupes %}
            <option value="{{ groupe.pk }}">{{ groupe.nom }}</option>
        {% endfor %}
        """
        context = {'groupes': groupes}
        resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


def Get_categories_tarifs(request):
    idactivite = request.POST.get('idactivite')
    if idactivite == "":
        resultat = ""
    else:
        categories_tarifs = CategorieTarif.objects.filter(activite_id=idactivite).order_by('nom')
        html = """
        <option value="">---------</option>
        {% for categorie in categories_tarifs %}
            <option value="{{ categorie.pk }}">{{ categorie.nom }}</option>
        {% endfor %}
        """
        context = {'categories_tarifs': categories_tarifs}
        resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)




class Page(Onglet):
    model = Inscription
    url_liste = "individu_inscriptions_liste"
    url_ajouter = "individu_inscriptions_ajouter"
    url_modifier = "individu_inscriptions_modifier"
    url_supprimer = "individu_inscriptions_supprimer"
    description_liste = "Saisissez ici les inscriptions de l'individu."
    description_saisie = "Saisissez toutes les informations concernant l'inscription et cliquez sur le bouton Enregistrer."
    objet_singulier = "une inscription"
    objet_pluriel = "des inscriptions"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Inscriptions"
        context['onglet_actif'] = "inscriptions"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
        ]
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idindividu"] = self.Get_idindividu()
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)})

    def check_inscriptions_existantes(self, form=None, instance=None):
        # On vérifie si l'individu est déjà inscrit à cette activité sur cette famille
        activite = form.cleaned_data["activite"]
        if not activite.inscriptions_multiples:
            date_debut = form.cleaned_data["date_debut"]
            date_fin = form.cleaned_data["date_fin"] if form.cleaned_data["date_fin"] else datetime.date(2999, 12, 31)
            inscriptions_paralleles = []
            for inscription in Inscription.objects.filter(individu=form.cleaned_data["individu"], famille=form.cleaned_data["famille"], activite=form.cleaned_data["activite"]):
                date_fin_temp = inscription.date_fin if inscription.date_fin else datetime.date(2999, 12, 31)
                if inscription.date_debut <= date_fin and date_fin_temp >= date_debut and inscription != instance:
                    inscriptions_paralleles.append(inscription)
            if inscriptions_paralleles:
                messages.add_message(self.request, messages.ERROR, "Inscription impossible : Cet individu est déjà inscrit à cette activité sur cette période et sur cette famille")
                return False
        return True


class Liste(Page, crud.Liste):
    model = Inscription
    template_name = "fiche_individu/individu_liste.html"

    def get_queryset(self):
        return Inscription.objects.select_related("activite", "groupe", "categorie_tarif", "famille", "activite__structure").filter(Q(individu=self.Get_idindividu()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['box_conclusion'] = """<a class="btn btn-default" href="%s"><i class="fa fa-calendar-plus-o margin-r-5"></i> Appliquer un forfait daté</a>""" % reverse_lazy("individu_appliquer_forfait_date", args=(self.kwargs['idfamille'], self.kwargs['idindividu']))
        return context

    class datatable_class(MyDatatable):
        filtres = ["idinscription", 'date_debut', 'date_fin', 'activite', 'groupe', 'categorie_tarif', 'statut']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=['categorie_tarif__nom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idinscription", 'date_debut', 'date_fin', 'activite', 'groupe', 'categorie_tarif', 'statut', 'famille']
            #hidden_columns = = ["idinscription"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'statut': 'Formate_statut',
            }
            ordering = ['date_debut']

        def Formate_statut(self, instance, *args, **kwargs):
            if instance.statut == "attente":
                return "<i class='fa fa-hourglass-2 text-orange'></i> Attente"
            elif instance.statut == "refus":
                return "<i class='fa fa-times-circle text-red'></i> Refus"
            else:
                return "<i class='fa fa-check-circle-o text-green'></i> Valide"

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            if instance.activite.structure in view.request.user.structures.all():
                # Affiche les boutons d'action si l'utilisateur est associé à l'activité
                html = [
                    self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                    self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                ]
            else:
                # Afficher que l'accès est interdit
                html = ["<span class='text-red'><i class='fa fa-minus-circle margin-r-5' title='Accès non autorisé'></i>Accès interdit</span>",]
            return self.Create_boutons_actions(html)



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"

    def form_valid(self, form):
        # On vérifie si l'individu est déjà inscrit à cette activité sur cette famille
        if self.check_inscriptions_existantes(form, instance=self.object) == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde de l'aide
        self.object = form.save()
        messages.add_message(self.request, messages.SUCCESS, "L'inscription a bien été enregistrée")

        # Enregistre un forfait si besoin
        f = utils_forfaits.Forfaits(request=self.request, famille=self.object.famille_id, activites=[self.object.activite_id], individus=[self.object.individu_id])
        f.Applique_forfait(mode_inscription=True, selection_activite=self.object.activite_id)

        # Mémorisation dans l'historique
        self.save_historique(instance=self.object, form=form)

        return HttpResponseRedirect(self.get_success_url())


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"

    def test_func(self):
        """ Vérifie que l'utilisateur peut se connecter à cette page """
        if not super(Modifier, self).test_func():
            return False
        inscription = Inscription.objects.select_related("activite", "activite__structure").get(pk=self.kwargs["pk"])
        if inscription.activite.structure not in self.request.user.structures.all():
            return False
        return True

    def form_valid(self, form):
        # On vérifie si l'individu est déjà inscrit à cette activité sur cette famille
        if self.check_inscriptions_existantes(form, instance=self.object) == False:
            return self.render_to_response(self.get_context_data(form=form))

        # On vérifie qu'il n'existe pas de consommations associées en dehors de la période de la réservation
        if form.cleaned_data["date_fin"]:
            condition = Q(inscription=self.object) & (Q(date__lt=form.cleaned_data["date_debut"]) | Q(date__gt=form.cleaned_data["date_fin"]))
        else:
            condition = Q(inscription=self.object, date__lte=form.cleaned_data["date_debut"])
        liste_conso = Consommation.objects.filter(condition).count()
        if liste_conso:
            messages.add_message(self.request, messages.ERROR, "Modification impossible : %d consommations existent déjà hors de la période d'inscription sélectionnée")
            return self.render_to_response(self.get_context_data(form=form))

        return super(Modifier, self).form_valid(form)


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_individu/individu_delete.html"

    def test_func(self):
        """ Vérifie que l'utilisateur peut se connecter à cette page """
        if not super(Supprimer, self).test_func():
            return False
        inscription = Inscription.objects.select_related("activite", "activite__structure").get(pk=self.kwargs["pk"])
        if inscription.activite.structure not in self.request.user.structures.all():
            return False
        return True

    def Avant_suppression(self, objet=None):
        """ Suppression des conso forfait supprimables """
        liste_conso = Consommation.objects.filter(inscription=objet)
        nbre_conso_forfait = 0
        for conso in liste_conso:
            if conso.forfait == 2 and conso.etat == "reservation":
                nbre_conso_forfait += 1

        # Si ce sont toutes des conso associées à un forfait supprimable
        if nbre_conso_forfait == len(liste_conso):
            for conso in liste_conso:
                conso.delete()

        return True
