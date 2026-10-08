# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from core.utils import utils_formule_tarif


@require_POST
def Tester_formule(request):
    """ Teste une formule de tarif avec des valeurs saisies (même évaluateur que la facturation) """
    if not request.user.has_perm("core.activites_liste"):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de paramétrer les activités"}, status=403)

    try:
        formule = utils_formule_tarif.FormuleTarif(request.POST.get("formule", ""))
    except utils_formule_tarif.ErreurFormule as err:
        return JsonResponse({"valide": False, "erreur": str(err)})

    # Valeurs de test (uniquement les variables connues, converties en nombres)
    try:
        valeurs = json.loads(request.POST.get("valeurs", "{}"))
        if not isinstance(valeurs, dict):
            raise ValueError
    except ValueError:
        valeurs = {}
    variables = {code: valeurs.get(code) or 0 for code in utils_formule_tarif.VARIABLES}
    variables["QF_CONNU"] = 1 if valeurs.get("QF") not in (None, "") else 0
    if not variables["QF_CONNU"]:
        variables["QF"] = 999999
    questionnaires = valeurs.get("QUESTIONNAIRES") if isinstance(valeurs.get("QUESTIONNAIRES"), dict) else {}

    try:
        montant = formule.Evaluer(variables, fonction_questionnaire=lambda idquestion: questionnaires.get(str(idquestion)) or 0)
    except utils_formule_tarif.ErreurFormule as err:
        return JsonResponse({"valide": True, "erreur": str(err), "variables": sorted(formule.variables)})

    # Plancher et plafond, comme lors de la facturation
    montant_brut = montant
    for code, test in (("montant_min", lambda m, v: m < v), ("montant_max", lambda m, v: m > v)):
        try:
            limite = decimal.Decimal(str(request.POST.get(code) or 0).replace(",", "."))
        except decimal.InvalidOperation:
            limite = 0
        if limite and test(montant, limite):
            montant = limite
    if montant < 0:
        montant = decimal.Decimal(0)

    return JsonResponse({
        "valide": True,
        "montant": "%.2f" % montant,
        "montant_brut": "%.4f" % montant_brut if montant_brut != montant else None,
        "variables": sorted(formule.variables),
        "questions": sorted(formule.Get_questions()),
    })
