//  Copyright (c) 2019-2021 Ivan LUCAS.
//  Noethysweb, application de gestion multi-activités.
//  Distribué sous licence GNU GPL.

// Frise de correspondance entre les semaines d'une période et les semaines du cycle des modèles de planning,
// avec choix de la semaine de départ. Utilisée par le planning général, le planning individuel et les pages "Appliquer un modèle".
//
// var frise = FriseModelesPlanning({conteneur: "#id", url: "...", csrf: "...", parametres: function() { return {modeles: [1, 2], dates: ["2026-11-16", ...]}; }});
// frise.maj(); frise.departs(); frise.reinitialiser();

(function() {
    var STYLE = "" +
        ".fmp {margin-top: 10px;}" +
        ".fmp-titre {font-weight: bold; font-size: 0.9rem; margin: 8px 0 4px;}" +
        ".fmp-modele {display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; padding: 4px 0;}" +
        ".fmp-badge {font-size: 0.75rem; background: #eeedfe; color: #3c3489; border-radius: 4px; padding: 1px 6px;}" +
        ".fmp-depart {display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 0.85rem;}" +
        ".fmp-depart .btn.active {background: #3c8dbc; color: #fff; border-color: #3c8dbc;}" +
        ".fmp-origine {color: #6c757d; font-size: 0.78rem;}" +
        ".fmp-defil {overflow-x: auto; margin-top: 4px;}" +
        ".fmp-table {border-collapse: separate; border-spacing: 3px; font-size: 0.75rem;}" +
        ".fmp-table th {font-weight: normal; color: #6c757d; text-align: center; white-space: nowrap; padding: 0 2px;}" +
        ".fmp-table th[scope=row] {text-align: right; color: #212529; padding-right: 6px; max-width: 160px; overflow: hidden; text-overflow: ellipsis;}" +
        ".fmp-table td {text-align: center; border-radius: 4px; padding: 3px 4px; min-width: 42px; white-space: nowrap;}" +
        ".fmp-s1 {background: #e1f5ee; color: #085041;} .fmp-s2 {background: #9fe1cb; color: #04342c;} .fmp-s3 {background: #5dcaa5; color: #04342c;}" +
        ".fmp-p1 {background: #eeedfe; color: #3c3489;} .fmp-p2 {background: #cecbf6; color: #26215c;}" +
        ".fmp-vac {background: repeating-linear-gradient(45deg, #faeeda, #faeeda 4px, #fac775 4px, #fac775 6px); color: #633806;}" +
        ".fmp-entete-vac {color: #854f0b !important;}" +
        ".fmp-alerte {background: #fff3cd; color: #856404; border-radius: 4px; padding: 4px 8px; margin-top: 6px; font-size: 0.8rem;}";

    function Injecter_style() {
        if (document.getElementById("fmp_style")) { return; }
        var style = document.createElement("style");
        style.id = "fmp_style";
        style.textContent = STYLE;
        document.head.appendChild(style);
    }

    function Echapper(texte) {
        return $("<div>").text(texte === null || texte === undefined ? "" : String(texte)).html();
    }

    function Date_courte(iso) {
        var morceaux = iso.split("-");
        return morceaux[2] + "/" + morceaux[1];
    }

    function Nom_court(modele, num) {
        if (modele.reperage === "PARITE" && modele.nb_semaines === 2) { return num === 1 ? "Impaire" : "Paire"; }
        return "S" + num;
    }

    window.FriseModelesPlanning = function(options) {
        Injecter_style();
        var $conteneur = $(options.conteneur);
        var departs = $.extend({}, options.departs || {});
        var minuteur = null, requete = null, numero = 0;

        function Afficher(data) {
            var cycliques = data.modeles.filter(function(modele) { return modele.nb_semaines > 1; });
            if (!cycliques.length && !data.alertes.length) { $conteneur.empty().prop("hidden", true); return; }
            var html = "<div class='fmp'>";

            if (cycliques.length) {
                html += "<div class='fmp-titre'>Correspondance des semaines</div>";

                // Choix de la semaine de départ
                cycliques.forEach(function(modele) {
                    html += "<div class='fmp-modele'><span>" + Echapper(modele.nom) + "</span><span class='fmp-badge'>" + Echapper(modele.libelle_cycle) + "</span>";
                    if (modele.depart_modifiable && data.semaines.length) {
                        var index = modele.valeurs.findIndex(function(valeur) { return valeur; });
                        var semaine_ref = data.semaines[index >= 0 ? index : 0];
                        var libelle = index > 0 ? "La première semaine hors vacances (du " + Date_courte(semaine_ref.lundi) + ") est la" : "La semaine du " + Date_courte(semaine_ref.lundi) + " est la";
                        html += "<span class='fmp-depart'><span id='fmp_lbl_" + modele.id + "'>" + libelle + "</span><span class='btn-group btn-group-sm' role='group' aria-labelledby='fmp_lbl_" + modele.id + "'>";
                        for (var num = 1; num <= modele.nb_semaines; num++) {
                            var actif = num === modele.depart;
                            html += "<button type='button' class='btn btn-default" + (actif ? " active" : "") + "' aria-pressed='" + actif + "' data-modele='" + modele.id + "' data-semaine='" + num + "'>"
                                + Echapper(modele.noms_semaines[num] || ("Semaine " + num)) + "</button>";
                        }
                        html += "</span>";
                        if (modele.origine_depart && modele.origine_depart !== "choisie") { html += "<span class='fmp-origine'>" + Echapper(modele.origine_depart) + "</span>"; }
                        html += "</span>";
                    }
                    html += "</div>";
                });

                // Frise
                html += "<div class='fmp-defil'><table class='fmp-table'><caption class='sr-only'>Semaine du cycle appliquée pour chaque semaine de la période</caption><thead><tr><td></td>";
                data.semaines.forEach(function(semaine) {
                    html += "<th scope='col' class='" + (semaine.vacances ? "fmp-entete-vac" : "") + "' title='Semaine du " + Date_courte(semaine.lundi) + "'>S" + semaine.num + "<br>" + Date_courte(semaine.lundi)
                        + (semaine.jours_vacances && !semaine.vacances ? " <i class='fa fa-sun-o' title='Semaine partiellement en vacances' aria-label='partiellement en vacances'></i>" : "") + "</th>";
                });
                html += "</tr></thead><tbody>";
                cycliques.forEach(function(modele) {
                    html += "<tr><th scope='row' title='" + Echapper(modele.nom) + "'>" + Echapper(modele.nom) + "</th>";
                    modele.valeurs.forEach(function(valeur, index) {
                        var vacances = data.semaines[index].vacances;
                        var classe = vacances ? "fmp-vac" : (modele.reperage === "PARITE" ? "fmp-p" : "fmp-s") + valeur;
                        var texte = valeur ? Nom_court(modele, valeur) + (vacances ? " · vac." : "") : "Vac.";
                        var titre = valeur ? (modele.noms_semaines[valeur] || "") + (vacances ? " (vacances)" : "") : "Vacances : seuls les évènements communs à toutes les semaines s'appliquent";
                        html += "<td class='" + classe + "' title='" + Echapper(titre) + "'>" + Echapper(texte) + "</td>";
                    });
                    html += "</tr>";
                });
                html += "</tbody></table></div>";
            }

            data.alertes.forEach(function(alerte) {
                html += "<div class='fmp-alerte' role='status'><i class='fa fa-exclamation-triangle margin-r-5'></i>" + Echapper(alerte) + "</div>";
            });
            html += "</div>";
            $conteneur.html(html).prop("hidden", false);
        }

        function Charger() {
            var parametres = options.parametres();
            if (!parametres || !parametres.modeles || !parametres.modeles.length || !parametres.dates || !parametres.dates.length) {
                $conteneur.empty().prop("hidden", true);
                return;
            }
            if (requete) { requete.abort(); }
            var mon_numero = ++numero;
            requete = $.ajax({url: options.url, type: "POST", dataType: "json", data: {
                csrfmiddlewaretoken: options.csrf, modeles: JSON.stringify(parametres.modeles),
                dates: JSON.stringify(parametres.dates), departs: JSON.stringify(departs)
            }}).done(function(data) {
                if (mon_numero === numero) { Afficher(data); }
            }).fail(function(xhr) {
                if (xhr.statusText === "abort") { return; }
                $conteneur.html("<div class='fmp-alerte'>" + Echapper((xhr.responseJSON && xhr.responseJSON.erreur) || "Impossible de calculer la correspondance des semaines") + "</div>").prop("hidden", false);
            });
        }

        $conteneur.on("click", ".fmp-depart button", function() {
            departs[$(this).data("modele")] = parseInt($(this).data("semaine"));
            Charger();
            if (options.change) { options.change(); }
        });

        return {
            maj: function() { clearTimeout(minuteur); minuteur = setTimeout(Charger, 250); },
            departs: function() { return $.extend({}, departs); },
            reinitialiser: function() { departs = {}; $conteneur.empty().prop("hidden", true); }
        };
    };
})();
