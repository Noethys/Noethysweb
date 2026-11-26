/*  Noethysweb - Listes DataTables
    Barre d'outils (recherche, filtres, bouton « Outils »), actions de ligne (bouton principal + menu),
    alignement automatique des colonnes et mémorisation silencieuse des préférences de liste.
*/

// Jeton CSRF : champ caché de la page s'il existe, sinon cookie csrftoken
function nw_get_csrf() {
    var champ = document.querySelector("[name=csrfmiddlewaretoken]");
    if (champ && champ.value) {return champ.value};
    var resultat = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return resultat ? decodeURIComponent(resultat[1]) : "";
}


/* ---------------------------------------------------------------------------------------------
   Menu flottant générique (bouton « Outils » et menus des actions de ligne).
   Le menu est attaché au body pour ne jamais être coupé par un conteneur à défilement.
   Les libellés sont toujours insérés via textContent (aucune injection HTML possible).
--------------------------------------------------------------------------------------------- */
var nw_menu = (function () {
    var menu = null;
    var bouton = null;
    var cible = null;   // Conteneur où sont ajoutés les éléments (le menu ou sa zone de défilement)

    function items() {
        return menu ? Array.prototype.slice.call(menu.querySelectorAll("[role^=menuitem]:not([disabled])")) : [];
    }

    function focus_item(index) {
        var liste = items();
        if (!liste.length) {return};
        if (index < 0) {index = liste.length - 1};
        if (index >= liste.length) {index = 0};
        liste[index].focus();
    }

    function positionner() {
        if (!menu || !bouton) {return};
        var rect = bouton.getBoundingClientRect();
        // Hauteur naturelle du menu, puis place disponible sous et au-dessus du bouton
        menu.style.maxHeight = "none";
        var largeur = menu.offsetWidth;
        var hauteur = menu.offsetHeight;
        var espace_bas = window.innerHeight - rect.bottom - 12;
        var espace_haut = rect.top - 12;
        var haut, hauteur_max;
        if (hauteur <= espace_bas || espace_bas >= espace_haut) {
            // Sous le bouton (avec barre de défilement si le menu est trop long)
            hauteur_max = Math.max(espace_bas, 160);
            haut = rect.bottom + 4;
        } else {
            // Au-dessus du bouton
            hauteur_max = espace_haut;
            haut = rect.top - 4 - Math.min(hauteur, hauteur_max);
        }
        if (haut + Math.min(hauteur, hauteur_max) > window.innerHeight - 8) {haut = Math.max(8, window.innerHeight - Math.min(hauteur, hauteur_max) - 8)};
        menu.style.maxHeight = hauteur_max + "px";
        // Bouton dans la moitié gauche de l'écran : menu aligné sur son bord gauche, sinon sur son bord droit
        var gauche = (rect.left < window.innerWidth / 2) ? rect.left : rect.right - largeur;
        if (gauche + largeur > window.innerWidth - 8) {gauche = window.innerWidth - largeur - 8};
        if (gauche < 8) {gauche = 8};
        menu.style.left = gauche + "px";
        menu.style.top = haut + "px";
    }

    function fermer(rendre_focus) {
        if (!menu) {return};
        menu.parentNode.removeChild(menu);
        menu = null;
        document.removeEventListener("mousedown", clic_exterieur, true);
        document.removeEventListener("keydown", clavier, true);
        window.removeEventListener("resize", fermer_sans_focus);
        window.removeEventListener("scroll", defilement, true);
        if (bouton) {
            bouton.setAttribute("aria-expanded", "false");
            bouton.classList.remove("nw-actif");
            if (rendre_focus) {bouton.focus()};
        }
        bouton = null;
    }

    function fermer_sans_focus() {fermer(false)}

    function defilement(event) {
        if (menu && menu.contains(event.target)) {return};
        fermer(false);
    }

    function clic_exterieur(event) {
        if (menu && !menu.contains(event.target) && !(bouton && bouton.contains(event.target))) {fermer(false)};
    }

    function clavier(event) {
        if (!menu) {return};
        var liste = items();
        var index = liste.indexOf(document.activeElement);
        if (event.key === "Escape") {event.preventDefault(); fermer(true)}
        else if (event.key === "ArrowDown") {event.preventDefault(); focus_item(index + 1)}
        else if (event.key === "ArrowUp") {event.preventDefault(); focus_item(index - 1)}
        else if (event.key === "Home") {event.preventDefault(); focus_item(0)}
        else if (event.key === "End") {event.preventDefault(); focus_item(liste.length - 1)}
        else if (event.key === "Tab") {fermer(false)};
    }

    function vider() {
        while (menu && menu.firstChild) {menu.removeChild(menu.firstChild)};
        menu.classList.remove("nw-menu-avec-defilement");
        cible = menu;
    }

    function ouvrir(btn, construire) {
        var meme_bouton = (bouton === btn);
        fermer(false);
        if (meme_bouton) {return};
        bouton = btn;
        menu = document.createElement("div");
        menu.className = "nw-menu";
        menu.setAttribute("role", "menu");
        cible = menu;
        if (btn.id) {menu.setAttribute("aria-labelledby", btn.id)};
        document.body.appendChild(menu);
        construire(api_menu);
        btn.setAttribute("aria-expanded", "true");
        btn.classList.add("nw-actif");
        positionner();
        focus_item(0);
        document.addEventListener("mousedown", clic_exterieur, true);
        document.addEventListener("keydown", clavier, true);
        window.addEventListener("resize", fermer_sans_focus);
        window.addEventListener("scroll", defilement, true);
    }

    function creer_icone(classe_icone) {
        var icone = document.createElement("i");
        icone.className = "fa fa-fw " + (classe_icone || "");
        icone.setAttribute("aria-hidden", "true");
        return icone;
    }

    var api_menu = {
        entete: function (texte) {
            var div = document.createElement("div");
            div.className = "nw-menu-entete";
            div.setAttribute("role", "presentation");
            div.textContent = texte;
            cible.appendChild(div);
        },
        separateur: function () {
            var div = document.createElement("div");
            div.className = "nw-menu-separateur";
            div.setAttribute("role", "separator");
            cible.appendChild(div);
        },
        item: function (options) {
            // options : label, icone, danger, disabled, href, target, action(event), garder_ouvert, coche (true/false/undefined),
            //           badge (texte court affiché en pastille), sous_menu (affiche un chevron)
            var element;
            if (options.href) {
                element = document.createElement("a");
                element.href = options.href;
                if (options.target) {element.target = options.target; element.rel = "noopener"};
            } else {
                element = document.createElement("button");
                element.type = "button";
            }
            element.className = "nw-menu-item" + (options.danger ? " nw-danger" : "");
            if (options.coche === true || options.coche === false) {
                element.setAttribute("role", "menuitemcheckbox");
                element.setAttribute("aria-checked", options.coche ? "true" : "false");
                element.appendChild(creer_icone(options.coche ? "fa-check-square-o" : "fa-square-o"));
            } else {
                element.setAttribute("role", "menuitem");
                element.appendChild(creer_icone(options.icone));
            }
            element.setAttribute("tabindex", "-1");
            var span = document.createElement("span");
            span.textContent = options.label;
            element.appendChild(span);
            if (options.badge) {
                var badge = document.createElement("span");
                badge.className = "nw-menu-badge";
                badge.textContent = options.badge;
                element.appendChild(badge);
            }
            if (options.sous_menu) {
                element.setAttribute("aria-haspopup", "true");
                var chevron = creer_icone("fa-angle-right");
                chevron.classList.add("nw-menu-chevron");
                element.appendChild(chevron);
            }
            if (options.disabled) {
                element.setAttribute("disabled", "disabled");
                element.setAttribute("aria-disabled", "true");
            }
            element.addEventListener("click", function (event) {
                if (options.disabled) {event.preventDefault(); return};
                if (options.action) {
                    if (!options.href) {event.preventDefault()};
                    if (!options.garder_ouvert) {fermer(false)};
                    options.action(event, element);
                } else {
                    fermer(false);
                }
            });
            cible.appendChild(element);
            return element;
        },
        note: function (texte) {
            var div = document.createElement("div");
            div.className = "nw-menu-note";
            div.setAttribute("role", "note");
            div.textContent = texte;
            menu.appendChild(div);
        },
        zone_defilement: function () {
            // Les éléments suivants défilent seuls ; ceux déjà ajoutés (Retour, titre) restent visibles
            var zone = document.createElement("div");
            zone.className = "nw-menu-defilement";
            zone.setAttribute("role", "group");
            menu.appendChild(zone);
            menu.classList.add("nw-menu-avec-defilement");
            cible = zone;
        },
        vider: vider,
        repositionner: positionner,
        focus_premier: function () {focus_item(0)},
        fermer: fermer,
    };

    return {ouvrir: ouvrir, fermer: fermer};
})();


/* ---------------------------------------------------------------------------------------------
   Actions de ligne : la première action non destructive devient le bouton principal (icône +
   libellé court), les autres sont regroupées dans un menu. Les boutons d'origine restent dans
   la cellule (masqués) et sont déclenchés tels quels : liens, onclick, modales et gestionnaires
   existants sont conservés.
--------------------------------------------------------------------------------------------- */
var NW_ICONES_DESTRUCTIVES = ["fa-times", "fa-trash", "fa-trash-o", "fa-remove", "fa-close"];

function nw_est_destructif(element) {
    var titre = (element.getAttribute("title") || "").toLowerCase();
    if (titre.indexOf("supprimer") === 0) {return true};
    var icone = element.querySelector("i");
    if (!icone) {return false};
    for (var i = 0; i < NW_ICONES_DESTRUCTIVES.length; i++) {
        if (icone.classList.contains(NW_ICONES_DESTRUCTIVES[i])) {return true};
    }
    return false;
}

function nw_label_action(element) {
    var titre = (element.getAttribute("title") || element.getAttribute("aria-label") || element.textContent || "").replace(/\s+/g, " ").trim();
    return titre || "Action";
}

function nw_label_court(titre) {
    if (titre.length <= 14) {return titre};
    return titre.split(" ")[0];
}

function nw_lien_simple(element) {
    // Lien navigable sans script : reproduit en vrai lien dans le menu (clic molette, ctrl+clic...)
    if (element.tagName !== "A" || element.hasAttribute("onclick") || element.hasAttribute("data-toggle") || element.hasAttribute("download")) {return null};
    var href = element.getAttribute("href");
    if (!href || href.charAt(0) === "#") {return null};
    try {
        var url = new URL(href, window.location.href);
        if (url.protocol !== "http:" && url.protocol !== "https:") {return null};
        return url.href;
    } catch (e) {
        return null;
    }
}

function nw_est_desactive(element) {
    return element.classList.contains("disabled") || element.hasAttribute("disabled");
}

function nw_transformer_actions(cellule) {
    if (cellule.getAttribute("data-nw-actions")) {return};
    var boutons = [];
    var noeuds = Array.prototype.slice.call(cellule.childNodes);
    for (var i = 0; i < noeuds.length; i++) {
        var noeud = noeuds[i];
        if (noeud.nodeType === 3) {
            // Texte : seulement des espaces autorisés, sinon la cellule n'est pas une simple liste de boutons
            if (noeud.textContent.replace(/ /g, " ").trim()) {return};
        } else if (noeud.nodeType === 1) {
            if ((noeud.tagName === "A" || noeud.tagName === "BUTTON") && (noeud.classList.contains("btn") || noeud.classList.contains("btn-xs"))) {
                boutons.push(noeud);
            } else {
                return;
            }
        }
    }
    if (!boutons.length) {return};
    cellule.setAttribute("data-nw-actions", "1");

    // Bouton principal : la première action non destructive
    var principal = boutons[0];
    for (var j = 0; j < boutons.length; j++) {
        if (!nw_est_destructif(boutons[j])) {principal = boutons[j]; break};
    }
    var autres = boutons.filter(function (b) {return b !== principal});
    autres.sort(function (a, b) {return (nw_est_destructif(a) ? 1 : 0) - (nw_est_destructif(b) ? 1 : 0)});

    // Nettoyage des espaces de séparation
    for (var k = noeuds.length - 1; k >= 0; k--) {
        if (noeuds[k].nodeType === 3 || noeuds[k].nodeType === 8) {cellule.removeChild(noeuds[k])};
    }

    var groupe = document.createElement("div");
    groupe.className = "nw-actions" + (autres.length ? " nw-actions-menu" : "");
    groupe.setAttribute("role", "group");
    cellule.appendChild(groupe);

    // Bouton principal = l'élément d'origine, enrichi d'un libellé court
    var titre_principal = nw_label_action(principal);
    principal.classList.add("nw-action-principale");
    if (nw_est_destructif(principal)) {principal.classList.add("nw-danger")};
    if (!principal.getAttribute("aria-label")) {principal.setAttribute("aria-label", titre_principal)};
    if (!principal.textContent.trim()) {
        var libelle = document.createElement("span");
        libelle.className = "nw-action-libelle";
        libelle.setAttribute("aria-hidden", "true");
        libelle.textContent = nw_label_court(titre_principal);
        principal.appendChild(libelle);
    }
    groupe.appendChild(principal);

    // La ligne devient cliquable si l'action principale n'est ni destructive ni désactivée
    var ligne = cellule.parentNode;
    if (ligne && ligne.tagName === "TR" && !nw_est_destructif(principal) && !nw_est_desactive(principal)) {
        ligne.classList.add("nw-ligne-cliquable");
    }

    if (!autres.length) {return};

    // Boutons secondaires conservés mais masqués
    var conteneur = document.createElement("span");
    conteneur.className = "nw-actions-origine";
    conteneur.hidden = true;
    autres.forEach(function (b) {conteneur.appendChild(b)});
    cellule.appendChild(conteneur);

    var bouton_menu = document.createElement("button");
    bouton_menu.type = "button";
    bouton_menu.className = "btn nw-action-menu";
    bouton_menu.setAttribute("aria-haspopup", "menu");
    bouton_menu.setAttribute("aria-expanded", "false");
    bouton_menu.setAttribute("aria-label", "Autres actions");
    bouton_menu.setAttribute("title", "Autres actions");
    var icone = document.createElement("i");
    icone.className = "fa fa-caret-down";
    icone.setAttribute("aria-hidden", "true");
    bouton_menu.appendChild(icone);
    groupe.appendChild(bouton_menu);

    bouton_menu.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        nw_menu.ouvrir(bouton_menu, function (m) {
            var separateur_fait = false;
            autres.forEach(function (origine, index) {
                var destructif = nw_est_destructif(origine);
                if (destructif && !separateur_fait && index > 0) {m.separateur(); separateur_fait = true};
                var icone_origine = origine.querySelector("i");
                var classes_icone = icone_origine ? Array.prototype.filter.call(icone_origine.classList, function (c) {return /^fa-[a-z0-9-]+$/.test(c) && c !== "fa-fw"}).join(" ") : "";
                var href = nw_lien_simple(origine);
                m.item({
                    label: nw_label_action(origine),
                    icone: classes_icone,
                    danger: destructif,
                    disabled: nw_est_desactive(origine),
                    href: href,
                    target: href ? origine.getAttribute("target") : null,
                    action: href ? null : function () {origine.click()},
                });
            });
        });
    });
}


/* ---------------------------------------------------------------------------------------------
   Clic sur une ligne : déclenche l'action principale de la ligne (bouton d'origine, avec ses
   liens, onclick ou modales). Ignoré sur les éléments interactifs, les cases de sélection,
   la poignée de déplacement, après un glisser ou une sélection de texte.
--------------------------------------------------------------------------------------------- */
function nw_activer_clic_lignes(api) {
    var corps = api.table().body();
    if (!corps || corps.getAttribute("data-nw-clic")) {return};
    corps.setAttribute("data-nw-clic", "1");
    var depart = null;

    corps.addEventListener("mousedown", function (event) {
        depart = {x: event.clientX, y: event.clientY};
    });

    corps.addEventListener("click", function (event) {
        if (event.button !== 0) {return};
        var ligne = event.target.closest("tr.nw-ligne-cliquable");
        if (!ligne || !corps.contains(ligne)) {return};
        if (event.target.closest("a, button, input, select, textarea, label, [onclick], [role=button], td.select-checkbox, td.reorder")) {return};
        if (depart && (Math.abs(event.clientX - depart.x) > 5 || Math.abs(event.clientY - depart.y) > 5)) {return};
        if (window.getSelection && window.getSelection().toString()) {return};
        var principal = ligne.querySelector(".nw-action-principale");
        if (!principal || nw_est_destructif(principal) || nw_est_desactive(principal)) {return};
        // Ctrl/Cmd + clic : ouverture dans un nouvel onglet quand l'action est un simple lien
        var href = nw_lien_simple(principal);
        if (href && (event.ctrlKey || event.metaKey)) {
            window.open(href, "_blank", "noopener");
            return;
        }
        principal.click();
    });
}


/* ---------------------------------------------------------------------------------------------
   Liste vide : message adapté à la liste, et boutons pour effacer la recherche ou retirer
   les filtres quand ce sont eux qui vident la liste. Textes insérés via textContent.
--------------------------------------------------------------------------------------------- */
function nw_nom_elements(api) {
    // « Liste des familles » -> « familles » (titre du cadre qui contient la liste)
    var conteneur = api.table().container();
    var cadre = conteneur ? conteneur.closest(".card") : null;
    var titre = cadre ? cadre.querySelector(".card-title") : null;
    var texte = titre ? titre.textContent.replace(/\s+/g, " ").trim() : "";
    var resultat = texte.match(/^liste\s+(?:des|de la|du|de|d')\s*(.+)$/i);
    if (resultat) {return resultat[1].trim()};
    // Fiches famille, individu, collaborateur, activité... : le titre du cadre est directement le nom des éléments (ex : « Pièces »)
    if (!texte || texte.length > 40 || /[:.!?]/.test(texte)) {return ""};
    if (texte.length > 1 && texte.charAt(1) === texte.charAt(1).toLowerCase()) {
        texte = texte.charAt(0).toLowerCase() + texte.slice(1);
    }
    return texte;
}

function nw_pas_encore_de(nom) {
    if (!nom) {return "Aucun élément pour le moment"};
    var initiale = nom.charAt(0).toLowerCase();
    var elision = "aeiouyhéèêàâîôûœ".indexOf(initiale) > -1;
    return "Pas encore " + (elision ? "d'" : "de ") + nom;
}

function nw_creer(tag, classe, texte) {
    var element = document.createElement(tag);
    if (classe) {element.className = classe};
    if (texte) {element.textContent = texte};
    return element;
}

function nw_bouton_vide(icone, texte, action) {
    var bouton = nw_creer("button", "btn nw-vide-bouton");
    bouton.type = "button";
    var i = nw_creer("i", "fa " + icone);
    i.setAttribute("aria-hidden", "true");
    bouton.appendChild(i);
    bouton.appendChild(nw_creer("span", "", texte));
    bouton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        action(bouton);
    });
    return bouton;
}

function nw_retirer_filtres(bouton) {
    var formulaires = document.querySelectorAll("#nw_filtres_liste .nw-chip form");
    bouton.disabled = true;
    var requetes = Array.prototype.map.call(formulaires, function (formulaire) {
        return fetch(formulaire.action, {
            method: "POST",
            credentials: "same-origin",
            headers: {"X-CSRFToken": nw_get_csrf()},
            redirect: "manual",
        });
    });
    Promise.all(requetes).then(function () {window.location.reload()}, function () {window.location.reload()});
}

function nw_afficher_liste_vide(api) {
    var cellule = api.table().body().querySelector("td.dataTables_empty");
    if (!cellule || cellule.getAttribute("data-nw-vide")) {return};
    cellule.setAttribute("data-nw-vide", "1");

    var conteneur = api.table().container();
    var recherche = api.search();
    var nb_filtres = conteneur ? conteneur.querySelectorAll("#nw_filtres_liste .nw-chip").length : 0;

    var bloc = nw_creer("div", "nw-liste-vide");
    bloc.setAttribute("role", "status");
    var rond = nw_creer("span", "nw-vide-icone");
    var icone = nw_creer("i", "fa " + ((recherche || nb_filtres) ? "fa-search" : "fa-inbox"));
    icone.setAttribute("aria-hidden", "true");
    rond.appendChild(icone);
    bloc.appendChild(rond);

    var titre, texte;
    if (recherche) {
        titre = "Aucun résultat pour « " + recherche + " »";
        texte = "Vérifiez l'orthographe ou essayez avec moins de mots.";
        if (nb_filtres === 1) {texte += " Un filtre de liste est actif et limite aussi les résultats."};
        if (nb_filtres > 1) {texte += " " + nb_filtres + " filtres de liste sont actifs et limitent aussi les résultats."};
    } else if (nb_filtres) {
        titre = "Aucun résultat avec " + (nb_filtres > 1 ? "les filtres actifs" : "le filtre actif");
        texte = "Modifiez ou retirez " + (nb_filtres > 1 ? "les filtres" : "le filtre") + " pour afficher plus de résultats.";
    } else {
        titre = nw_pas_encore_de(nw_nom_elements(api));
        texte = "Cette liste est vide pour le moment.";
    }
    bloc.appendChild(nw_creer("h3", "", titre));
    bloc.appendChild(nw_creer("p", "", texte));

    if (recherche || nb_filtres) {
        var actions = nw_creer("div", "nw-vide-actions");
        if (recherche) {
            actions.appendChild(nw_bouton_vide("fa-times", "Effacer la recherche", function () {
                var champ = conteneur.querySelector(".dataTables_filter input");
                if (champ) {champ.value = ""};
                api.search("").draw();
            }));
        }
        if (nb_filtres) {
            actions.appendChild(nw_bouton_vide("fa-filter", nb_filtres > 1 ? "Retirer les filtres" : "Retirer le filtre", nw_retirer_filtres));
        }
        bloc.appendChild(actions);
    }

    while (cellule.firstChild) {cellule.removeChild(cellule.firstChild)};
    cellule.appendChild(bloc);
}


/* ---------------------------------------------------------------------------------------------
   Tableau plus large que son cadre : défilement horizontal dans le cadre. L'en-tête flottant
   (FixedHeader) ne sait pas suivre ce défilement : il est désactivé tant que le tableau déborde.
--------------------------------------------------------------------------------------------- */
function nw_verifier_debordement(api) {
    var table = api.table().node();
    var cadre = table ? table.closest(".nw-dt > .row > .col-sm-12") : null;
    if (!cadre) {return};
    var deborde = cadre.scrollWidth > cadre.clientWidth + 1;
    cadre.classList.toggle("nw-deborde", deborde);
    if (api.fixedHeader) {
        try {
            if (deborde) {api.fixedHeader.disable()} else {api.fixedHeader.enable()};
        } catch (e) {}
    }
}

var nw_minuteur_redimension = null;
window.addEventListener("resize", function () {
    if (nw_minuteur_redimension) {window.clearTimeout(nw_minuteur_redimension)};
    nw_minuteur_redimension = window.setTimeout(function () {
        $(".nw-dt table.dataTable").each(function () {
            if ($.fn.dataTable.isDataTable(this)) {nw_verifier_debordement($(this).DataTable())};
        });
    }, 200);
});


function nw_ouvrir_premiere_ligne(api) {
    var ligne = api.table().body().querySelector("tr:not(.dtrg-group)");
    if (!ligne || !ligne.classList.contains("nw-ligne-cliquable")) {return};
    var principal = ligne.querySelector(".nw-action-principale");
    if (!principal || nw_est_destructif(principal) || nw_est_desactive(principal)) {return};
    principal.click();
}


/* ---------------------------------------------------------------------------------------------
   Impression et export de toutes les lignes
--------------------------------------------------------------------------------------------- */

// Pagination côté serveur : charge provisoirement toutes les lignes, exécute « faire », puis revient à la page affichée
function nw_avec_toutes_les_lignes(dt, faire) {
    if (!dt.page.info().serverSide) {
        faire();
        return;
    }
    var settings = dt.settings()[0];
    var ancien_debut = settings._iDisplayStart;
    var ancienne_longueur = settings._iDisplayLength;
    dt.one("preXhr", function (e, s, data) {
        data.start = 0;
        data.length = -1;
    });
    dt.one("draw", function () {
        try {
            faire();
        } finally {
            dt.one("preXhr", function (e, s, data) {
                settings._iDisplayStart = ancien_debut;
                settings._iDisplayLength = ancienne_longueur;
                data.start = ancien_debut;
                data.length = ancienne_longueur;
            });
            setTimeout(function () {dt.draw(false)}, 0);
        }
    });
    dt.draw(false);
}

function nw_mise_en_page_impression(win) {
    $(win.document.body).css("font-size", "7pt");
    $(win.document.body).find("table")
        .css("font-size", "inherit")
        .css("border-collapse", "collapse")
        .css("border", "1px solid black");
    $(win.document.body).find("td").css("border", "1px solid black");
    $(win.document.body).find("h1").css("text-align", "center").css("font-size", "9pt");
}

// Bouton d'impression. « toutes_les_lignes » : en pagination côté serveur, toutes les lignes sont d'abord chargées.
// La fenêtre d'impression est ouverte immédiatement (au clic) pour ne pas être bloquée par le navigateur.
function nw_bouton_impression(nom, modifier, toutes_les_lignes) {
    return {
        extend: "print",
        name: nom,
        title: impression_titre,
        messageTop: impression_introduction,
        messageBottom: impression_conclusion,
        autoPrint: true,
        exportOptions: {columns: ":visible", modifier: modifier},
        customize: nw_mise_en_page_impression,
        action: function (e, dt, button, config) {
            var self = this;
            var imprimer = $.fn.dataTable.ext.buttons.print.action;
            if (!toutes_les_lignes || !dt.page.info().serverSide) {
                imprimer.call(self, e, dt, button, config);
                return;
            }
            var fenetre = window.open("", "");
            if (!fenetre) {
                toastr.error("La fenêtre d'impression a été bloquée par le navigateur.");
                return;
            }
            fenetre.document.write("<p style='font-family:sans-serif'>Préparation de l'impression…</p>");
            nw_avec_toutes_les_lignes(dt, function () {
                var ouvrir = window.open;
                window.open = function () {return fenetre};
                try {
                    fenetre.document.open();
                    imprimer.call(self, e, dt, button, config);
                } finally {
                    window.open = ouvrir;
                }
            });
        }
    };
}


/* ---------------------------------------------------------------------------------------------
   Déplacement des colonnes par glisser-déposer des titres (extension ColReorder).
   La case à cocher (à gauche) et la colonne Actions (à droite) restent fixes.
   L'ordre est mémorisé par utilisateur sous forme de codes de colonnes.
--------------------------------------------------------------------------------------------- */
function nw_codes_colonnes(api) {
    return api.columns().header().toArray().map(function (entete) {
        return entete.getAttribute("data-code") || entete.getAttribute("data-name") || "";
    });
}

function nw_activer_deplacement_colonnes(api) {
    if (!$.fn.dataTable.ColReorder || api.settings()[0]._colReorder) {return};
    var table = api.table().node();
    var entetes = api.columns().header().toArray();
    if (entetes.length < 3) {return};
    var fixe_gauche = (entetes[0].classList.contains("select-checkbox") || entetes[0].querySelector("input[type=checkbox]")) ? 1 : 0;
    var fixe_droite = entetes[entetes.length - 1].classList.contains("nw-col-actions") ? 1 : 0;
    if (entetes.length - fixe_gauche - fixe_droite < 2) {return};

    // Ordre mémorisé : appliqué seulement s'il contient exactement les colonnes actuelles
    var options = {fixedColumnsLeft: fixe_gauche, fixedColumnsRight: fixe_droite, realtime: false};
    var memorise = table.getAttribute("data-nw-ordre-colonnes");
    if (memorise) {
        try {
            var codes_memorises = JSON.parse(memorise);
            var codes_actuels = nw_codes_colonnes(api);
            var ordre = codes_memorises.map(function (code) {return codes_actuels.indexOf(code)});
            var valide = codes_memorises.length === codes_actuels.length && ordre.indexOf(-1) === -1 && new Set(ordre).size === ordre.length;
            if (valide) {options.order = ordre};
        } catch (e) {}
    }
    new $.fn.dataTable.ColReorder(api, options);
    nw_marquer_entetes_deplacables(api, fixe_gauche, fixe_droite);

    // Pagination côté serveur : les lignes déjà chargées ne sont pas réordonnées par ColReorder
    // (données sous forme d'objets), elles sont donc rechargées après chaque déplacement
    var cote_serveur = api.page.info().serverSide;
    if (cote_serveur && options.order) {api.draw(false)};
    // Le relâchement de la souris après un glisser ne doit pas trier la colonne
    var fin_glisser = 0;
    api.on("column-reorder.dt", function (e, settings, details) {
        if (details && details.drop === false) {return};
        fin_glisser = Date.now();
        nw_marquer_entetes_deplacables(api, fixe_gauche, fixe_droite);
        if (cote_serveur) {api.draw(false)};
    });
    var entete = api.table().header();
    if (entete) {
        entete.addEventListener("click", function (event) {
            if (Date.now() - fin_glisser < 400) {
                event.stopImmediatePropagation();
                event.preventDefault();
            }
        }, true);
    }

    // Mémorisation de l'ordre choisi
    if (table.classList.contains("datatable") && typeof url_ordre_colonnes !== "undefined") {
        api.on("column-reorder.dt", function (e, settings, details) {
            if (details && details.drop === false) {return};
            nw_memoriser("ordre_colonnes", url_ordre_colonnes, {view: nom_view, colonnes: JSON.stringify(nw_codes_colonnes(api))});
            nw_aligner_colonnes(api);
            nw_verifier_debordement(api);
        });
    }
}

// Curseur « main » et infobulle sur les titres déplaçables (triables ou non)
function nw_marquer_entetes_deplacables(api, fixe_gauche, fixe_droite) {
    var entetes = api.columns().header().toArray();
    entetes.forEach(function (entete, index) {
        var deplacable = index >= fixe_gauche && index < entetes.length - fixe_droite;
        entete.classList.toggle("nw-deplacable", deplacable);
        if (!deplacable) {return};
        if (!entete.hasAttribute("title") || entete.getAttribute("data-nw-aide-colonne")) {
            var triable = api.settings()[0].aoColumns[index].bSortable !== false;
            entete.setAttribute("title", triable ? "Cliquez pour trier, faites glisser pour déplacer la colonne" : "Faites glisser pour déplacer la colonne");
            entete.setAttribute("data-nw-aide-colonne", "1");
        }
    });
}

// Pagination côté serveur : le serveur (django-datatable-view) ne connaît que l'ordre d'origine des colonnes.
// La requête est remise dans cet ordre, et les lignes reçues sont remises dans l'ordre affiché.
function nw_reponse_ordre_affiche(api, json) {
    if (!api.settings()[0]._colReorder || !json || !Array.isArray(json.data)) {return};
    var nb = api.columns().count();
    var ordre = api.colReorder.order();
    var identique = ordre.every(function (origine, index) {return origine === index});
    if (identique) {return};
    json.data = json.data.map(function (ligne) {
        if (Array.isArray(ligne) || !ligne) {return ligne};
        var nouvelle = $.extend({}, ligne);
        for (var index = 0; index < nb; index++) {
            nouvelle[index] = ligne[ordre[index]];
        }
        return nouvelle;
    });
}

function nw_requete_ordre_origine(api, data) {
    if (!api.settings()[0]._colReorder || !data || !data.columns) {return};
    var transposer = function (index) {return api.colReorder.transpose(index, "toOriginal")};
    var colonnes = [];
    data.columns.forEach(function (colonne, index) {colonnes[transposer(index)] = colonne});
    data.columns = colonnes;
    if (data.order) {
        data.order.forEach(function (tri) {tri.column = transposer(tri.column)});
    }
}


/* ---------------------------------------------------------------------------------------------
   Alignement automatique : texte à gauche, montants à droite, colonnes courtes (icônes, coches,
   petits nombres) centrées, actions à droite.
--------------------------------------------------------------------------------------------- */
var NW_REGEX_MONTANT = /^[-+]?\d{1,3}(?:[   ]?\d{3})*(?:[.,]\d+)?\s*(?:€|%)?$|^[-+]?\d+[.,]\d+\s*(?:€|%)?$/;

function nw_aligner_colonnes(api) {
    var classes = {gauche: "nw-al-gauche", centre: "nw-al-centre", droite: "nw-al-droite"};
    api.columns(":visible").every(function (index) {
        var entete = this.header();
        if (!entete) {return};
        var cellules = api.column(index, {page: "current"}).nodes().toArray();
        var nom = entete.getAttribute("data-name") || "";
        var alignement = "gauche";
        if (entete.classList.contains("select-checkbox") || ["id", "ordre", "defaut", "checkbox"].indexOf(nom) > -1 || entete.querySelector("input[type=checkbox]")) {
            alignement = "centre";
        } else if (entete.classList.contains("nw-col-actions")) {
            alignement = "droite";
        } else {
            var nb = 0, nb_court = 0, nb_montant = 0, nb_decimal = 0;
            cellules.forEach(function (cellule) {
                if (!cellule) {return};
                var texte = (cellule.textContent || "").replace(/\s+/g, " ").trim();
                if (!texte) {
                    if (cellule.querySelector("i, img, input, svg, .badge")) {nb++; nb_court++};
                    return;
                }
                nb++;
                if (texte.length <= 3) {nb_court++};
                if (NW_REGEX_MONTANT.test(texte)) {
                    nb_montant++;
                    if (/[.,]\d/.test(texte) || /€/.test(texte)) {nb_decimal++};
                }
            });
            if (nb > 0 && nb_court === nb) {alignement = "centre"}
            else if (nb > 0 && nb_montant === nb && nb_decimal > 0) {alignement = "droite"};
        }
        cellules.push(entete);
        if (this.footer()) {cellules.push(this.footer())};
        cellules.forEach(function (cellule) {
            if (!cellule) {return};
            cellule.classList.remove("nw-al-gauche", "nw-al-centre", "nw-al-droite");
            cellule.classList.add(classes[alignement]);
        });
    });
}


/* ---------------------------------------------------------------------------------------------
   Barre d'outils de la liste
--------------------------------------------------------------------------------------------- */
var nw_compteur_menus = 0;

// Infobulles d'aide
var NW_AIDE_RECHERCHE = "Tapez un ou plusieurs mots pour filtrer la liste.\nEntrée : ouvre la première ligne trouvée.";
var NW_AIDE_COCHE = "Clic : coche ou décoche la ligne.\nMaj + clic : coche toutes les lignes entre la dernière ligne cliquée et celle-ci.";
var NW_AIDE_COCHE_TOUT = "Coche ou décoche toutes les lignes.\nDans la liste, Maj + clic coche toute une plage de lignes.";

function nw_infobulles_coches(api) {
    $(api.table().body()).find("td.select-checkbox").attr("title", NW_AIDE_COCHE);
    var entete = api.table().header();
    if (entete) {$(entete).find("#checkbox_all, input[data-id=all]").attr("title", NW_AIDE_COCHE_TOUT)};
}

function nw_marquer_colonne_actions(api) {
    api.columns().every(function () {
        var entete = this.header();
        if (!entete) {return};
        var nom = entete.getAttribute("data-name") || "";
        if (nom === "actions" || (!nom && entete.textContent.trim().toLowerCase() === "actions")) {
            entete.classList.add("nw-col-actions");
            $(this.nodes()).addClass("nw-col-actions");
        }
    });
}

function nw_preparer_liste(api) {
    var conteneur = api.table().container();
    if (!conteneur || conteneur.getAttribute("data-nw-prepare")) {return};
    conteneur.setAttribute("data-nw-prepare", "1");
    conteneur.classList.add("nw-dt");

    nw_marquer_colonne_actions(api);
    nw_activer_clic_lignes(api);
    api.on("preXhr.dt", function (e, settings, data) {nw_requete_ordre_origine(api, data)});
    api.on("xhr.dt", function (e, settings, json) {nw_reponse_ordre_affiche(api, json)});
    if (api.settings()[0]._bInitComplete) {
        nw_activer_deplacement_colonnes(api);
    } else {
        api.one("init.dt", function () {nw_activer_deplacement_colonnes(api)});
    }

    // Maj + clic sur une case de sélection : empêche la sélection du texte de la page
    var corps_table = api.table().body();
    if (corps_table) {
        corps_table.addEventListener("mousedown", function (event) {
            if (event.shiftKey && event.target.closest("td.select-checkbox")) {event.preventDefault()};
        });
    }
    api.on("column-visibility.dt init.dt", function () {
        window.setTimeout(function () {nw_verifier_debordement(api)}, 0);
    });

    // Pied de liste collé en bas de l'écran : ombre pour le détacher des lignes qui passent dessous
    var pied = conteneur.querySelector(".nw-dt-pied");
    if (pied && window.IntersectionObserver) {
        var repere = document.createElement("div");
        repere.className = "nw-pied-repere";
        repere.setAttribute("aria-hidden", "true");
        pied.parentNode.insertBefore(repere, pied.nextSibling);
        new IntersectionObserver(function (entrees) {
            pied.classList.toggle("nw-pied-colle", !entrees[0].isIntersecting);
        }).observe(repere);
    }

    // Recherche
    var recherche = conteneur.querySelector(".dataTables_filter input");
    if (recherche) {
        recherche.setAttribute("placeholder", "Rechercher…");
        recherche.setAttribute("aria-label", "Rechercher dans la liste");
        recherche.setAttribute("title", NW_AIDE_RECHERCHE);
        recherche.classList.add("nw-recherche");

        // Entrée dans la recherche : ouvre la première ligne trouvée (comme un clic sur cette ligne).
        // On attend que les lignes affichées correspondent bien au texte saisi (recherche en cours ou différée).
        var etat = {affichee: api.search(), en_cours: false, minuteur: null};
        api.on("preXhr.dt", function () {etat.en_cours = true});
        api.on("xhr.dt", function () {etat.en_cours = false});
        api.on("draw.dt", function () {etat.affichee = api.search()});
        recherche.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" || event.isComposing) {return};
            event.preventDefault();
            var valeur = recherche.value;
            if (!valeur.trim()) {return};
            api.off("draw.nwentree");
            if (etat.minuteur) {window.clearTimeout(etat.minuteur)};
            if (etat.affichee === valeur && !etat.en_cours) {
                nw_ouvrir_premiere_ligne(api);
                return;
            }
            api.on("draw.nwentree", function () {
                if (etat.affichee === valeur && !etat.en_cours) {
                    api.off("draw.nwentree");
                    nw_ouvrir_premiere_ligne(api);
                }
            });
            // Abandon si aucun résultat n'arrive (erreur réseau...)
            etat.minuteur = window.setTimeout(function () {api.off("draw.nwentree")}, 10000);
            if (api.search() !== valeur) {api.search(valeur).draw()};
        });
    }

    // Filtres de liste (pastilles) : uniquement sur la première liste de la page
    var filtres = document.getElementById("nw_filtres_liste");
    var emplacement_filtres = conteneur.querySelector(".nw-dt-filtres");
    if (filtres && emplacement_filtres && !filtres.getAttribute("data-nw-place")) {
        filtres.setAttribute("data-nw-place", "1");
        emplacement_filtres.appendChild(filtres);
    }

    // Bouton « Outils » placé juste après le bouton « + Filtre »
    var emplacement_options = conteneur.querySelector(".nw-dt-options");
    if (emplacement_options) {
        nw_compteur_menus += 1;
        var bouton = document.createElement("button");
        bouton.type = "button";
        bouton.id = "nw_options_liste_" + nw_compteur_menus;
        bouton.className = "btn nw-pastille nw-options";
        bouton.setAttribute("aria-haspopup", "menu");
        bouton.setAttribute("aria-expanded", "false");
        bouton.setAttribute("title", "Outils de la liste : colonnes, exports, impression");
        var icone = document.createElement("i");
        icone.className = "fa fa-wrench";
        icone.setAttribute("aria-hidden", "true");
        bouton.appendChild(icone);
        var texte = document.createElement("span");
        texte.textContent = "Outils";
        bouton.appendChild(texte);
        var fleche = document.createElement("i");
        fleche.className = "fa fa-angle-down nw-fleche";
        fleche.setAttribute("aria-hidden", "true");
        bouton.appendChild(fleche);
        emplacement_options.appendChild(bouton);
        bouton.addEventListener("click", function () {
            nw_menu.ouvrir(bouton, function (m) {nw_construire_menu_options(m, api)});
        });
    }
}

function nw_bouton_existe(api, nom) {
    try {
        return api.buttons(nom + ":name").count() > 0;
    } catch (e) {
        return false;
    }
}

function nw_declencher_bouton(api, nom) {
    try {
        api.button(nom + ":name").trigger();
    } catch (e) {
        if (window.console) {console.error(e)};
    }
}

function nw_construire_menu_options(m, api) {
    m.entete("Affichage");
    m.item({label: "Choisir les colonnes…", icone: "fa-columns", sous_menu: true, garder_ouvert: true, action: function () {
        nw_afficher_sous_menu(m, api, nw_construire_menu_colonnes);
    }});
    var plein_ecran = document.body.classList.contains("nw-plein-ecran");
    m.item({label: plein_ecran ? "Quitter le plein écran" : "Plein écran", icone: plein_ecran ? "fa-compress" : "fa-expand", action: function () {
        nw_basculer_plein_ecran(api);
    }});
    if (typeof url_reinitialiser_liste !== "undefined" && typeof nom_view !== "undefined" && api.table().node().classList.contains("datatable")) {
        m.item({label: "Rétablir l'affichage par défaut", icone: "fa-undo", action: function () {
            nw_reinitialiser_affichage();
        }});
    }

    var nb_coches = 0;
    try {nb_coches = api.rows({selected: true}).count()} catch (e) {};
    var groupes = nw_groupes_outils(api, nb_coches);

    var exports = ["excel", "pdf", "csv", "copier"].filter(function (cle) {return groupes[cle].choix.length});
    if (exports.length) {
        m.separateur();
        m.entete("Exporter");
        exports.forEach(function (cle) {nw_item_groupe(m, api, groupes[cle])});
    }

    m.separateur();
    if (groupes.imprimer.choix.length) {nw_item_groupe(m, api, groupes.imprimer)};
    m.item({label: "Actualiser", icone: "fa-refresh", action: function () {
        if (api.page.info().serverSide) {api.ajax.reload(null, false)} else {api.draw(false)};
    }});
}

/* Outils regroupés : un groupe d'un seul choix s'affiche comme une entrée simple,
   un groupe de plusieurs choix ouvre un sous-menu (le menu affiche alors ces choix et un bouton Retour) */
function nw_groupes_outils(api, nb_coches) {
    var badge = nb_coches > 0 ? String(nb_coches) : null;
    var plusieurs_pages = api.page.info().pages > 1;
    var groupes = {
        excel: {label: "Excel", icone: "fa-file-excel-o", choix: [
            ["nw_excel_page", "Page affichée", "fa-file-o"],
            ["nw_excel_tout", "Toutes les pages", "fa-files-o"],
            ["nw_excel_selection", "Lignes cochées", "fa-check-square-o", true],
        ]},
        pdf: {label: "PDF", icone: "fa-file-pdf-o", choix: [
            ["nw_pdf_portrait", "Portrait", "fa-file-pdf-o"],
            ["nw_pdf_paysage", "Paysage", "fa-file-pdf-o"],
        ]},
        csv: {label: "CSV", icone: "fa-file-text-o", choix: [["nw_csv", "CSV", "fa-file-text-o"]]},
        copier: {label: "Copier dans le presse-papiers", icone: "fa-clipboard", choix: [["nw_copier", "Copier dans le presse-papiers", "fa-clipboard"]]},
        imprimer: {label: "Imprimer", icone: "fa-print", choix: [
            ["nw_imprimer", "Toute la liste", "fa-files-o"],
            ["nw_imprimer_page", "Page affichée", "fa-file-o", false, plusieurs_pages],
            ["nw_imprimer_selection", "Lignes cochées", "fa-check-square-o", true],
        ]},
    };
    Object.keys(groupes).forEach(function (cle) {
        groupes[cle].choix = groupes[cle].choix.filter(function (choix) {
            return nw_bouton_existe(api, choix[0]) && (!choix[3] || nb_coches > 0) && choix[4] !== false;
        }).map(function (choix) {
            return {bouton: choix[0], label: choix[1], icone: choix[2], badge: choix[3] ? badge : null};
        });
    });
    return groupes;
}

function nw_item_groupe(m, api, groupe) {
    if (groupe.choix.length === 1) {
        m.item({label: groupe.label, icone: groupe.icone, action: function () {nw_declencher_bouton(api, groupe.choix[0].bouton)}});
        return;
    }
    m.item({label: groupe.label, icone: groupe.icone, sous_menu: true, garder_ouvert: true, action: function () {
        nw_afficher_sous_menu(m, api, function (m, api) {
            nw_bouton_retour(m, api);
            m.separateur();
            m.entete(groupe.label);
            groupe.choix.forEach(function (choix) {
                m.item({label: choix.label, icone: choix.icone, badge: choix.badge, action: function () {nw_declencher_bouton(api, choix.bouton)}});
            });
        });
    }});
}

function nw_afficher_sous_menu(m, api, construire) {
    m.vider();
    construire(m, api);
    m.repositionner();
    m.focus_premier();
}

function nw_bouton_retour(m, api) {
    m.item({label: "Retour", icone: "fa-arrow-left", garder_ouvert: true, action: function () {
        nw_afficher_sous_menu(m, api, nw_construire_menu_options);
    }});
}

/* Plein écran : masque le menu latéral et la barre du haut pour donner toute la largeur à la liste */
function nw_basculer_plein_ecran(api) {
    var actif = document.body.classList.toggle("nw-plein-ecran");
    $(".nw-dt table.dataTable").each(function () {
        if (!$.fn.dataTable.isDataTable(this)) {return};
        var table = $(this).DataTable();
        table.columns.adjust();
        nw_verifier_debordement(table);
        if (table.fixedHeader) {try {table.fixedHeader.adjust()} catch (e) {}};
    });
    if (actif) {
        var conteneur = api.table().container();
        var carte = conteneur ? (conteneur.closest(".card") || conteneur) : null;
        if (carte) {carte.scrollIntoView({block: "start"})};
    }
}

document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && document.body.classList.contains("nw-plein-ecran") && !document.querySelector(".nw-menu, .modal.show")) {
        var table = $(".nw-dt table.dataTable").first();
        if (table.length && $.fn.dataTable.isDataTable(table[0])) {nw_basculer_plein_ecran(table.DataTable())};
    }
});

/* Rétablir l'affichage par défaut : efface le tri, les colonnes, leur ordre et le nombre de lignes mémorisés */
function nw_reinitialiser_affichage() {
    $.ajax({
        type: "POST",
        url: url_reinitialiser_liste,
        data: {view: nom_view},
        datatype: "json",
        success: function () {window.location.reload()},
        error: function () {toastr.error("L'affichage n'a pas pu être rétabli.")}
    });
}

function nw_construire_menu_colonnes(m, api) {
    nw_bouton_retour(m, api);
    m.separateur();
    m.entete("Colonnes affichées");
    if (api.settings()[0]._colReorder) {
        m.note("Pour déplacer une colonne, faites glisser son titre dans le tableau.");
    }
    m.zone_defilement();
    api.columns().every(function () {
        var colonne = this;
        var entete = colonne.header();
        if (!entete || entete.classList.contains("nw-col-actions") || entete.classList.contains("select-checkbox") || entete.querySelector("input")) {return};
        var titre = entete.textContent.replace(/\s+/g, " ").trim();
        if (!titre) {return};
        var element = m.item({label: titre, coche: colonne.visible(), garder_ouvert: true, action: function () {
            var visible = !colonne.visible();
            colonne.visible(visible);
            element.setAttribute("aria-checked", visible ? "true" : "false");
            element.querySelector("i").className = "fa fa-fw " + (visible ? "fa-check-square-o" : "fa-square-o");
            api.columns.adjust();
        }});
    });
}


/* ---------------------------------------------------------------------------------------------
   Mémorisation silencieuse des préférences (une seule requête après une rafale de changements)
--------------------------------------------------------------------------------------------- */
var nw_minuteurs = {};

function nw_memoriser(cle, url, data) {
    if (nw_minuteurs[cle]) {window.clearTimeout(nw_minuteurs[cle])};
    nw_minuteurs[cle] = window.setTimeout(function () {
        $.ajax({type: "POST", url: url, data: data, datatype: "json"});
    }, 1000);
}


/* ---------------------------------------------------------------------------------------------
   Initialisation
--------------------------------------------------------------------------------------------- */
$(document).ready(function() {

    // En-tête CSRF des requêtes AJAX
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", nw_get_csrf());
            }
        }
    });

    var opts = {
        bProcessing: true,
        pagingType: "simple_numbers",
        bDeferRender: true,
        searchDelay: 400,
        responsive: false,
        rowReorder: active_deplacements,
        rowGroup: colonne_regroupement,
        lengthMenu: [
            [ 10, 25, 50, 100, 200, 500, 1000, -1 ],
            [ '10', '25', '50', '100', '200', '500', '1000', 'Toutes' ]
        ],
        dom: "<'nw-dt-barre'<'nw-dt-gauche'<'barre_menu_dt_gauche nw-vide'>f<'nw-dt-filtres'><'nw-dt-options'>>>" +
            "<'nw-dt-boutons-caches'B>" +
            "<'row'<'col-sm-12'tr>>" +
            "<'nw-dt-pied'<'nw-dt-pied-gauche'i><'nw-dt-pied-droite'lp>>",

        // Ces boutons ne sont pas affichés : ils sont déclenchés depuis le menu « Outils »
        buttons:[
            // selected: null = toutes les lignes, même si certaines sont cochées
            nw_bouton_impression('nw_imprimer', {selected: null}, true),
            nw_bouton_impression('nw_imprimer_page', {page: 'current', selected: null}, false),
            nw_bouton_impression('nw_imprimer_selection', {selected: true}, false),
            {
                extend: 'excel',
                name: 'nw_excel_selection',
                exportOptions: {
                    columns: ':visible',
                    modifier: {selected: true}
                }
            },
            {
                extend: 'copy',
                name: 'nw_copier',
                exportOptions: {
                    columns: ':visible'
                }
            },
            {
                extend: 'csv',
                name: 'nw_csv',
                exportOptions: {
                    columns: ':visible'
                }
            },
            {
                extend: 'excel',
                name: 'nw_excel_page',
                exportOptions: {
                    columns: ':visible',
                    modifier: {page: 'current', selected: null}
                }
            },
            {
                extend: 'excel',
                name: 'nw_excel_tout',
                exportOptions: {
                    columns: ':visible',
                    modifier: {selected: null}
                },
                action: function (e, dt, button, config) {
                    var self = this;
                    nw_avec_toutes_les_lignes(dt, function () {
                        $.fn.dataTable.ext.buttons.excelHtml5.action.call(self, e, dt, button, config);
                    });
                }
            },
            {
                extend: 'pdf',
                name: 'nw_pdf_portrait',
                orientation: 'portrait',
                exportOptions: {
                    columns: ':visible'
                },
                footer: true,
            },
            {
                extend: 'pdf',
                name: 'nw_pdf_paysage',
                orientation: 'landscape',
                exportOptions: {
                    columns: ':visible'
                },
                footer: true,
            }
        ],
        footerCallback: function ( row, data, start, end, display ) {
            var api = this.api();
            try {
                var all_columns = api.settings().init().columns;
            } catch(err) {
                var all_columns = [];
            }
            var nb_cols = api.columns().nodes().length;
            var j = 1;
            var label = "";
            while (j < nb_cols) {
                var nom_colonne = $(api.column(j).header()).attr("data-code") || "";
                if (!nom_colonne) {
                    try {
                        nom_colonne = all_columns[j].undefined
                    } catch(err) {
                        nom_colonne = "";
                    }
                }
                var pageTotal = api
                    .column(j, {page: 'current'})
                    .data()
                    .reduce(function (a, b) {
                        var parse = function (valeur) {
                            if (typeof valeur !== "string") {
                                return Number(valeur) || 0;
                            }
                            // Retire les balises HTML éventuelles (colonnes avec mise en forme conditionnelle, ex: montant colorisé)
                            valeur = valeur.replace(/<[^>]*>/g, "");
                            // Ne garde que les chiffres, le signe négatif et les séparateurs décimaux
                            valeur = valeur.replace(/[^0-9,\.\-]/g, "");
                            // Gère le format français (virgule décimale)
                            valeur = valeur.replace(",", ".");
                            return parseFloat(valeur) || 0;
                        };
                        return parse(a) + parse(b);
                    }, 0);
                if (jQuery.inArray(nom_colonne, totaux) > -1) {
                    label = parseFloat(pageTotal).toFixed(2);
                } else {
                    label = "";
                };
                $(api.column(j).footer()).text(label);
                j++;
            }
        },
        drawCallback: function (settings) {
            var api = new $.fn.dataTable.Api(settings);
            nw_preparer_liste(api);
            nw_marquer_colonne_actions(api);
            $(api.table().body()).find("td.nw-col-actions").each(function () {nw_transformer_actions(this)});
            nw_aligner_colonnes(api);
            nw_infobulles_coches(api);
            nw_afficher_liste_vide(api);
            nw_verifier_debordement(api);
        },
        language: {
            buttons: {
                copyTitle: "Copie dans le presse-papiers",
                copySuccess: {_: "%d lignes copiées", 1: "1 ligne copiée"},
            },
            processing:     "Chargement…",
            search:         "",
            searchPlaceholder: "Rechercher…",
            lengthMenu:     "Lignes par page _MENU_",
            info:           "<b>_START_–_END_</b> sur <b>_TOTAL_</b>",
            infoEmpty:      "Aucun élément",
            infoFiltered:   " (filtrés parmi _MAX_)",
            infoPostFix:    "",
            loadingRecords: "Chargement…",
            zeroRecords:    "Aucun élément ne correspond à votre recherche",
            emptyTable:     "Aucune donnée",
            paginate: {
                first:      "«",
                previous:   "<i class='fa fa-chevron-left' aria-hidden='true'></i>",
                next:       "<i class='fa fa-chevron-right' aria-hidden='true'></i>",
                last:       "»"
            },
            aria: {
                sortAscending:  ": activer pour trier la colonne par ordre croissant",
                sortDescending: ": activer pour trier la colonne par ordre décroissant",
                paginate: {
                    first: "Première page",
                    previous: "Page précédente",
                    next: "Page suivante",
                    last: "Dernière page"
                }
            },
            select: {
                "rows": {
                    "_": "%d lignes sélectionnées",
                    "0": "",
                    "1": "1 ligne sélectionnée"
                }
            },
        },
        fixedHeader: {
            header: true,
            footer: true,
            footerOffset: 48
        },
    };

    // Checkbox colonne
    if (active_checkbox === true) {
        opts['columnDefs'] = [{orderable: false, className: 'select-checkbox', targets: 0}];
        // Clic : coche ou décoche une ligne. Maj + clic : coche toute la plage depuis la dernière ligne cliquée.
        // Ctrl (ou Cmd) + clic : coche ou décoche une ligne sans toucher aux autres.
        opts['select'] = {style: 'multi+shift', selector: 'td:first-child'};
    };

    if (hauteur_table != '') {
        jQuery.extend(opts, {"scrollY": hauteur_table, "scrollCollapse": true, "paging": false});
    };

    var datatable = datatableview.initialize($('.datatable'), opts);

    // Initialisation des custom-datatable
    opts["pageLength"] = 25;
    $('.custom-datatable').DataTable(opts);

    // Préparation immédiate de la barre d'outils (sans attendre le chargement des données)
    $('.datatable, .custom-datatable').each(function () {
        if ($.fn.dataTable.isDataTable(this)) {nw_preparer_liste($(this).DataTable())};
    });

    // Déplacement d'une ligne
    var table = $('.datatable').DataTable()
    table.on('row-reordered', function (e, diff, edit) {
        var deplacements = {};
        for ( var i=0, ien=diff.length ; i<ien ; i++ ) {
            var rowData = table.row( diff[i].node ).data();
            deplacements[rowData["DT_RowId"]] = diff[i].newPosition + 1;
        }
        $.ajax({
            type: "POST",
            url: "deplacer_lignes",
            data: {"deplacements": JSON.stringify(deplacements),},
            datatype: "json",
            success: function (data) {
                var index_page = table.page();
                table.ajax.reload();
                table.page(index_page).draw('page');
            },
            error: function () {
                toastr.error("Le déplacement n'a pas pu être enregistré.");
                table.ajax.reload(null, false);
            }
        });
    });

    $('.datatable').on('init.dt', function () {
        if (liste_coches.length > 0) {
            var table = $('.datatable').DataTable();
            $.each(table.rows().data(), function (index, valeurs) {
                if (jQuery.inArray(parseInt(valeurs[1]), liste_coches) > -1) {
                    table.row(":eq(" + index + ")", {page: "current"}).select();
                };
            });
        };
    });

    // On check colonne du header
    $("#checkbox_all").on("change", function(){
        if ($("#checkbox_all").prop("checked")) {
            $('.datatable').DataTable().rows().select();
            $('.custom-datatable').DataTable().rows().select();
        } else {
            $('.datatable').DataTable().rows().deselect();
            $('.custom-datatable').DataTable().rows().deselect();
        };
    });

    // Si coche ou décoche ligne : boutons d'action sur la sélection
    $('.datatable').on('select.dt deselect.dt',  function (evtObj) {
        var nb_selections = table.rows(".selected").nodes().length;
        if (bouton_supprimer) {
            if (!($("#bouton_supprimer_plusieurs").length) && nb_selections) {
                $(".barre_menu_dt_gauche").append("<button type='button' id='bouton_supprimer_plusieurs' class='btn nw-pastille nw-pastille-danger' onclick='supprimer_selections()' title='Supprimer les lignes sélectionnées'><i class='fa fa-trash-o' aria-hidden='true'></i><span>Supprimer</span></button>");
            };
            if (($("#bouton_supprimer_plusieurs").length) && !nb_selections) {$("#bouton_supprimer_plusieurs").remove()};
        }
        $.each(boutons_coches, function(index, valeurs) {
            var bouton = document.getElementById(String(valeurs.id));
            if (!bouton && nb_selections) {
                // Action et libellé définis par l'application côté serveur (et non par l'utilisateur)
                $(".barre_menu_dt_gauche").append("<button type='button' id='" + valeurs.id + "' class='btn nw-pastille' onclick='" + valeurs.action + "' title='" + valeurs.title + "'><span>" + valeurs.label + "</span></button>");
            };
            if (bouton && !nb_selections) {$(bouton).remove()};
        });
        $(".barre_menu_dt_gauche").toggleClass("nw-vide", !$(".barre_menu_dt_gauche").children().length);
    });

    $('.datatable').on( 'length.dt', function (e, settings, len) {
        nw_memoriser("page_length", url_page_length, {view: nom_view, page_length: JSON.stringify(len)});
    } );

    $('.datatable').on( 'column-visibility.dt', function (e, settings, column, state) {
        var all_columns = table.settings().init().columns;
        var hidden_columns = [];
        for (var i in all_columns) {
            if (table.column(all_columns[i].name + ':name').visible() === false) {
                hidden_columns.push(all_columns[i].undefined);
            }
        }
        nw_memoriser("hidden_columns", url_hidden_columns, {view: nom_view, colonnes: JSON.stringify(hidden_columns)});
    } );

});

function get_coches() {
    var table = new $.fn.dataTable.Api('.datatable');
    var lignes = table.rows({selected: true});
    var data = lignes.data().toArray();
    // Récupère la liste des ids des lignes sélectionnées
    var listepk = [];
    $.each(data, function(index, valeurs) {
        listepk.push(parseInt(valeurs[1]));
    });
    return listepk;
}

function supprimer_selections() {
    var listepk = get_coches();
    var url = url_supprimer_plusieurs.replace("xxx", listepk.join(";"));
    window.location = url;
}

function modifier_selections() {
    var listepk = get_coches();
    var url = url_modifier_plusieurs.replace("xxx", listepk.join(";"));
    window.location = url;
}

// Mémorisation du tri choisi par l'utilisateur
$('.datatable th').on('click', function() {
    var code_colonne = $(this).data("code");
    if (code_colonne) {
        var table = new $.fn.dataTable.Api('.datatable');
        window.setTimeout(function () {
            var table_order = table.order();
            if (table_order.length) {
                nw_memoriser("tri_liste", url_tri_liste, {view: nom_view, colonne: code_colonne, sens: table_order[0][1]});
            }
        }, 200);
    };
});
