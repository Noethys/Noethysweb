#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.utils.html import format_html
from django.urls import reverse_lazy, reverse
from datatableview import Datatable, columns, helpers
from datatableview.views import DatatableView, MultipleDatatableView, XEditableDatatableView
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json



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

    def Create_bouton(self, url=None, title="", icone="fa-copy"):
        return """<a type='button' class='btn btn-default btn-xs' href='%s' title='%s'><i class="fa fa-fw %s"></i></a>""" % (url, title, icone)

    def Get_actions_standard(self, instance, *args, **kwargs):
        view = kwargs["view"]
        html = [
            self.Create_bouton_modifier(url=reverse(view.url_modifier, args=[instance.pk])),
            self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
        ]
        return self.Create_boutons_actions(html)
