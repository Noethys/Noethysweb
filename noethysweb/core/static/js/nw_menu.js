/*  Noethysweb - Menu flottant partagé
    Utilisé par les listes DataTables (mydatatableview.js) et les listes bootstrap-table (nw_bootstrap_table.js).
*/

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
