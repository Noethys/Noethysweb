#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.db.models import Sum
from django.urls import reverse_lazy
from core.models import Prestation, Ventilation
from outils.views.procedures import BaseProcedure


class Procedure(BaseProcedure):
    def Executer(self, variables=None):
        prestations = {item["idprestation"]: item["total"] for item in Prestation.objects.values("idprestation").all().annotate(total=Sum("montant"))}
        ventilations = Ventilation.objects.values("famille", "famille__nom", "prestation_id", "reglement_id", "reglement__date").all().annotate(total=Sum("montant")).order_by("famille_id", "reglement_id")

        liste_anomalies = []
        for ventilation in ventilations:
            idprestation = ventilation["prestation_id"]
            if idprestation in prestations:
                if prestations[idprestation] < ventilation["total"]:
                    texte = f"""
                        <tr>
                            <td>{ventilation["famille__nom"]}</td>
                            <td>{ventilation["reglement_id"]}</td>
                            <td>{ventilation["reglement__date"].strftime('%d/%m/%Y')}</td>
                            <td>{prestations[idprestation]}</td>
                            <td>{ventilation["total"]}</td>
                            <td><a href="%s" target="_blank">Ouvrir le règlement</a></td>
                        </tr>
                    """ % reverse_lazy("famille_reglements_modifier", kwargs={"idfamille": ventilation["famille"], "pk": ventilation["reglement_id"]})
                    liste_anomalies.append(texte)

        if not liste_anomalies:
            return "Aucune erreur"

        headers = "<th>Famille</th><th>IDreglement</th><th>Date règlement</th><th>Montant prestation</th><th>Montant ventilé</th><th>Actions</th>"
        return "<table class='table table-bordered text-center table-valign-middle'><tr>%s</tr>%s</table>" % (headers, "".join(liste_anomalies))
