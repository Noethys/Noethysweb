#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.utils.html import format_html
from django.urls import reverse_lazy, reverse
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datatableview import Datatable, columns, helpers
from datatableview.views import DatatableView, MultipleDatatableView, XEditableDatatableView
from core.utils import utils_texte, utils_parametres
from core.models import Parametre


class MyDatatableView(DatatableView):
    pass


class MyMultipleDatatableView(MultipleDatatableView):
    pass


class Deplacer_lignes(View):
    """ A surcharger avec un model pour activer le déplacement des lignes dans la liste """
    model = None

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(Deplacer_lignes, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = request.POST.get("deplacements")
        dict_deplacements = json.loads(data)
        for id, new_ordre in dict_deplacements.items():
            niveau = self.model.objects.get(pk=int(id))
            niveau.ordre = int(new_ordre)
            niveau.save()
        return JsonResponse({'status': 'Success'})


class MyDatatable(Datatable):
    structure_template = "core/widgets/datatableview/bootstrap_structure.html"

    def __init__(self, *args, **kwargs):
        nom_view = str(kwargs["view"])
        nom_view = nom_view[1:nom_view.find(".Liste ")]
        request = kwargs["view"].request

        # Importation des paramètres de la liste
        parametres = {parametre.categorie: utils_parametres.To_python(parametre.parametre, None) for parametre in Parametre.objects.filter(nom=nom_view, utilisateur=request.user)}

        # Tri mémorisé de la liste
        if parametres.get("tri_liste", None):
            nom_colonne, sens = parametres["tri_liste"].split(";")
            self._meta.ordering = ["%s%s" % ("-" if sens == "desc" else "", nom_colonne)]

        # Colonnes cachées mémorisées
        if parametres.get("hidden_columns", None):
            self._meta.hidden_columns = json.loads(parametres["hidden_columns"])

        # Page length mémorisées
        if parametres.get("page_length", None):
            self._meta.page_length = parametres["page_length"]

        super(MyDatatable, self).__init__(*args, **kwargs)

        # vérifie que les hidden columns sont bien cachées
        if parametres.get("hidden_columns", None):
            for code, colonne in self.columns.items():
                if colonne and self._meta.hidden_columns and code not in self._meta.hidden_columns:
                    colonne.visible = True

    def Create_boutons_actions(self, liste_boutons=[]):
        return format_html("&nbsp;".join(liste_boutons))

    def Create_bouton_imprimer(self, url=None, title="Imprimer"):
        return self.Create_bouton(url=url, title=title, icone="fa-file-pdf-o")

    def Create_bouton_modifier(self, url=None, title="Modifier"):
        return self.Create_bouton(url=url, title=title, icone="fa-pencil")

    def Create_bouton_supprimer(self, url=None, title="Supprimer"):
        return self.Create_bouton(url=url, title=title, icone="fa-times")

    def Create_bouton_dupliquer(self, url=None, title="Dupliquer"):
        return self.Create_bouton(url=url, title=title, icone="fa-copy")

    def Create_bouton(self, url=None, title="", icone="fa-copy", args=""):
        return """<a type='button' class='btn btn-default btn-xs' href='%s' title='%s' %s><i class="fa fa-fw %s"></i></a>""" % (url, title, args, icone)

    def Get_actions_standard(self, instance, *args, **kwargs):
        view = kwargs["view"]
        html = [
            self.Create_bouton_modifier(url=reverse(view.url_modifier, args=[instance.pk])),
            self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
        ]
        return self.Create_boutons_actions(html)

    def Formate_montant_standard(self, instance, **kwargs):
        return utils_texte.Formate_montant(kwargs.get("default_value", 0.0))
