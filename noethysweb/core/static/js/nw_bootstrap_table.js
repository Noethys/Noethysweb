/*  Noethysweb - Listes bootstrap-table
    Présentation alignée sur les listes DataTables : recherche en pastille, bouton « Outils » (colonnes,
    plein écran, exports, impression) et pied de liste (nombre de lignes, lignes par page, pagination).
    Nécessite core/static/js/nw_menu.js.
*/

// Options communes à passer à bootstrapTable() (fusionnées avec les options propres à la page)
var NW_BT_OPTIONS = {
    searchAlign: "left",
    buttonsAlign: "left",
    showRefresh: false,
    showToggle: false,
    showFullscreen: false,
    showColumns: false,
    paginationPreText: "<i class='fa fa-chevron-left' aria-hidden='true'></i>",
    paginationNextText: "<i class='fa fa-chevron-right' aria-hidden='true'></i>",
    paginationSuccessivelySize: 3,
    paginationPagesBySide: 1,
    stickyHeader: true,
    formatSearch: function () {return "Rechercher…"},
    formatShowingRows: function (debut, fin, total, total_non_filtre) {
        var texte = "<b>" + debut + "–" + fin + "</b> sur <b>" + total + "</b>";
        if (total_non_filtre !== undefined && total_non_filtre > 0 && total_non_filtre > total) {
            texte += " (filtrés parmi " + total_non_filtre + ")";
        }
        return texte;
    },
    formatRecordsPerPage: function (choix) {return "Lignes par page " + choix},
    formatNoMatches: function () {return "Aucune donnée"},
};

var nw_bt_compteur = 0;

function nw_bt_creer(tag, classe, texte) {
    var element = document.createElement(tag);
    if (classe) {element.className = classe};
    if (texte) {element.textContent = texte};
    return element;
}

// Prépare la barre d'outils d'une liste bootstrap-table déjà initialisée
function nw_bt_preparer($table) {
    var conteneur = $table.closest(".bootstrap-table")[0];
    if (!conteneur || conteneur.classList.contains("nw-bt")) {return};
    conteneur.classList.add("nw-bt");

    var barre = conteneur.querySelector(".fixed-table-toolbar");
    if (!barre) {return};

    // Champ de recherche
    var recherche = barre.querySelector(".search input");
    if (recherche) {
        recherche.classList.add("nw-recherche");
        recherche.setAttribute("placeholder", "Rechercher…");
        recherche.setAttribute("aria-label", "Rechercher dans la liste");
        recherche.setAttribute("title", "Tapez un ou plusieurs mots pour filtrer la liste.");
        recherche.removeAttribute("style");
    }

    // Bouton « Outils »
    nw_bt_compteur += 1;
    var emplacement = nw_bt_creer("div", "nw-bt-outils");
    var bouton = nw_bt_creer("button", "btn nw-pastille nw-options");
    bouton.type = "button";
    bouton.id = "nw_bt_outils_" + nw_bt_compteur;
    bouton.setAttribute("aria-haspopup", "menu");
    bouton.setAttribute("aria-expanded", "false");
    bouton.setAttribute("title", "Outils de la liste : colonnes, exports, impression");
    var icone = nw_bt_creer("i", "fa fa-wrench");
    icone.setAttribute("aria-hidden", "true");
    bouton.appendChild(icone);
    bouton.appendChild(nw_bt_creer("span", "", "Outils"));
    var fleche = nw_bt_creer("i", "fa fa-angle-down nw-fleche");
    fleche.setAttribute("aria-hidden", "true");
    bouton.appendChild(fleche);
    emplacement.appendChild(bouton);
    barre.appendChild(emplacement);
    bouton.addEventListener("click", function () {
        nw_menu.ouvrir(bouton, function (m) {nw_bt_menu_outils(m, $table)});
    });
}

function nw_bt_options($table) {
    return $table.bootstrapTable("getOptions");
}

function nw_bt_est_arborescence($table) {
    return !!(nw_bt_options($table).treeShowField && typeof $table.treegrid === "function");
}

function nw_bt_plusieurs_pages($table) {
    var options = nw_bt_options($table);
    return options.pagination && options.totalPages > 1;
}

function nw_bt_menu_outils(m, $table) {
    m.entete("Affichage");
    m.item({label: "Choisir les colonnes…", icone: "fa-columns", sous_menu: true, garder_ouvert: true, action: function () {
        nw_bt_sous_menu(m, $table, nw_bt_menu_colonnes);
    }});
    if (nw_bt_est_arborescence($table)) {
        m.item({label: "Tout déplier", icone: "fa-plus-square-o", action: function () {$table.treegrid("expandAll")}});
        m.item({label: "Tout replier", icone: "fa-minus-square-o", action: function () {$table.treegrid("collapseAll")}});
    }
    var plein_ecran = document.body.classList.contains("nw-plein-ecran");
    m.item({label: plein_ecran ? "Quitter le plein écran" : "Plein écran", icone: plein_ecran ? "fa-compress" : "fa-expand", action: function () {
        nw_bt_basculer_plein_ecran($table);
    }});

    m.separateur();
    m.entete("Exporter");
    nw_bt_item_export(m, $table, "Excel", "fa-file-excel-o", "xlsx");
    nw_bt_item_export(m, $table, "PDF", "fa-file-pdf-o", "pdf");
    nw_bt_item_export(m, $table, "CSV", "fa-file-text-o", "csv");

    m.separateur();
    m.item({label: "Imprimer", icone: "fa-print", action: function () {
        var bouton = $table.closest(".bootstrap-table").find("button[name=print]");
        if (bouton.length) {bouton.trigger("click")};
    }});
}

// Export : si la liste a plusieurs pages, choix entre la page affichée et toute la liste
function nw_bt_item_export(m, $table, label, icone, type) {
    if (!nw_bt_plusieurs_pages($table)) {
        m.item({label: label, icone: icone, action: function () {nw_bt_exporter($table, type, false)}});
        return;
    }
    m.item({label: label, icone: icone, sous_menu: true, garder_ouvert: true, action: function () {
        nw_bt_sous_menu(m, $table, function (m, $table) {
            nw_bt_bouton_retour(m, $table);
            m.separateur();
            m.entete(label);
            m.item({label: "Page affichée", icone: "fa-file-o", action: function () {nw_bt_exporter($table, type, false)}});
            m.item({label: "Toute la liste", icone: "fa-files-o", action: function () {nw_bt_exporter($table, type, true)}});
        });
    }});
}

function nw_bt_exporter($table, type, toute_la_liste) {
    var pagination = nw_bt_options($table).pagination;
    if (toute_la_liste && pagination) {$table.bootstrapTable("togglePagination")};
    try {
        $table.bootstrapTable("exportTable", {type: type});
    } finally {
        if (toute_la_liste && pagination) {$table.bootstrapTable("togglePagination")};
    }
}

function nw_bt_sous_menu(m, $table, construire) {
    m.vider();
    construire(m, $table);
    m.repositionner();
    m.focus_premier();
}

function nw_bt_bouton_retour(m, $table) {
    m.item({label: "Retour", icone: "fa-arrow-left", garder_ouvert: true, action: function () {
        nw_bt_sous_menu(m, $table, nw_bt_menu_outils);
    }});
}

function nw_bt_menu_colonnes(m, $table) {
    nw_bt_bouton_retour(m, $table);
    m.separateur();
    m.entete("Colonnes affichées");
    m.zone_defilement();
    nw_bt_options($table).columns.forEach(function (ligne) {
        ligne.forEach(function (colonne) {
            if (colonne.checkbox || colonne.radio || colonne.field === undefined || colonne.switchable === false) {return};
            var div = document.createElement("div");
            div.innerHTML = colonne.title || "";
            var titre = div.textContent.replace(/\s+/g, " ").trim();
            if (!titre) {return};
            var element = m.item({label: titre, coche: colonne.visible !== false, garder_ouvert: true, action: function () {
                var visible = colonne.visible === false;
                $table.bootstrapTable(visible ? "showColumn" : "hideColumn", colonne.field);
                element.setAttribute("aria-checked", visible ? "true" : "false");
                element.querySelector("i").className = "fa fa-fw " + (visible ? "fa-check-square-o" : "fa-square-o");
            }});
        });
    });
}

// Plein écran : même fonctionnement que les listes DataTables (menu latéral et barre du haut masqués)
function nw_bt_basculer_plein_ecran($table) {
    var actif = document.body.classList.toggle("nw-plein-ecran");
    $table.bootstrapTable("resetView");
    if (actif) {
        var carte = $table.closest(".card")[0] || $table.closest(".bootstrap-table")[0];
        if (carte) {carte.scrollIntoView({block: "start"})};
    }
}

document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || !document.body.classList.contains("nw-plein-ecran") || document.querySelector(".nw-menu, .modal.show")) {return};
    var table = $(".nw-bt .fixed-table-body table").first();
    if (table.length) {nw_bt_basculer_plein_ecran(table)};
});
