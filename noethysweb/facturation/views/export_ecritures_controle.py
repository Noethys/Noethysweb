# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Contrôle des codes comptables et analytiques des prestations avant un export des écritures comptables.
Commun à tous les exports : Cloé, CWE, EBP, Quadra et Sage. """

import json
from django.http import JsonResponse
from django.template import Template, Context
from core.widgets import DateRangePickerWidget
from facturation.utils import utils_codes_prestations

# Codes repris dans le fichier de chaque export (CWE et Quadra n'exportent pas de code analytique)
EXPORTS = {
    "cloe": ("code_analytique", "code_compta"),
    "cwe": ("code_compta",),
    "ebp": ("code_analytique", "code_compta"),
    "quadra": ("code_compta",),
    "sage": ("code_analytique", "code_compta"),
}

LABELS_CHAMPS = {"code_analytique": "code analytique", "code_compta": "code comptable"}


def Get_parametres(request):
    """ Renvoie (champs, factures) ou une JsonResponse d'erreur """
    nom_export = request.POST.get("nom_export", "")
    if nom_export not in EXPORTS:
        return JsonResponse({"erreur": "Export inconnu"}, status=401)
    if not request.user.has_perm("core.export_ecritures_%s" % nom_export):
        return JsonResponse({"erreur": "Vous n'avez pas accès à cet export"}, status=401)
    # Le navigateur envoie la période telle qu'affichée ('01/10/2026 - 31/10/2026') : conversion par le widget, comme dans le formulaire de l'export
    periode = DateRangePickerWidget().value_from_datadict(request.POST, None, "periode")
    try:
        factures = utils_codes_prestations.Get_factures_periode(periode)
    except Exception:
        return JsonResponse({"erreur": "Veuillez sélectionner une période"}, status=401)
    return EXPORTS[nom_export], factures


def Verifier(request):
    """ Renvoie le tableau des prestations sans code (vide si tout est renseigné) """
    parametres = Get_parametres(request)
    if isinstance(parametres, JsonResponse):
        return parametres
    champs, factures = parametres
    anomalies = utils_codes_prestations.Get_anomalies(factures=factures, champs=champs)
    if not anomalies:
        return JsonResponse({"nbre": 0})
    nbre = sum(anomalie["nbre"] for anomalie in anomalies)
    context = {"anomalies": anomalies, "champs": champs, "nbre": nbre,
               "labels_manquants": " ou de ".join(LABELS_CHAMPS[champ] for champ in champs)}
    return JsonResponse({"nbre": nbre, "html": Template(HTML_ANOMALIES).render(Context(context))})


def Corriger(request):
    """ Enregistre les codes saisis dans l'alerte pour les prestations sans code """
    parametres = Get_parametres(request)
    if isinstance(parametres, JsonResponse):
        return parametres
    champs, factures = parametres
    try:
        corrections = json.loads(request.POST.get("corrections", "[]"))
        assert isinstance(corrections, list) and all(isinstance(correction, dict) for correction in corrections)
    except Exception:
        return JsonResponse({"erreur": "Données invalides"}, status=401)
    nbre = utils_codes_prestations.Corriger_anomalies(factures=factures, corrections=corrections, champs=champs)
    return JsonResponse({"succes": True, "nbre": nbre})


HTML_ANOMALIES = """
<p class="mb-2">{{ nbre }} prestation{{ nbre|pluralize }} des factures de la période {{ nbre|pluralize:"n'a,n'ont" }} pas de {{ labels_manquants }}.</p>
<p class="text-muted small">Vous pouvez saisir les codes manquants ci-dessous : ils seront enregistrés dans les prestations concernées (les codes déjà renseignés ne sont pas modifiés). Laissez une case vide pour ne rien changer.</p>
<style>
    /* En-tête figé lors du défilement. Les ombres remplacent les bordures haute et basse, qui disparaissent avec border-collapse */
    #table_anomalies_codes thead th {position: sticky; top: 0; z-index: 2; background-color: #fff; box-shadow: inset 0 1px 0 #dee2e6, inset 0 -1px 0 #dee2e6;}
</style>
<div style="max-height: 50vh; overflow-y: auto;">
<table class="table table-sm table-bordered mb-0" id="table_anomalies_codes">
    <thead><tr>
        <th>Label</th><th>Activité</th><th class="text-center">Nbre</th>
        {% if "code_analytique" in champs %}<th>Code analytique</th>{% endif %}
        {% if "code_compta" in champs %}<th>Code comptable</th>{% endif %}
    </tr></thead>
    <tbody>
    {% for anomalie in anomalies %}
        <tr data-label="{{ anomalie.label }}" data-idactivite="{{ anomalie.idactivite|default_if_none:'' }}">
            <td>{{ anomalie.label }}</td>
            <td>{{ anomalie.activite }}</td>
            <td class="text-center">{{ anomalie.nbre }}</td>
            {% if "code_analytique" in champs %}<td>{% if anomalie.sans_code_analytique %}<input type="text" class="form-control form-control-sm" data-champ="code_analytique" maxlength="200" aria-label="Code analytique de {{ anomalie.label }}" placeholder="Manquant ({{ anomalie.sans_code_analytique }})">{% else %}<span class="text-success"><i class="fa fa-check"></i> Renseigné</span>{% endif %}</td>{% endif %}
            {% if "code_compta" in champs %}<td>{% if anomalie.sans_code_compta %}<input type="text" class="form-control form-control-sm" data-champ="code_compta" maxlength="200" aria-label="Code comptable de {{ anomalie.label }}" placeholder="Manquant ({{ anomalie.sans_code_compta }})">{% else %}<span class="text-success"><i class="fa fa-check"></i> Renseigné</span>{% endif %}</td>{% endif %}
        </tr>
    {% endfor %}
    </tbody>
</table>
</div>
"""
