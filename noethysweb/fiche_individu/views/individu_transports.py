# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, uuid
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Template, RequestContext
from datatableview.views import MultipleDatatableView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Transport, TransportCompagnie, TransportLigne, TransportLieu, TransportArret, Vacance, Ferie
from core.utils import utils_dates
from fiche_individu.forms.individu_transport import Formulaire
from fiche_individu.views.individu import Onglet


def Get_info_transport(request):
    categorie = request.POST.get("categorie")
    champ = request.POST.get("champ")
    idligne = request.POST.get("ligne", 0) or 0
    resultat = ""
    if categorie and champ:
        donnees = []
        if champ == "compagnie": donnees = TransportCompagnie.objects.filter(categorie=categorie).order_by("nom")
        if champ == "ligne": donnees = TransportLigne.objects.filter(categorie=categorie).order_by("nom")
        if "lieu" in champ: donnees = TransportLieu.objects.filter(categorie=categorie).order_by("nom")
        if "arret" in champ: donnees = TransportArret.objects.filter(ligne_id=idligne).order_by("ordre")
        if donnees:
            html = """
            <option value="">---------</option>
            {% for donnee in donnees %}
                <option value="{{ donnee.pk }}">{{ donnee.nom }}</option>
            {% endfor %}
            """
            resultat = Template(html).render(RequestContext(request, {"donnees": donnees}))
    return HttpResponse(resultat)


class Page(Onglet):
    url_liste = "individu_transports_liste"
    description_saisie = "Saisissez toutes les informations et cliquez sur le bouton Enregistrer."
    objet_singulier = ""
    objet_pluriel = ""

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Transports"
        context['onglet_actif'] = "transports"
        if self.request.user.has_perm("core.individu_transports_modifier"):
            context['boutons_liste_progtransports'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("individu_progtransports_ajouter", kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.Get_idfamille()}), "icone": "fa fa-plus"},
            ]
            context['boutons_liste_transports'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("individu_transports_ajouter", kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.Get_idfamille()}), "icone": "fa fa-plus"},
            ]
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.individu_transports_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idindividu"] = self.Get_idindividu()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST and self.request.POST.get("page") == "progtransport":
            url = "individu_progtransports_ajouter"
        if "SaveAndNew" in self.request.POST and self.request.POST.get("page") == "transport":
            url = "individu_transports_ajouter"
        return reverse_lazy(url, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, MultipleDatatableView):
    template_name = "fiche_individu/individu_transports.html"

    class progtransports_datatable_class(MyDatatable):
        categorie = columns.TextColumn("Catégorie", sources="categorie", processor="Get_categorie")
        origine = columns.TextColumn("Origine", sources=None, processor="Get_origine")
        destination = columns.TextColumn("Destination", sources=None, processor="Get_destination")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            model = Transport
            structure_template = MyDatatable.structure_template
            columns = ["idtransport", "categorie", "date_debut", "date_fin", "origine", "destination"]
            ordering = ["idtransport"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }
            footer = False

        def Get_categorie(self, instance, **kwargs):
            return instance.get_categorie_display()

        def Get_origine(self, instance, **kwargs):
            if instance.depart_lieu: return instance.depart_lieu.nom
            if instance.depart_arret: return instance.depart_arret.nom
            if instance.depart_localisation: return instance.depart_localisation
            return ""

        def Get_destination(self, instance, **kwargs):
            if instance.arrivee_lieu: return instance.arrivee_lieu.nom
            if instance.arrivee_arret: return instance.arrivee_arret.nom
            if instance.arrivee_localisation: return instance.arrivee_localisation
            return ""

        def Get_actions_speciales(self, instance, *args, **kwargs):
            if not kwargs["view"].request.user.has_perm("core.individu_transports_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = kwargs["view"].kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse("individu_progtransports_modifier", kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse("individu_progtransports_supprimer", kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)


    class transports_datatable_class(MyDatatable):
        categorie = columns.TextColumn("Catégorie", sources="categorie", processor="Get_categorie")
        origine = columns.TextColumn("Origine", sources=None, processor="Get_origine")
        destination = columns.TextColumn("Destination", sources=None, processor="Get_destination")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            model = Transport
            structure_template = MyDatatable.structure_template
            columns = ["idtransport", "categorie"]#, "depart_date", "depart_heure", "origine", "arrivee_date", "arrivee_heure", "destination"]
            processors = {
                "depart_date": helpers.format_date("%d/%m/%Y"),
                "arrivee_date": helpers.format_date("%d/%m/%Y"),
                "depart_heure": helpers.format_date("%H:%M"),
                "arrivee_heure": helpers.format_date("%H:%M"),
            }
            labels = {
                "depart_date": "Date dép.",
                "depart_heure": "Heure dép.",
                "arrivee_date": "Date arr.",
                "arrivee_heure": "Heure arr.",
            }
            ordering = ["idtransport"]
            footer = False

        def Get_categorie(self, instance, **kwargs):
            return instance.get_categorie_display()

        def Get_origine(self, instance, **kwargs):
            if instance.depart_lieu: return instance.depart_lieu.nom
            if instance.depart_arret: return instance.depart_arret.nom
            if instance.depart_localisation: return instance.depart_localisation
            return ""

        def Get_destination(self, instance, **kwargs):
            if instance.arrivee_lieu: return instance.arrivee_lieu.nom
            if instance.arrivee_arret: return instance.arrivee_arret.nom
            if instance.arrivee_localisation: return instance.arrivee_localisation
            return ""

        def Get_actions_speciales(self, instance, *args, **kwargs):
            if not kwargs["view"].request.user.has_perm("core.individu_transports_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = kwargs["view"].kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse("individu_transports_modifier", kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse("individu_transports_supprimer", kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)

    datatable_classes = {
        'progtransports': progtransports_datatable_class,
        'transports': transports_datatable_class,
    }

    def get_progtransports_datatable_queryset(self):
        return Transport.objects.filter(mode="PROG", individu=self.Get_idindividu())

    def get_transports_datatable_queryset(self):
        return Transport.objects.select_related("depart_lieu", "arrivee_lieu", "depart_arret", "arrivee_arret").filter(mode="TRANSP", individu=self.Get_idindividu())

    def get_datatables(self, only=None):
        datatables = super(Liste, self).get_datatables(only)
        return datatables



class Ajouter_progtransport(Page, crud.Ajouter):
    form_class = Formulaire
    model = Transport
    template_name = "fiche_individu/individu_edit.html"
    mode = "PROG"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Programmations de transports"
        context['onglet_actif'] = "transports"
        return context


class Modifier_progtransport(Page, crud.Modifier):
    form_class = Formulaire
    model = Transport
    template_name = "fiche_individu/individu_edit.html"
    mode = "PROG"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Programmations de transports"
        context['onglet_actif'] = "transports"
        return context


class Supprimer_progtransport(Page, crud.Supprimer):
    model = Transport
    template_name = "fiche_individu/individu_delete.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Programmations de transports"
        context['onglet_actif'] = "transports"
        return context


class Ajouter_transport(Page, crud.Ajouter):
    form_class = Formulaire
    model = Transport
    template_name = "fiche_individu/individu_edit.html"
    mode = "TRANSP"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Transports"
        context['onglet_actif'] = "transports"
        return context

    def form_valid(self, form):
        # Vérification du formulaire
        if not form.is_valid():
            self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde du transport
        if form.cleaned_data["recurrence"] == "AUCUNE":
            object = form.save()

        if form.cleaned_data["recurrence"] == "PERIODE":
            serie = str(uuid.uuid4())
            for date in self.Calcule_occurences(form.cleaned_data):
                transport = Transport.objects.create(
                    individu=form.cleaned_data["individu"], mode=form.cleaned_data["mode"], categorie=form.cleaned_data["categorie"],
                    ligne=form.cleaned_data["ligne"], numero=form.cleaned_data["numero"],
                    details=form.cleaned_data["details"], observations=form.cleaned_data["observations"],
                    depart_date=date, depart_heure=form.cleaned_data["depart_heure"], depart_arret=form.cleaned_data["depart_arret"],
                    depart_lieu=form.cleaned_data["depart_lieu"], depart_localisation=form.cleaned_data["depart_localisation"],
                    arrivee_date=date, arrivee_heure=form.cleaned_data["arrivee_heure"],
                    arrivee_arret=form.cleaned_data["arrivee_arret"], arrivee_lieu=form.cleaned_data["arrivee_lieu"],
                    arrivee_localisation=form.cleaned_data["arrivee_localisation"],
                ) # serie=serie,

        return HttpResponseRedirect(self.get_success_url())

    def Calcule_occurences(self, cleaned_data={}):
        """ Calcule les occurences """
        liste_resultats = []

        liste_vacances = Vacance.objects.all()
        liste_feries = Ferie.objects.all()

        cleaned_data["recurrence_jours_vacances"] = [int(x) for x in cleaned_data["recurrence_jours_vacances"]]
        cleaned_data["recurrence_jours_scolaires"] = [int(x) for x in cleaned_data["recurrence_jours_scolaires"]]

        # Liste dates
        listeDates = [cleaned_data["recurrence_date_debut"], ]
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
                liste_resultats.append(date)

            dateTemp = date
        return liste_resultats


class Modifier_transport(Page, crud.Modifier):
    form_class = Formulaire
    model = Transport
    template_name = "fiche_individu/individu_edit.html"
    mode = "TRANSP"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Transports"
        context['onglet_actif'] = "transports"
        return context


class Supprimer_transport(Page, crud.Supprimer):
    model = Transport
    template_name = "fiche_individu/individu_delete.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Transports"
        context['onglet_actif'] = "transports"
        return context
