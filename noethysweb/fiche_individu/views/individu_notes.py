# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Note, Individu
from fiche_individu.forms.individu_note import Formulaire
from fiche_individu.views.individu import Onglet


class Page(Onglet):
    model = Note
    url_liste = "individu_resume"
    url_ajouter = "individu_notes_ajouter"
    description_saisie = "Saisissez les caractéristiques de la note et cliquez sur le bouton Enregistrer."
    objet_singulier = "une note"
    objet_pluriel = "des notes"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Note"
        context['onglet_actif'] = "resume"
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idindividu"] = self.Get_idindividu()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)})



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_individu/individu_delete.html"
